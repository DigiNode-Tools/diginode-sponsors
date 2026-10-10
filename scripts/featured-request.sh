#!/usr/bin/env bash
#
# Name:    featured-request.sh
# Purpose: Check a "Become a Featured Sponsor" request (a GitHub issue) and, if everything is in order, add the sponsor's
#          logo to logos/ and their details to featured-approved.json, ready for Olly to approve in a pull request.
#
# Input (environment variables - the issue body is untrusted, so it is only ever read from here):
#   ISSUE_AUTHOR    GitHub login of the person who opened the issue
#   ISSUE_BODY      The issue body, as written by the "Become a Featured Sponsor" form
#   SPONSORS_TOKEN  GitHub token that can read DigiNode-Tools' sponsors (read:org, read:user)
#   GH_TOKEN        GitHub token for checking organisation membership (the workflow's own token is fine)
#   SPONSORS_FILE   Optional, for testing: read the sponsorships from this file instead of GitHub
#
# Output, written to $RESULT_FILE (default result.env):
#   status=ok|rejected      sponsor=<login>     message=<text for the issue comment>
#
# Exit code: 0 whenever a result was written (ok or rejected), 1 if the script itself failed.

set -euo pipefail

ORG="DigiNode-Tools"
FEATURED_MIN=300
FEATURED_PLACES=3
MAX_LOGO_BYTES=$((1024 * 1024))

ROOT=$(cd "$(dirname "$0")/.." && pwd)
RESULT_FILE="${RESULT_FILE:-$ROOT/result.env}"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

reject() {
    printf 'status=rejected\nsponsor=%s\nmessage=%s\n' "${SPONSOR:-}" "$1" > "$RESULT_FILE"
    echo "Rejected: $1"
    exit 0
}

# Read one field from the issue form. Issue forms are written as "### Label" followed by the answer.
form_field() {
    printf '%s\n' "$ISSUE_BODY" | tr -d '\r' | awk -v label="### $1" '
        $0 == label { found = 1; next }
        found && /^### / { exit }
        found { print }' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -v '^$' | grep -v '^_No response_$' || true
}

# ------------------------------------------------------------------------------------------
# Read and check the form

SPONSOR=$(form_field "Sponsoring GitHub account" | head -1)
SPONSOR="${SPONSOR#@}"
if [ -z "$SPONSOR" ]; then
    SPONSOR="$ISSUE_AUTHOR"
fi
if ! [[ "$SPONSOR" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,38})$ ]]; then
    reject "\"Sponsoring GitHub account\" isn't a valid GitHub username or organisation."
fi

NAME=$(form_field "Name to display" | head -1)
if ! [[ "$NAME" =~ ^[[:alnum:]][[:alnum:]\ .,\&\'+-]{0,39}$ ]]; then
    reject "\"Name to display\" can only use letters, numbers, spaces and . , & ' + - and must be 40 characters or less."
fi

WEBSITE=$(form_field "Website" | head -1)
if ! [[ "$WEBSITE" =~ ^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~/?#=\&%+-]*)?$ ]] || [ ${#WEBSITE} -gt 200 ]; then
    reject "\"Website\" must be a normal web address starting with https:// (e.g. https://example.com)."
fi

# The logo is uploaded into the form, which turns it into a link to github.com/user-attachments/...
LOGO_URL=$(form_field "Logo" | grep -oE 'https://(github\.com/user-attachments/assets|user-images\.githubusercontent\.com|private-user-images\.githubusercontent\.com)/[A-Za-z0-9/._-]+' | head -1 || true)
if [ -z "$LOGO_URL" ]; then
    reject "Please upload your logo by dragging and dropping it into the \"Logo\" box (PNG, JPG or WebP)."
fi

# ------------------------------------------------------------------------------------------
# If it's an organisation, the person asking must be a public member of it

if [ "$SPONSOR" != "$ISSUE_AUTHOR" ]; then
    if ! gh api "orgs/$SPONSOR/public_members/$ISSUE_AUTHOR" > /dev/null 2>&1; then
        reject "@$ISSUE_AUTHOR isn't a public member of the \`$SPONSOR\` organisation on GitHub. Please make your membership public, or ask someone who is a public member to submit the request."
    fi
fi

# ------------------------------------------------------------------------------------------
# Is the account actively sponsoring at the Featured tier?

if [ -n "${SPONSORS_FILE:-}" ]; then
    jq . "$SPONSORS_FILE" > "$WORK/nodes.json"
else
    query='query { organization(login: "'"$ORG"'") { sponsorshipsAsMaintainer(first: 100, activeOnly: true) {
        nodes { privacyLevel isOneTimePayment tier { monthlyPriceInDollars isOneTime }
                sponsorEntity { ... on User { login } ... on Organization { login } } } } } }'
    curl -fsSL --retry 3 -H "Authorization: Bearer $SPONSORS_TOKEN" -H "Content-Type: application/json" \
        -d "$(jq -n --arg q "$query" '{query: $q}')" https://api.github.com/graphql > "$WORK/response.json"
    if jq -e '.errors' "$WORK/response.json" > /dev/null; then
        jq -r '.errors[].message' "$WORK/response.json" >&2
        exit 1
    fi
    jq '.data.organization.sponsorshipsAsMaintainer.nodes' "$WORK/response.json" > "$WORK/nodes.json"
fi

tier=$(jq -r --arg login "$SPONSOR" '[.[] | select((.sponsorEntity.login | ascii_downcase) == ($login | ascii_downcase)
        and (.isOneTimePayment | not) and (.tier.isOneTime | not))] | first | .tier.monthlyPriceInDollars // 0' "$WORK/nodes.json")
privacy=$(jq -r --arg login "$SPONSOR" '[.[] | select((.sponsorEntity.login | ascii_downcase) == ($login | ascii_downcase))] | first | .privacyLevel // ""' "$WORK/nodes.json")
login=$(jq -r --arg login "$SPONSOR" '[.[] | select((.sponsorEntity.login | ascii_downcase) == ($login | ascii_downcase))] | first | .sponsorEntity.login // ""' "$WORK/nodes.json")

if [ "$tier" -lt "$FEATURED_MIN" ]; then
    reject "\`$SPONSOR\` isn't currently sponsoring DigiNode Tools at the \$$FEATURED_MIN a month Featured Sponsor tier. Please [become a Featured Sponsor](https://github.com/sponsors/DigiNode-Tools) first, then edit this issue (any small change will do) to check again."
fi
if [ "$privacy" != "PUBLIC" ]; then
    reject "\`$SPONSOR\`'s sponsorship is private. Featured Sponsors need a public sponsorship, so they can be shown. You can change this in your [sponsorship settings](https://github.com/sponsors/DigiNode-Tools), then edit this issue to check again."
fi
SPONSOR="$login"

# ------------------------------------------------------------------------------------------
# Is there a place free? (Updating an existing Featured Sponsor's details is always allowed.)

already=$(jq -r --arg login "$SPONSOR" 'has($login)' "$ROOT/featured-approved.json")
if [ "$already" != "true" ]; then
    taken=$(jq '[keys[] | select(. != "_comment")] | length' "$ROOT/featured-approved.json")
    if [ "$taken" -ge "$FEATURED_PLACES" ]; then
        reject "Sorry, all $FEATURED_PLACES Featured Sponsor places are currently taken. Olly will be in touch."
    fi
fi

# ------------------------------------------------------------------------------------------
# Download the logo and check it really is an image

curl -fsSL --retry 3 --max-filesize "$MAX_LOGO_BYTES" -o "$WORK/logo" "$LOGO_URL" \
    || reject "The logo couldn't be downloaded, or it's larger than 1 MB. Please upload it again."
size=$(wc -c < "$WORK/logo" | tr -d ' ')
[ "$size" -le "$MAX_LOGO_BYTES" ] || reject "The logo is larger than 1 MB. Please upload a smaller version."

case "$(file --brief --mime-type "$WORK/logo")" in
    image/png  ) ext="png";;
    image/jpeg ) ext="jpg";;
    image/webp ) ext="webp";;
    *          ) reject "The logo must be a PNG, JPG or WebP image.";;
esac

# ------------------------------------------------------------------------------------------
# Add them (replacing any earlier logo of theirs)

rm -f "$ROOT/logos/$SPONSOR".*
cp "$WORK/logo" "$ROOT/logos/$SPONSOR.$ext"

jq --arg login "$SPONSOR" --arg name "$NAME" --arg url "$WEBSITE" --arg logo "logos/$SPONSOR.$ext" \
    '.[$login] = {name: $name, url: $url, logo: $logo}' "$ROOT/featured-approved.json" > "$WORK/approved.json"
cp "$WORK/approved.json" "$ROOT/featured-approved.json"

{
    echo "status=ok"
    echo "sponsor=$SPONSOR"
    echo "message=Everything checks out: \`$SPONSOR\` is a Featured Sponsor and there's a place for them."
} > "$RESULT_FILE"
echo "OK: $SPONSOR - $NAME - $WEBSITE - logos/$SPONSOR.$ext"

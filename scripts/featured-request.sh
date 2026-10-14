#!/usr/bin/env bash
#
# Name:    featured-request.sh
# Purpose: Check a "Become a Featured Sponsor" request (a GitHub issue) and, if everything is in order, add the sponsor's
#          logo to logos/ and their details to featured-approved.json, ready for Olly to approve in a pull request.
#          A GitHub sponsor is checked against GitHub Sponsors. A Ko-fi sponsor (the form's "Ko-fi name" is filled in)
#          is checked against kofi-members.json (kept up to date from Ko-fi's webhook), and is added under the same key.
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

# shellcheck source=lib.sh
source "$ROOT/scripts/lib.sh"

# ------------------------------------------------------------------------------------------
# Read and check the form

# Ko-fi sponsors give the name on their Ko-fi support instead of a GitHub account
KOFI_NAME=$(form_field "Ko-fi name" | head -1)
if [ -n "$KOFI_NAME" ]; then
    [ ${#KOFI_NAME} -le 60 ] || reject "\"Ko-fi name\" must be 60 characters or less."
    SPONSOR=$("${PYTHON:-python3}" "$ROOT/scripts/kofi-membership.py" --key "$KOFI_NAME")
    if ! [[ "$SPONSOR" =~ ^kofi-[a-z0-9-]{1,34}$ ]]; then
        SPONSOR=""
        reject "\"Ko-fi name\" should be the name on your Ko-fi support, as shown on the [sponsors page](https://diginode.tools/sponsors/)."
    fi
else
    get_sponsor_account
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
# Is the account actively sponsoring at the Featured tier?

if [ -n "$KOFI_NAME" ]; then
    # Listed in kofi-members.json at the Featured tier, and not expired (only public Ko-fi supporters are ever added)
    ok=$(jq -r --arg key "$SPONSOR" --arg today "$(date -u +%F)" --argjson min "$FEATURED_MIN" \
        '(.[$key] // {}) as $m | (($m.amount // 0) >= $min and (($m.until // "9999-12-31") >= $today))' "$ROOT/kofi-members.json")
    if [ "$ok" != "true" ]; then
        reject "We couldn't find a Ko-fi Featured Sponsor with that name. Please check it's the name on your Ko-fi support, that your support is public, and that you've joined the **Featured Sponsor** tier on [Ko-fi](https://ko-fi.com/diginode) (it can take a few minutes to show up). Then edit this issue (any small change will do) to check again."
    fi
else
    get_sponsorship
    tier="$SPONSOR_TIER"
    privacy="$SPONSOR_PRIVACY"

    if [ "$tier" -lt "$FEATURED_MIN" ]; then
        reject "\`$SPONSOR\` isn't currently sponsoring DigiNode Tools at the \$$FEATURED_MIN a month Featured Sponsor tier. Please [become a Featured Sponsor](https://github.com/sponsors/DigiNode-Tools) first, then edit this issue (any small change will do) to check again."
    fi
    if [ "$privacy" != "PUBLIC" ]; then
        reject "\`$SPONSOR\`'s sponsorship is private. Featured Sponsors need a public sponsorship, so they can be shown. You can change this in your [sponsorship settings](https://github.com/sponsors/DigiNode-Tools), then edit this issue to check again."
    fi
fi

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
    image/png | image/jpeg | image/webp ) ;;
    * ) reject "The logo must be a PNG, JPG or WebP image.";;
esac

# Turn it into a card the same size as all the others (this re-draws the image, so only the picture itself is kept)
card_error=$("${PYTHON:-python3}" "$ROOT/scripts/make-card.py" "$WORK/logo" "$WORK/card.png" 2>&1) || {
    [ $? -eq 2 ] && reject "$card_error"
    echo "$card_error" >&2
    exit 1
}

# ------------------------------------------------------------------------------------------
# Add them (replacing any earlier logo of theirs)

rm -f "$ROOT/logos/$SPONSOR".*
cp "$WORK/card.png" "$ROOT/logos/$SPONSOR.png"

jq --arg login "$SPONSOR" --arg name "$NAME" --arg url "$WEBSITE" --arg logo "logos/$SPONSOR.png" \
    '.[$login] = {name: $name, url: $url, logo: $logo}' "$ROOT/featured-approved.json" > "$WORK/approved.json"
cp "$WORK/approved.json" "$ROOT/featured-approved.json"

{
    echo "status=ok"
    echo "sponsor=$SPONSOR"
    if [ -n "$KOFI_NAME" ]; then
        echo "message=Everything checks out: \`$SPONSOR\` is a Featured Sponsor on Ko-fi and there's a place for them. As this is a Ko-fi sponsor, please also check that @$ISSUE_AUTHOR really is them (e.g. they mention it in a Ko-fi message)."
    else
        echo "message=Everything checks out: \`$SPONSOR\` is a Featured Sponsor and there's a place for them."
    fi
} > "$RESULT_FILE"
echo "OK: $SPONSOR - $NAME - $WEBSITE - logos/$SPONSOR.png"

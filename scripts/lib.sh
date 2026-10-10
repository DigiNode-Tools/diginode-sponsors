#!/usr/bin/env bash
#
# Shared by the scripts that handle the issue forms (featured-request.sh and patron-listing.sh). Expects ISSUE_AUTHOR,
# ISSUE_BODY, WORK (a temporary folder) and a reject function, which writes the result and exits.

ORG="DigiNode-Tools"

# Read one field from an issue form. Issue forms are written as "### Label" followed by the answer.
form_field() {
    printf '%s\n' "$ISSUE_BODY" | tr -d '\r' | awk -v label="### $1" '
        $0 == label { found = 1; next }
        found && /^### / { exit }
        found { print }' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -v '^$' | grep -v '^_No response_$' || true
}

# Work out which account the request is for, from the "Sponsoring GitHub account" field (blank = the issue author).
# If it's an organisation, the person asking must be a public member of it. Sets SPONSOR.
get_sponsor_account() {
    SPONSOR=$(form_field "Sponsoring GitHub account" | head -1)
    SPONSOR="${SPONSOR#@}"
    if [ -z "$SPONSOR" ]; then
        SPONSOR="$ISSUE_AUTHOR"
    fi
    if ! [[ "$SPONSOR" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,38})$ ]]; then
        reject "\"Sponsoring GitHub account\" isn't a valid GitHub username or organisation."
    fi
    if [ "$(echo "$SPONSOR" | tr '[:upper:]' '[:lower:]')" != "$(echo "$ISSUE_AUTHOR" | tr '[:upper:]' '[:lower:]')" ]; then
        if ! gh api "orgs/$SPONSOR/public_members/$ISSUE_AUTHOR" > /dev/null 2>&1; then
            reject "@$ISSUE_AUTHOR isn't a public member of the \`$SPONSOR\` organisation on GitHub. Please make your membership public, or ask someone who is a public member to submit the request."
        fi
    fi
}

# Get the current sponsorships into $WORK/nodes.json (or from SPONSORS_FILE, for testing), then look up SPONSOR.
# Sets SPONSOR_TIER (monthly dollars, 0 if not a monthly sponsor), SPONSOR_PRIVACY, and corrects the case of SPONSOR.
get_sponsorship() {
    if [ -n "${SPONSORS_FILE:-}" ]; then
        jq . "$SPONSORS_FILE" > "$WORK/nodes.json"
    else
        local query='query { organization(login: "'"$ORG"'") { sponsorshipsAsMaintainer(first: 100, activeOnly: true) {
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

    local match='select((.sponsorEntity.login | ascii_downcase) == ($login | ascii_downcase))'
    SPONSOR_TIER=$(jq -r --arg login "$SPONSOR" "[.[] | $match | select((.isOneTimePayment | not) and (.tier.isOneTime | not))] | first | .tier.monthlyPriceInDollars // 0" "$WORK/nodes.json")
    SPONSOR_PRIVACY=$(jq -r --arg login "$SPONSOR" "[.[] | $match] | first | .privacyLevel // \"\"" "$WORK/nodes.json")
    local login
    login=$(jq -r --arg login "$SPONSOR" "[.[] | $match] | first | .sponsorEntity.login // \"\"" "$WORK/nodes.json")
    if [ -n "$login" ]; then
        SPONSOR="$login"
    fi
}

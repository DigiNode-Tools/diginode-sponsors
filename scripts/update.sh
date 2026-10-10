#!/usr/bin/env bash
#
# Name:    update.sh
# Purpose: Build the DigiNode Tools sponsors page (sponsors.md) and the list of Featured Sponsors that DigiNode Setup
#          and DigiNode Dashboard display (featured.json), from the current GitHub Sponsors of DigiNode-Tools.
#
# Usage:   scripts/update.sh [--input FILE]
#
#   --input FILE  Read the sponsorships from FILE instead of GitHub, for testing. FILE is a JSON array in the same
#                 format as the "nodes" returned by the GitHub API (see the query below).
#
# If PENDING_FILE is set, the logins of public Featured Sponsors who have been sponsoring for REMIND_DAYS days but haven't
# been approved yet (usually because they haven't filled in the form) are written to it, one per line, so they can be
# reminded.
#
# Needs a GitHub token with the read:org and read:user scopes, in SPONSORS_TOKEN (or from 'gh auth token').
#
# Who is listed:
#   Featured Sponsors  - sponsoring monthly at $300 or more, AND approved by Olly in featured-approved.json
#   Patrons           - sponsoring monthly at $100 or more (and Featured Sponsors who haven't been approved yet), unless
#                       they asked not to be in patron-settings.json
#   Sponsors who chose to sponsor privately are never listed.

set -euo pipefail

ORG="DigiNode-Tools"
FEATURED_MIN=300
FEATURED_PLACES=3
PATRON_MIN=100
SPONSORS_URL="https://github.com/sponsors/DigiNode-Tools"
REMIND_DAYS=3
RAW_URL="https://raw.githubusercontent.com/DigiNode-Tools/diginode-sponsors/main"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
INPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --input ) INPUT="${2:?--input needs a file}"; shift;;
        *       ) echo "Unknown option: $1" >&2; exit 1;;
    esac
    shift
done

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

NOW=$(jq -nr 'now | floor | todate')

# ------------------------------------------------------------------------------------------
# Get the current sponsorships

if [ -n "$INPUT" ]; then
    jq . "$INPUT" > "$WORK/nodes.json"
else
    TOKEN="${SPONSORS_TOKEN:-$(gh auth token 2>/dev/null || true)}"
    if [ -z "$TOKEN" ]; then
        echo "No GitHub token. Set SPONSORS_TOKEN (needs the read:org and read:user scopes)." >&2
        exit 1
    fi

    query='query {
      organization(login: "'"$ORG"'") {
        sponsorshipsAsMaintainer(first: 100, activeOnly: true) {
          nodes {
            privacyLevel
            createdAt
            isOneTimePayment
            tier { monthlyPriceInDollars isOneTime }
            sponsorEntity {
              ... on User { login name url websiteUrl }
              ... on Organization { login name url websiteUrl }
            }
          }
        }
      }
    }'

    curl -fsSL --retry 3 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
        -d "$(jq -n --arg q "$query" '{query: $q}')" https://api.github.com/graphql > "$WORK/response.json"

    if jq -e '.errors' "$WORK/response.json" > /dev/null; then
        echo "GitHub returned an error:" >&2
        jq -r '.errors[].message' "$WORK/response.json" >&2
        exit 1
    fi

    jq '.data.organization.sponsorshipsAsMaintainer.nodes' "$WORK/response.json" > "$WORK/nodes.json"
fi

# ------------------------------------------------------------------------------------------
# Work out who is a Featured Sponsor and who is a Patron

jq --slurpfile approved "$ROOT/featured-approved.json" --slurpfile settings "$ROOT/patron-settings.json" \
   --argjson featured_min "$FEATURED_MIN" --argjson patron_min "$PATRON_MIN" --arg raw "$RAW_URL" '
    ($approved[0] | del(._comment)) as $approved
    | ($approved | keys_unsorted) as $order
    | ($settings[0] | del(._comment)) as $settings
    | map(select(.privacyLevel == "PUBLIC" and (.isOneTimePayment | not) and (.tier.isOneTime | not)))
    | map({
        login: .sponsorEntity.login,
        name: (.sponsorEntity.name // .sponsorEntity.login),
        github: .sponsorEntity.url,
        amount: .tier.monthlyPriceInDollars
      })
    | {
        # In the order they were approved, so their place in the row stays the same
        featured: [ .[] | select(.amount >= $featured_min and $approved[.login] != null)
                    | $approved[.login] as $a
                    | .login as $l | {order: ($order | index($l)), name: ($a.name // .name), url: ($a.url // .github),
                       logo: (if $a.logo then $raw + "/" + $a.logo else null end), card: $a.logo} ]
                  | sort_by(.order) | map(del(.order)),
        # Patrons are linked to their GitHub profile, unless they have asked not to be (patron-settings.json)
        patrons:  [ sort_by(-.amount, (.name | ascii_downcase))[]
                    | select(.amount >= $patron_min and ((.amount >= $featured_min and $approved[.login] != null) | not))
                    | ($settings[.login].listing // "linked") as $listing
                    | select($listing != "hidden")
                    | {name, url: (if $listing == "linked" then .github else null end)} ]
      }' "$WORK/nodes.json" > "$WORK/lists.json"

# ------------------------------------------------------------------------------------------
# featured.json - read by DigiNode Setup, DigiNode Dashboard and the diginode.tools WordPress plugin. They ignore it if
# "checked" is more than 7 days old, so a Featured Sponsor who has stopped sponsoring is never shown for long, even if
# this stops running.

jq --arg now "$NOW" '{checked: $now, featured: [.featured[] | {name, url, logo}]}' "$WORK/lists.json" > "$ROOT/featured.json"

# ------------------------------------------------------------------------------------------
# slots/featured-1.png to featured-3.png - the three Featured Sponsor places, shown in the DigiNode Tools README and on the
# website. Each is a sponsor's logo card, or the "Your brand here" placeholder. Their links are handled by the WordPress
# plugin (https://diginode.tools/featured-sponsor/1 etc.), which reads featured.json.

mkdir -p "$ROOT/slots"
for slot in $(seq 1 "$FEATURED_PLACES"); do
    card=$(jq -r --argjson i "$((slot - 1))" '.featured[$i].card // empty' "$WORK/lists.json")
    if [ -n "$card" ] && [ -f "$ROOT/$card" ]; then
        cp "$ROOT/$card" "$ROOT/slots/featured-$slot.png"
    else
        cp "$ROOT/images/featured-placeholder.png" "$ROOT/slots/featured-$slot.png"
    fi
done

# ------------------------------------------------------------------------------------------
# sponsors.md - embedded in the diginode.tools/sponsors page. Edit page-intro.md to change the text.

{
    echo "<!-- Generated by scripts/update.sh - do not edit. Edit page-intro.md instead. -->"
    echo ""
    echo "## Featured Sponsors"
    echo ""
    echo '<p align="center">'
    for slot in $(seq 1 "$FEATURED_PLACES"); do
        jq -r --argjson i "$((slot - 1))" --arg raw "$RAW_URL" --arg join "$SPONSORS_URL" '
            def html: gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;") | gsub("\""; "&quot;");
            (.featured[$i] // null) as $s
            | if $s and $s.card then "<a href=\"\($s.url | html)\"><img src=\"\($raw)/\($s.card)\" alt=\"\($s.name | html)\" width=\"300\"></a>"
              else "<a href=\"\($join)\"><img src=\"\($raw)/images/featured-placeholder.png\" alt=\"Your brand here - become a Featured Sponsor\" width=\"300\"></a>"
              end' "$WORK/lists.json"
    done
    echo '</p>'
    echo ""
    cat "$ROOT/page-intro.md"

    if [ "$(jq '.patrons | length' "$WORK/lists.json")" -gt 0 ]; then
        echo ""
        echo "## Thank you to my amazing Patrons"
        echo ""
        jq -r '.patrons[] | if .url then "- [\(.name)](\(.url))" else "- \(.name)" end' "$WORK/lists.json"
    fi
} > "$ROOT/sponsors.md"

# ------------------------------------------------------------------------------------------
# Featured Sponsors who haven't been approved yet, for a reminder

if [ -n "${PENDING_FILE:-}" ]; then
    jq -r --slurpfile approved "$ROOT/featured-approved.json" --argjson featured_min "$FEATURED_MIN" \
       --argjson days "$REMIND_DAYS" '
        .[] | select(.privacyLevel == "PUBLIC" and (.isOneTimePayment | not) and (.tier.isOneTime | not)
                     and .tier.monthlyPriceInDollars >= $featured_min
                     and $approved[0][.sponsorEntity.login] == null
                     and ((.createdAt // "1970-01-01T00:00:00Z") | fromdateiso8601) < (now - $days * 86400))
            | .sponsorEntity.login' "$WORK/nodes.json" > "$PENDING_FILE"
fi

echo "Featured Sponsors: $(jq '.featured | length' "$WORK/lists.json")    Patrons: $(jq '.patrons | length' "$WORK/lists.json")"

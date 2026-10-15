#!/usr/bin/env bash
#
# Name:    patron-listing.sh
# Purpose: Handle a "Change how I'm listed" request (a GitHub issue) from a sponsor, by updating patron-settings.json.
#
# Input (environment variables - the issue body is untrusted, so it is only ever read from here):
#   ISSUE_AUTHOR, ISSUE_BODY, SPONSORS_TOKEN, GH_TOKEN, SPONSORS_FILE - the same as featured-request.sh
#
# Output, written to $RESULT_FILE (default result.env):
#   status=ok|unchanged|rejected      sponsor=<login>     message=<text for the issue comment>

set -euo pipefail

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

get_sponsor_account

case "$(form_field "How should you be listed?" | head -1)" in
    "My name, linked to my GitHub profile" ) listing="linked";    wanted="will be listed by name, linked to its GitHub profile";;
    "My name only, without a link"         ) listing="name";      wanted="will be listed by name only, without a link";;
    "A nickname (enter it below)"          ) listing="nickname";  wanted="will be listed by its nickname";;
    "As \"A supporter\", without a name"   ) listing="anonymous"; wanted="will be listed as \"A supporter\", without a name";;
    "Don't list me"                        ) listing="hidden";    wanted="won't be listed";;
    * ) reject "Please choose how you'd like to be listed.";;
esac

nickname=""
if [ "$listing" = "nickname" ]; then
    nickname=$(form_field "Nickname" | head -1 | sed -e "s/[^[:alnum:] .,'&()_-]//g" -e 's/  */ /g' -e 's/^ //' -e 's/ $//' | cut -c1-30)
    [ -n "$nickname" ] || reject "Please enter a nickname (letters, numbers, spaces and simple punctuation), or choose another option."
    wanted="will be listed as \"$nickname\""
fi
hide_amount=false
if form_field "Amount" | grep -q '^- \[[xX]\]'; then
    hide_amount=true
    wanted="$wanted, without the amount"
fi

# Anyone who has sponsored DigiNode Tools - monthly or once, now or in the past - can choose how they are listed
ACTIVE_ONLY=false get_sponsorship
if [ -z "$SPONSOR_PRIVACY" ]; then
    reject "\`$SPONSOR\` hasn't sponsored DigiNode Tools on GitHub. If you sponsor from an organisation, enter it in \"Sponsoring GitHub account\". If you support me on Ko-fi, just send me a message there instead."
fi

# Being listed by name, linked, with the amount shown, is the default, so it's stored by removing them from the file
current=$(jq -c --arg login "$SPONSOR" '.[$login] // {}' "$ROOT/patron-settings.json")
if [ "$listing" = "linked" ] && [ "$hide_amount" = "false" ]; then
    jq --arg login "$SPONSOR" 'del(.[$login])' "$ROOT/patron-settings.json" > "$WORK/settings.json"
else
    jq --arg login "$SPONSOR" --arg listing "$listing" --arg nickname "$nickname" --argjson hide "$hide_amount" \
        '.[$login] = ({listing: $listing} + (if $nickname != "" then {nickname: $nickname} else {} end) + (if $hide then {hide_amount: true} else {} end))' \
        "$ROOT/patron-settings.json" > "$WORK/settings.json"
fi
cp "$WORK/settings.json" "$ROOT/patron-settings.json"
new_setting=$(jq -c --arg login "$SPONSOR" '.[$login] // {}' "$ROOT/patron-settings.json")

note=""
if [ "$SPONSOR_PRIVACY" != "PUBLIC" ]; then
    note=" Your sponsorship is private, so you aren't listed anyway. This setting will apply if you make it public."
fi
[ "$current" = "$new_setting" ] && status="unchanged" || status="ok"
printf 'status=%s\nsponsor=%s\nmessage=%s\n' "$status" "$SPONSOR" "Done: \`$SPONSOR\` $wanted. The sponsors page will be updated within a few minutes.$note" > "$RESULT_FILE"
echo "OK: $SPONSOR - $listing"

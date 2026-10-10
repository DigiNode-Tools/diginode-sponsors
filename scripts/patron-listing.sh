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
    "My name, linked to my GitHub profile" ) listing="linked"; wanted="will be listed by name, linked to its GitHub profile";;
    "My name only, without a link"         ) listing="name";   wanted="will be listed by name only, without a link";;
    "Don't list me"                        ) listing="hidden"; wanted="won't be listed";;
    * ) reject "Please choose how you'd like to be listed.";;
esac

# Only current sponsors can change how they are listed (it keeps patron-settings.json tidy)
get_sponsorship
if [ -z "$SPONSOR_PRIVACY" ]; then
    reject "\`$SPONSOR\` isn't currently sponsoring DigiNode Tools. If you sponsor from an organisation, enter it in \"Sponsoring GitHub account\"."
fi

# "linked" is the default, so it's stored by removing them from the file
current=$(jq -r --arg login "$SPONSOR" '.[$login].listing // "linked"' "$ROOT/patron-settings.json")
if [ "$listing" = "linked" ]; then
    jq --arg login "$SPONSOR" 'del(.[$login])' "$ROOT/patron-settings.json" > "$WORK/settings.json"
else
    jq --arg login "$SPONSOR" --arg listing "$listing" '.[$login] = {listing: $listing}' "$ROOT/patron-settings.json" > "$WORK/settings.json"
fi
cp "$WORK/settings.json" "$ROOT/patron-settings.json"

note=""
if [ "$SPONSOR_PRIVACY" != "PUBLIC" ]; then
    note=" Your sponsorship is private, so you aren't listed anyway. This setting will apply if you make it public."
fi
[ "$current" = "$listing" ] && status="unchanged" || status="ok"
printf 'status=%s\nsponsor=%s\nmessage=%s\n' "$status" "$SPONSOR" "Done: \`$SPONSOR\` $wanted. The sponsors page will be updated within a few minutes.$note" > "$RESULT_FILE"
echo "OK: $SPONSOR - $listing"

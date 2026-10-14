#!/usr/bin/env python3
#
# Name:    kofi-membership.py
# Purpose: Add or extend a Ko-fi member in kofi-members.json, from a Ko-fi membership payment. Run by the "Update
#          sponsors" Action when the DigiNode Tools Sponsors WordPress plugin on diginode.tools passes on a Ko-fi
#          webhook (a repository_dispatch event, type kofi-membership).
#
#          The plugin only passes on public membership payments, with just: name, tier, amount, currency and timestamp
#          (no email or message - Action logs in this repo are public).
#
#          Only the Patron and Featured Sponsor tiers are listed. Each monthly payment lists the member until 35 days
#          after it, so they drop off about a month after their last payment (Ko-fi doesn't say when someone cancels).
#          A Ko-fi Featured Sponsor is shown as a Patron until Olly approves them in featured-approved.json (same key).
#
# Usage:   KOFI_PAYLOAD='{"name": "...", "tier": "...", "amount": "...", "currency": "USD", "timestamp": "..."}' \
#            scripts/kofi-membership.py
#          If NEW_FEATURED_FILE is set and someone has just become a Ko-fi Featured Sponsor, "key<TAB>name" is written to
#          it, so Olly can be told they're waiting to send their logo.
#          scripts/kofi-membership.py --key "NAME"   Print the kofi-members.json key for a Ko-fi name (used by
#                                                    featured-request.sh), or nothing if the name isn't usable

import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "kofi-members.json")
LISTED_DAYS = 35
TIERS = [("featured", 300), ("patron", 100)]   # Matched against the Ko-fi tier name (e.g. "🚀 Featured Sponsor")


def clean_name(name):
    """The supporter's name, safe to show in markdown and HTML: letters, numbers, spaces and simple punctuation."""
    name = unicodedata.normalize("NFC", str(name or ""))
    name = "".join(c for c in name if c.isalnum() or c in " .,'&()-_")
    return re.sub(r"\s+", " ", name).strip()[:60]


def member_key(name):
    """The kofi-members.json key for a (cleaned) Ko-fi name."""
    slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()).strip("-")
    return "kofi-" + (slug[:30].strip("-") or hashlib.sha256(name.encode()).hexdigest()[:8])


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--key":
        name = clean_name(sys.argv[2])
        if name:
            print(member_key(name))
        return
    try:
        payload = json.loads(os.environ.get("KOFI_PAYLOAD") or "{}")
    except ValueError:
        sys.exit("ERROR: KOFI_PAYLOAD isn't valid JSON")

    tier_name = str(payload.get("tier") or "").lower()
    amount = next((a for word, a in TIERS if word in tier_name), None)
    if amount is None:
        print(f"Not a listed tier ({payload.get('tier')!r}) - nothing to do")
        return

    name = clean_name(payload.get("name"))
    if not name:
        print("No usable name - nothing to do")
        return
    key = member_key(name)

    try:
        paid = datetime.datetime.fromisoformat(str(payload.get("timestamp")).replace("Z", "+00:00")).date()
    except ValueError:
        paid = datetime.date.today()
    until = (paid + datetime.timedelta(days=LISTED_DAYS)).isoformat()

    with open(FILE, encoding="utf-8") as f:
        members = json.load(f)

    entry = members.get(key)
    if amount >= 300 and (entry is None or entry.get("amount", 0) < 300) and os.environ.get("NEW_FEATURED_FILE"):
        with open(os.environ["NEW_FEATURED_FILE"], "w", encoding="utf-8") as f:
            f.write(f"{key}\t{name}\n")
    if entry is None:
        members[key] = {"name": name, "amount": amount, "until": until}
        print(f"Added {key} ({name}) at ${amount} a month, listed until {until}")
    else:
        # Keep anything Olly set by hand (name, url). An entry without "until" is listed until Olly removes it.
        entry["amount"] = amount
        if "until" in entry:
            entry["until"] = max(entry["until"], until)
        print(f"Updated {key} ({entry.get('name')}) at ${amount} a month, listed until {entry.get('until', 'removed by hand')}")

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(members, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()

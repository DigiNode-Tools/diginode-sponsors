#!/usr/bin/env python3
#
# Name:    kofi-membership.py
# Purpose: Handle a public Ko-fi payment, passed on by the DigiNode Tools Sponsors WordPress plugin on diginode.tools
#          (a repository_dispatch event, type kofi-membership). Run by the "Update sponsors" Action.
#            - A one-off donation, or the first payment of a monthly tier below Patron, is added to kofi-recent.json, for
#              Recent supporters on the sponsors page (recent-supporters.py).
#            - A Patron or Featured Sponsor payment adds or extends them in kofi-members.json.
#
#          The plugin only passes on public payments, with just: type, whether it's the first payment of a membership,
#          name, tier, amount, currency and timestamp (no email or message - Action logs in this repo are public).
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
RECENT_FILE = os.path.join(ROOT, "kofi-recent.json")
LISTED_DAYS = 35
RECENT_KEEP_DAYS = 120
# The listed tiers, from sponsor-info.json: (word to look for in the Ko-fi tier name, monthly dollars), Featured first
with open(os.path.join(ROOT, "sponsor-info.json"), encoding="utf-8") as _f:
    _tiers = json.load(_f)["tiers"]
TIERS = sorted(((t["name"].split()[0].lower(), t["monthly"]) for t in _tiers if t.get("listed")), key=lambda x: -x[1])
# The other monthly tiers (Supporter, Node Runner, Champion): (word to look for, tier name)
OTHER_TIERS = [(t["name"].split()[0].lower(), t["name"]) for t in _tiers if not t.get("listed")]


def clean_name(name):
    """The supporter's name, safe to show in markdown and HTML: letters, numbers, spaces and simple punctuation."""
    name = unicodedata.normalize("NFC", str(name or ""))
    name = "".join(c for c in name if c.isalnum() or c in " .,'&()-_")
    return re.sub(r"\s+", " ", name).strip()[:60]


def member_key(name):
    """The kofi-members.json key for a (cleaned) Ko-fi name."""
    slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()).strip("-")
    return "kofi-" + (slug[:30].strip("-") or hashlib.sha256(name.encode()).hexdigest()[:8])


def paid_at(payload):
    try:
        return datetime.datetime.fromisoformat(str(payload.get("timestamp")).replace("Z", "+00:00"))
    except ValueError:
        return datetime.datetime.now(datetime.UTC)


def record_recent(payload):
    """Add a one-off donation, or someone joining a monthly tier below Patron, to kofi-recent.json."""
    name = clean_name(payload.get("name"))
    kind = str(payload.get("type") or "")
    tier_name = str(payload.get("tier") or "").lower()
    if not name:
        return
    entry = {"name": name, "key": member_key(name), "time": int(paid_at(payload).timestamp())}
    if kind == "Donation":
        try:
            entry.update({"kind": "gift", "amount": round(float(payload.get("amount")), 2),
                          "currency": re.sub(r"[^A-Z]", "", str(payload.get("currency") or "USD"))[:3] or "USD"})
        except (TypeError, ValueError):
            return
    elif kind == "Subscription" and payload.get("first") and not any(word in tier_name for word, _ in TIERS):
        entry.update({"kind": "tier", "tier": next((n for word, n in OTHER_TIERS if word in tier_name), None)})
    else:
        return
    try:
        with open(RECENT_FILE, encoding="utf-8") as f:
            recent = json.load(f)
    except (OSError, ValueError):
        recent = {}
    cutoff = int(datetime.datetime.now(datetime.UTC).timestamp()) - RECENT_KEEP_DAYS * 86400
    items = [r for r in recent.get("recent", []) if r.get("time", 0) >= cutoff and r != entry] + [entry]
    recent = {"_comment": "Made by scripts/kofi-membership.py - recent public Ko-fi donations, and people who joined a "
                          "monthly tier below Patron, for Recent supporters (recent-supporters.py).",
              "recent": sorted(items, key=lambda r: -r["time"])[:50]}
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(recent, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Recent supporter: {name} ({entry['kind']})")


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

    record_recent(payload)
    if payload.get("type") == "Donation":
        return

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

    paid = paid_at(payload).date()
    until = (paid + datetime.timedelta(days=LISTED_DAYS)).isoformat()

    with open(FILE, encoding="utf-8") as f:
        members = json.load(f)

    entry = members.get(key)
    if amount == TIERS[0][1] and (entry is None or entry.get("amount", 0) < TIERS[0][1]) and os.environ.get("NEW_FEATURED_FILE"):
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

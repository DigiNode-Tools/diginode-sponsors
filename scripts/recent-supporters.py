#!/usr/bin/env python3
#
# Name:    recent-supporters.py
# Purpose: Build recent-supporters.json - "Recent supporters" on the diginode.tools/sponsors page. A mix of:
#            - people who started a monthly tier below Patron (Supporter, Node Runner, Champion), on GitHub Sponsors or
#              Ko-fi - Patrons and Featured Sponsors have their own places on the page
#            - one-time gifts worth at least recent.min_gift_usd: on GitHub Sponsors, Ko-fi, or in DGB
#          from the last recent.days days, newest first, at most recent.max (sponsor-info.json).
#
#          Only public supporters are listed: public GitHub sponsorships, public Ko-fi payments (the plugin only passes
#          those on), and DGB donations (shown by a shortened address). Each is shown by name, linked to their GitHub
#          profile, unless they chose otherwise in patron-settings.json (a name only, a nickname, "A supporter", not at
#          all, or without the amount). Monthly tiers are shown by name, never by amount.
#
# Input:   GitHub's API (SPONSORS_TOKEN, read:org and read:user - or GITHUB_NODES_FILE, a saved list of sponsorships, for
#          testing), kofi-recent.json, dgb-donate.json, patron-settings.json, sponsor-info.json
# Usage:   scripts/recent-supporters.py

import datetime
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG = "DigiNode-Tools"


def load(name, default):
    try:
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def github_sponsorships():
    """The latest sponsorships (current and ended, monthly and one-time), newest first."""
    if os.environ.get("GITHUB_NODES_FILE"):
        with open(os.environ["GITHUB_NODES_FILE"], encoding="utf-8") as f:
            return json.load(f)
    token = os.environ.get("SPONSORS_TOKEN")
    if not token:
        sys.exit("ERROR: no SPONSORS_TOKEN")
    query = f'''query {{ organization(login: "{ORG}") {{
        sponsorshipsAsMaintainer(first: 100, activeOnly: false, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
          nodes {{ createdAt privacyLevel isOneTimePayment tier {{ monthlyPriceInDollars isOneTime }}
                  sponsorEntity {{ ... on User {{ login name url }} ... on Organization {{ login name url }} }} }} }} }} }}'''
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        sys.exit("ERROR: " + "; ".join(e.get("message", "") for e in data["errors"]))
    return data["data"]["organization"]["sponsorshipsAsMaintainer"]["nodes"]


def main():
    info = load("sponsor-info.json", {})
    cfg = info["recent"]
    tiers = sorted(info["tiers"], key=lambda t: t["monthly"])
    patron_min = min(t["monthly"] for t in tiers if t.get("listed"))
    by_name = {t["name"]: t for t in tiers}
    settings = {k: v for k, v in load("patron-settings.json", {}).items() if not k.startswith("_")}
    now = int(time.time())
    since = now - cfg["days"] * 86400
    min_gift = cfg["min_gift_usd"]
    items = []

    def add(key, name, url, time_, tier=None, amount=None, source=""):
        s = settings.get(key, {})
        listing = s.get("listing", "linked")
        if listing == "hidden":
            return
        if listing == "nickname" and s.get("nickname"):
            name, url = s["nickname"], None
        elif listing == "anonymous":
            name, url = "A supporter", None
        elif listing == "name":
            url = None
        if s.get("hide_amount"):
            amount = None
        t = by_name.get(tier) if tier else None
        items.append({"name": name, "url": url, "source": source, "time": time_,
                      "tier": tier, "emoji": t["emoji"] if t else ("💠" if source == "DGB" else "☕" if source == "Ko-fi" else "💖"),
                      "amount": amount})

    # GitHub Sponsors
    for n in github_sponsorships():
        try:
            when = int(datetime.datetime.fromisoformat(n["createdAt"].replace("Z", "+00:00")).timestamp())
        except (KeyError, TypeError, ValueError):
            continue
        entity = n.get("sponsorEntity") or {}
        if when < since or n.get("privacyLevel") != "PUBLIC" or not entity.get("login"):
            continue
        price = (n.get("tier") or {}).get("monthlyPriceInDollars") or 0
        login, name = entity["login"], entity.get("name") or entity["login"]
        url = entity.get("url") or f"https://github.com/{login}"
        if n.get("isOneTimePayment") or (n.get("tier") or {}).get("isOneTime"):
            if price >= min_gift:
                add(login, name, url, when, amount=f"${price:,}", source="GitHub Sponsors")
        elif price < patron_min:
            tier = next((t["name"] for t in reversed(tiers) if t["monthly"] <= price), None)
            add(login, name, url, when, tier=tier, source="GitHub Sponsors")

    # Ko-fi
    for r in load("kofi-recent.json", {}).get("recent", []):
        if r.get("time", 0) < since:
            continue
        if r.get("kind") == "gift":
            if r.get("amount", 0) >= min_gift:   # Amounts in other currencies are taken as roughly dollars
                symbol = {"USD": "$", "GBP": "£", "EUR": "€"}.get(r.get("currency"), "")
                amount = f"{symbol}{r['amount']:,.0f}" + ("" if symbol else f" {r.get('currency', '')}")
                add(r.get("key", ""), r["name"], None, r["time"], amount=amount, source="Ko-fi")
        elif r.get("kind") == "tier":
            add(r.get("key", ""), r["name"], None, r["time"], tier=r.get("tier"), source="Ko-fi")

    # DGB
    dgb = load("dgb-donate.json", {})
    for r in dgb.get("recent", []):
        if r.get("time", 0) >= since and (r.get("usd") or 0) >= min_gift:
            add("", r.get("from") or "A DGB donor", None, r["time"],
                amount=f"{r['amount']:,.0f} DGB (≈ ${r['usd']:,.0f})", source="DGB")

    items.sort(key=lambda i: -i["time"])
    out = {
        "_comment": "Made by scripts/recent-supporters.py - don't edit. Recent supporters on the sponsors page.",
        "checked": datetime.datetime.fromtimestamp(now, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recent": items[:cfg["max"]],
    }
    path = os.path.join(ROOT, "recent-supporters.json")
    old = load("recent-supporters.json", {})
    # Only save when the list changed, or once a day, so readers can tell it's still being checked
    try:
        old_checked = datetime.datetime.strptime(old.get("checked", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()
    except ValueError:
        old_checked = 0
    if old.get("recent") != out["recent"] or now - old_checked > 86400:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print(f"Recent supporters: {len(out['recent'])}")


if __name__ == "__main__":
    main()

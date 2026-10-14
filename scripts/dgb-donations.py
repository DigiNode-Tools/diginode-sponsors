#!/usr/bin/env python3
#
# Name:    dgb-donations.py
# Purpose: Keep dgb-donate.json up to date: the DGB address to donate to now, its QR code for the terminal, and the
#          most recent donations (for "Thanks to recent DGB donors" on the sponsors page). Run by the "Update DGB
#          donations" Action. Everyone who shows a DGB donation address reads it from dgb-donate.json: the sponsors page
#          (the website plugin), DigiNode Tools (in the terminal) and the donation card image in the READMEs.
#
#          Addresses: if DGB_DONATION_XPUB is set (the extended public key of the Ledger "Donations" account - a secret,
#          never printed), the address is the first one in that account that hasn't received anything yet, so each
#          donation normally goes to a new address. Otherwise it's the fixed address in sponsor-info.json. Donations to
#          the fixed address are always counted too - older DigiNode Tools versions and older pages still show it.
#
#          Recent donations: up to dgb.recent_max, from the last dgb.recent_days, of at least dgb.min_donation DGB.
#          Each shows only the amount, a shortened sender address and when. Payments from the wallet's own addresses
#          (moving funds around) aren't counted.
#
#          Sources, tried in turn: cryptoid.info, the DigiByte Blockbook explorer, Blockchair. If all of them fail, the
#          last dgb-donate.json is kept (its "checked" time stops moving, and readers stop showing donations after a week).
#
# Usage:   scripts/dgb-donations.py [--dry-run]
#          Needs the qrcode Python package for the terminal QR code (pip install qrcode).

import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dgbaddr import receive_address  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dgb-donate.json")
UA = {"User-Agent": "Mozilla/5.0 (diginode-sponsors; +https://github.com/DigiNode-Tools/diginode-sponsors)"}
ADDR_RE = re.compile(r"^(dgb1[02-9ac-hj-np-z]{20,80}|D[1-9A-HJ-NP-Za-km-z]{25,40})$")
MAX_INDEX = 500   # Never look further into the account than this


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


# ------------------------------------------------------------------------------------------
# Sources. Each has: received(address) -> DGB ever received; payments(address) -> [(txid, unix time, DGB)];
# sender(txid) -> the first input's address. Any of them may raise; the next source is then tried.

class Cryptoid:
    name = "cryptoid.info"

    def received(self, a):
        return float(fetch(f"https://chainz.cryptoid.info/dgb/api.dws?q=getreceivedbyaddress&a={a}"))

    def payments(self, a):
        d = json.loads(fetch(f"https://chainz.cryptoid.info/explorer/address.summary.dws?coin=dgb&id={a}"))
        out, h, t = [], 0, 0
        for i, row in enumerate(d.get("tx", [])):
            # [id, txid, height, time, amount] - after the first row, height and time are offsets from the row before
            h, t = (row[2], row[3]) if i == 0 else (h + row[2], t + row[3])
            if row[4] > 0:   # Received (a negative amount would be money sent from the address)
                out.append((row[1].lower(), t, float(row[4])))
        return out

    def sender(self, txid):
        d = json.loads(fetch(f"https://chainz.cryptoid.info/dgb/api.dws?q=txinfo&t={txid}"))
        return (d.get("inputs") or [{}])[0].get("addr")


class Blockbook:
    name = "digibyteblockexplorer.com"
    base = "https://digibyteblockexplorer.com/api/v2"

    def _addr(self, a):
        return json.loads(fetch(f"{self.base}/address/{a}?details=txs&pageSize=200"))

    def received(self, a):
        return int(self._addr(a).get("totalReceived", "0")) / 1e8

    def payments(self, a):
        out = []
        for tx in self._addr(a).get("transactions", []):
            amt = sum(int(o.get("value", "0")) for o in tx.get("vout", []) if a in (o.get("addresses") or []))
            if amt:
                out.append((tx["txid"].lower(), int(tx.get("blockTime", 0)), amt / 1e8))
        return out

    def sender(self, txid):
        tx = json.loads(fetch(f"{self.base}/tx/{txid}"))
        return ((tx.get("vin") or [{}])[0].get("addresses") or [None])[0]


class Blockchair:
    name = "blockchair.com"

    def _addr(self, a):
        return json.loads(fetch(f"https://api.blockchair.com/digibyte/dashboards/address/{a}?transaction_details=true&limit=100"))["data"][a]

    def received(self, a):
        return self._addr(a)["address"]["received"] / 1e8

    def payments(self, a):
        out = []
        for tx in self._addr(a).get("transactions", []):
            if tx.get("balance_change", 0) > 0:
                when = datetime.datetime.strptime(tx["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.UTC)
                out.append((tx["hash"].lower(), int(when.timestamp()), tx["balance_change"] / 1e8))
        return out

    def sender(self, txid):
        d = json.loads(fetch(f"https://api.blockchair.com/digibyte/dashboards/transaction/{txid}"))["data"][txid]
        return (d.get("inputs") or [{}])[0].get("recipient")


SOURCES = [Cryptoid(), Blockbook(), Blockchair()]


def ask(method, *args):
    """Call method on each source in turn until one works. Returns (result, source name)."""
    errors = []
    for s in SOURCES:
        try:
            return getattr(s, method)(*args), s.name
        except Exception as e:   # noqa: BLE001 - any failure means try the next source
            errors.append(f"{s.name}: {type(e).__name__}")
            time.sleep(1)
    raise RuntimeError(f"{method} failed on every source ({'; '.join(errors)})")


# ------------------------------------------------------------------------------------------
# The terminal QR code: half-block characters, two rows of modules per line, with a quiet zone. Readers only accept
# these characters (and spaces).

def terminal_qr(text):
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    m = qr.get_matrix()
    if len(m) % 2:
        m.append([False] * len(m[0]))
    lines = []
    for y in range(0, len(m), 2):
        lines.append("".join("█" if a and b else "▀" if a else "▄" if b else " " for a, b in zip(m[y], m[y + 1])))
    return lines


def short(a):
    return f"{a[:5]}…{a[-3:]}" if a and ADDR_RE.match(a) else None


def main():
    dry = "--dry-run" in sys.argv
    with open(os.path.join(ROOT, "sponsor-info.json"), encoding="utf-8") as f:
        info = json.load(f)
    cfg = info["dgb"]
    fixed = info["dgb_address"]
    xpub = os.environ.get("DGB_DONATION_XPUB", "").strip()
    if xpub.startswith("{"):   # The whole of Ledger Live's account JSON was pasted - only its "xpub" is needed
        try:
            xpub = str(json.loads(xpub).get("xpub", "")).strip()
        except ValueError:
            sys.exit("ERROR: DGB_DONATION_XPUB isn't an extended public key or Ledger Live's account JSON")
    now = int(time.time())
    used_sources = set()

    # Which addresses? The fixed one, plus every used address in the Donations account and the first unused one.
    addresses, current = [fixed], fixed
    if xpub:
        for i in range(MAX_INDEX):
            a = receive_address(xpub, i)
            got, src = ask("received", a)
            used_sources.add(src)
            if got <= 0:
                current = a
                break
            addresses.append(a)
        else:
            sys.exit(f"ERROR: the first {MAX_INDEX} addresses have all been used")
    own = set(addresses) | {current}

    # Recent payments to any of them
    since = now - cfg["recent_days"] * 86400
    payments = {}
    for a in addresses:
        rows, src = ask("payments", a)
        used_sources.add(src)
        for txid, when, amount in rows:
            if when >= since and amount >= cfg["min_donation"]:
                p = payments.setdefault(txid, {"time": when, "amount": 0.0})
                p["amount"] += amount
    recent = []
    for txid, p in sorted(payments.items(), key=lambda kv: -kv[1]["time"]):
        if len(recent) >= cfg["recent_max"]:
            break
        try:
            frm, src = ask("sender", txid)
            used_sources.add(src)
        except RuntimeError:
            frm = None
        if frm in own:
            continue   # The wallet moving its own funds, not a donation
        recent.append({"amount": round(p["amount"], 2), "from": short(frm), "time": p["time"]})

    out = {
        "_comment": "Made by scripts/dgb-donations.py - don't edit. The DGB address to donate to now, its QR code for "
                    "the terminal, and the most recent donations.",
        "checked": datetime.datetime.fromtimestamp(now, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "address": current,
        "qr_terminal": terminal_qr(current),
        "recent": recent,
        "sources": sorted(used_sources),
    }
    if not ADDR_RE.match(current):
        sys.exit(f"ERROR: unexpected address format")
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if dry:
        print(text)
        return
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    same = {k: v for k, v in old.items() if k != "checked"} == {k: v for k, v in out.items() if k != "checked"}
    try:
        old_checked = datetime.datetime.strptime(old.get("checked", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()
    except ValueError:
        old_checked = 0
    # Only save when something changed - or once a day, so readers can tell it's still being checked
    if not same or now - old_checked > 86400:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text)
    changed = old.get("address") != current
    print(f"Address {'changed' if changed else 'unchanged'}; {len(recent)} recent donations; sources: {', '.join(sorted(used_sources))}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"address_changed={'yes' if changed else 'no'}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
#
# Name:    new-preview-code.py
# Purpose: Make a new code for Ko-fi members to join the Sponsors Preview. Shows it once on screen, for pasting into the
#          Ko-fi tiers' welcome messages, and writes only its fingerprint to access.json. Then commit and push access.json.
#          Everyone using the old code leaves the preview on their next update, until they enter the new one.
#
# Usage:   scripts/new-preview-code.py

import hashlib
import json
import os
import secrets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "access.json")
ALPHABET = "BCDFGHJKMNPQRSTVWXZ23456789"   # Nothing that can be misread or spell a word

code = "-".join("".join(secrets.choice(ALPHABET) for _ in range(5)) for _ in range(4))
with open(FILE, encoding="utf-8") as f:
    data = json.load(f)
data["preview"]["kofi_code_sha256"] = hashlib.sha256(f"diginode-preview:{code}".encode()).hexdigest()
with open(FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f"\nNew Sponsors Preview code for Ko-fi:\n\n    {code}\n\nIt isn't saved anywhere. access.json is updated: commit and push it.\n")

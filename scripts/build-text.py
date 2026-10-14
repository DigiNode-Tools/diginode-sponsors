#!/usr/bin/env python3
#
# Name:    build-text.py
# Purpose: Build everything that's made from sponsor-info.json - the one place where the sponsor information is kept:
#
#            snippets/pitch.md, helps.md, plans.md, tiers.md, tiers-all.md, dgb.md   the shared sponsor text (copied
#                                     into the READMEs and page-intro.md by sync-readmes.py)
#            .github/ISSUE_TEMPLATE/featured-sponsor.yml   the Become a Featured Sponsor form (its price)
#            platform-text.md         the text to paste into GitHub Sponsors and Ko-fi, which can't be updated
#                                     automatically. The Action opens an issue when it changes.
#
#          Run by the "Build sponsor text" Action whenever sponsor-info.json changes. To try it locally:
#          scripts/build-text.py && scripts/sync-readmes.py --local
#
# Usage:   scripts/build-text.py

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(ROOT, "sponsor-info.json"), encoding="utf-8") as f:
    info = json.load(f)

links = info["links"]
tiers = info["tiers"]
featured = next(t for t in tiers if t.get("listed") == "featured")
patron = next(t for t in tiers if t.get("listed") == "patron")
places = info["featured_places"]


def plain(md):
    """Markdown to plain text, for GitHub Sponsors tier descriptions and Ko-fi (no markdown there)."""
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", md)
    return md.replace("**", "")


def write(path, text):
    full = os.path.join(ROOT, path)
    old = open(full, encoding="utf-8").read() if os.path.exists(full) else None
    if old != text:
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Updated {path}")


def money(n):
    return f"${n:,}"


# ------------------------------------------------------------------------------------------
# Snippets (copied into the READMEs and page-intro.md by sync-readmes.py). Snippets can't hold comments - they're
# copied as they are - so the "made from sponsor-info.json" note is in snippets/README.md instead.

write("snippets/pitch.md", info["pitch"] + "\n")
write("snippets/helps.md", "\n".join(f"- {h}" for h in info["helps"]) + "\n")
write("snippets/plans.md", info["plans_intro"] + "\n\n" + "\n".join(f"- {p}" for p in info["plans"]) + "\n")

write("snippets/tiers.md",
      f"- **{patron['name']}** ({money(patron['monthly'])} a month): {patron['perk']}\n"
      f"- **{featured['name']}** ({money(featured['monthly'])} a month, only {places} places): {featured['perk']} "
      f"After sponsoring, [add your logo using this form]({links['featured_form']}) (on Ko-fi, give your Ko-fi name "
      f"in the form, or send me your logo, name and website in a Ko-fi message).\n")

rows = ["| Tier | Monthly | |", "|---|---|---|"]
for t in tiers:
    extra = f" Only {places} places." if t is featured else ""
    rows.append(f"| {t['emoji']} **{t['name']}** | {money(t['monthly'])} | {t['description']}{extra} |")
one = info["one_time"]
write("snippets/tiers-all.md", "\n".join(rows) + "\n\n"
      f"Or give once: {', '.join(money(n) for n in one['github'])} on GitHub Sponsors, "
      f"{', '.join(money(n) for n in one['kofi'])} on Ko-fi - or any amount you like on either.\n")

# The DGB address changes after each donation (see scripts/dgb-donations.py), so the address is never written out
# here: the card image is redrawn for the current address, and the sponsors page shows it as text to copy.
dgb_text = (f"Prefer to donate DGB? Scan the QR code. Each donation goes to a new address - to copy the current one, "
            f"see [{links['page'].replace('https://', '').rstrip('/')}]({links['page']}).")
dgb_img = f"<img src=\"{info['dgb_card']}\" alt=\"Donate DigiByte - scan the QR code\" width=\"600\">"
write("snippets/dgb.md", f"{dgb_text}\n\n{dgb_img}\n")

# ------------------------------------------------------------------------------------------
# The Become a Featured Sponsor form

form_path = ".github/ISSUE_TEMPLATE/featured-sponsor.yml"
with open(os.path.join(ROOT, form_path), encoding="utf-8") as f:
    form = f.read()
form = re.sub(r"description: Add your logo and link to DigiNode Tools \(for \$[\d,]+/month Featured Sponsors\)",
              f"description: Add your logo and link to DigiNode Tools (for {money(featured['monthly'])}/month Featured Sponsors)", form)
form = re.sub(r"at the \*\*\$[\d,]+ a month Featured Sponsor\*\* tier",
              f"at the **{money(featured['monthly'])} a month Featured Sponsor** tier", form)
write(form_path, form)

# ------------------------------------------------------------------------------------------
# platform-text.md - what to paste into GitHub Sponsors and Ko-fi

def block(text):
    return "```text\n" + text.strip() + "\n```"


gh_intro = f"""### Help me spend more time on DigiNode Tools

{info['pitch']}

**What your support pays for, and what I'm building next: [diginode.tools/sponsors]({links['page']})**

You can also support me on [Ko-fi]({links['kofi']}), with the same tiers.

#### Donate DigiByte

{dgb_text}

{dgb_img}

Thank you for your support!

Olly
[diginode.tools](https://diginode.tools) · [@diginode.tools on Bluesky](https://bsky.app/profile/diginode.tools) · [@olly.st on Bluesky](https://bsky.app/profile/olly.st)"""

kofi_about = (f"Hi, I'm Olly. {info['pitch']}\n\n"
              f"What your support pays for, and what I'm building next: {links['page'].replace('https://', '')}\n\n"
              f"You can also sponsor me on GitHub, with the same tiers: {links['github'].replace('https://', '')}\n\n"
              "Thank you!\nOlly")
if len(kofi_about) > 900:
    raise SystemExit(f"ERROR: the Ko-fi About text is {len(kofi_about)} characters - Ko-fi allows 900. Shorten the pitch.")

kofi_post = (f"{info['pitch']}\n\n"
             f"See what your support pays for, and what I'm building next: {links['page']}\n\n"
             "Donate DigiByte\n"
             f"Prefer to donate DGB? The address to send it to, with its QR code, is on the sponsors page: {links['page']}\n\n"
             f"You can also sponsor me on GitHub, with the same tiers: {links['github']}\n\n"
             "Thank you for your support!\nOlly")

out = [f"<!-- Made from sponsor-info.json by scripts/build-text.py - edit sponsor-info.json, not this file. -->",
       "# Text for GitHub Sponsors and Ko-fi",
       "",
       "GitHub Sponsors and Ko-fi can't be updated automatically, so this is the text to paste into them. When it "
       "changes, the **Build sponsor text** Action opens an issue saying what to update. Paste each box exactly as it is.",
       "",
       "## GitHub Sponsors",
       "",
       "[Profile](https://github.com/sponsors/DigiNode-Tools/dashboard/profile) > **Introduction** (markdown):",
       "",
       block(gh_intro),
       "",
       "[Sponsor tiers](https://github.com/sponsors/DigiNode-Tools/dashboard/tiers) - monthly tiers (name, price, description):",
       ""]
for t in tiers:
    name = f"{t['emoji']} {t['name']}" + (f" (only {places} places)" if t is featured else "")
    desc = plain(t["description"]) + (("\n\n" + t["github_extra"]) if t.get("github_extra") else "")
    out += [f"**{name}** - {money(t['monthly'])} a month", "", block(desc), ""]
out += [f"One-time tiers: {', '.join(money(n) for n in one['github'])} (plus a custom amount).", "",
        "## Ko-fi", "",
        "[Settings > Profile](https://ko-fi.com/settings) > **About you** (Ko-fi allows 900 characters):", "",
        block(kofi_about), "",
        "[Settings > Payment](https://ko-fi.com/settings?tab=payment) > **suggested amounts**: "
        f"{', '.join(str(n) for n in one['kofi'])} (US $).", "",
        "[Memberships](https://ko-fi.com/memberships/settings) - each tier (name, price, description, welcome message):", ""]
for t in tiers:
    desc = plain(t["description"])
    if t is featured:
        desc = f"Only {places} places. {desc}"
    if t.get("kofi_extra"):
        desc += " " + t["kofi_extra"]
    welcome = t.get("kofi_welcome", info["kofi_welcome"])
    limit = f" - tick **Limit number of people who can join** and set it to the number of free places (at most {places})" if t is featured else ""
    out += [f"**{t['emoji']} {t['name']}** - {money(t['monthly'])} a month{limit}", "",
            "Description:", "", block(desc), "", "Welcome message:", "", block(welcome), ""]
out += ["The pinned post (**Support DigiNode Tools**, with the Ko-fi banner as its image - not the DGB card, which would go out of date when the address changes):", "", block(kofi_post), ""]
write("platform-text.md", "\n".join(out))

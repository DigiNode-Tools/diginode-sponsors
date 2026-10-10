# Maintaining diginode-sponsors

Notes for Olly. The [README](README.md) is for sponsors.

(Premium Sponsors used to be called Featured Sponsors, which is why some files still say "featured".)

## What's where

| File | What it is |
|---|---|
| `snippets/` | **The shared sponsor text.** Edit it here and it's copied everywhere - see below. |
| `page-intro.md` | The text of the diginode.tools/sponsors page. **Edit this** to change it (except the parts between `sponsors:` markers, which come from `snippets/`). |
| `featured-approved.json` | Approved Premium Sponsors. Normally updated for you - see below. |
| `patron-settings.json` | Patrons who asked to be listed without a link, or not at all. Updated by the "Change how I'm listed" form. |
| `logos/` | Premium Sponsor logo cards (made by `scripts/make-card.py`). |
| `images/` | The "Your brand here" placeholder and the DGB donation QR code. |
| `sponsors.md` | Generated. The full sponsors page, embedded on diginode.tools/sponsors. |
| `featured.json` | Generated. The Premium Sponsors, read by DigiNode Setup, DigiNode Dashboard and the website plugin. |
| `slots/` | Generated. `premium-1.png` to `premium-3.png`: each a sponsor's logo card, or the placeholder. Shown in the DigiNode Tools README. |
| `sync.json` | The READMEs the shared sponsor text is copied into. |

## Actions

- **Update sponsors** - every day, and whenever `featured-approved.json`, `patron-settings.json` or `page-intro.md` changes on `main`. Rebuilds `sponsors.md`, `featured.json` and `slots/`, and reminds Premium Sponsors who haven't sent their logo.
- **Premium Sponsor request** (`featured-request.yml`) - checks the "Become a Premium Sponsor" form and opens a pull request.
- **Patron listing request** - handles the "Change how I'm listed" form. No approval needed.
- **Sync sponsor text** - copies `snippets/` into every README in `sync.json` whenever a snippet changes.

Anything that fails opens an issue here.

## Who is listed

- **Premium Sponsors** - sponsoring monthly at $300 or more, **and** approved in `featured-approved.json`. Shown on the diginode.tools home page and sponsors page, in the DigiNode Tools README, and in DigiNode Setup and DigiNode Dashboard. In the order they were approved.
- **Patrons** - sponsoring monthly at $100 or more. Listed on the sponsors page, linked to their GitHub profile unless they chose otherwise. (A $300 sponsor who hasn't been approved yet is listed here.)
- Private and one-time sponsors are never listed. People stop being listed when they stop sponsoring.

If the list hasn't been checked for 7 days (e.g. because the Action has stopped working), DigiNode Tools and the website stop showing Premium Sponsors, so nobody is shown after they stop paying.

## Approving a Premium Sponsor

Premium Sponsors fill in the **Become a Premium Sponsor** issue form. The Action checks:

- the GitHub account is actively sponsoring at $300+ a month, publicly (if it's an organisation, the person asking must be a public member of it)
- there's a place free (3 places; someone updating their own details doesn't need a new place)
- the name only uses safe characters, the website is an `https://` link, and the logo is a real PNG, JPG or WebP under 1 MB

If something's wrong, it replies on the issue explaining what. Editing the issue checks it again.

If everything is OK, it turns the logo into a card (the same size as all the others, on white) and opens a pull request adding it to `logos/` and their details to `featured-approved.json`. **Check the card and website in the pull request, then merge it.** Merging closes the issue and runs **Update sponsors**, so they appear within a few minutes. If you don't want to approve them, close the pull request, reply on the issue, and refund their sponsorship.

Public $300 sponsors who haven't been approved 3 days after sponsoring get one reminder issue, tagging them with the link to the form.

To remove a Premium Sponsor early, delete their entry from `featured-approved.json` (and their logo). Retire the $300 tier on GitHub while all 3 places are taken.

### Adding one by hand

Make a card from their logo (needs Pillow: `pip install pillow`), then add them to `featured-approved.json` using their GitHub login as the key:

```bash
scripts/make-card.py their-logo.png logos/their-github-login.png
```

```json
"their-github-login": {
  "name": "Example Exchange",
  "url": "https://example.com",
  "logo": "logos/their-github-login.png"
}
```

## The shared sponsor text

Text about sponsoring lives in `snippets/`, and is copied into the READMEs listed in `sync.json` (including this repo's README and `page-intro.md`) whenever it changes. Edit it once here, and everything else follows within a minute.

| Snippet | Used for |
|---|---|
| `badge.md` | The "Sponsor DigiNode Tools - Click to support me" button |
| `short.md` | The button and one line, at the top of most READMEs |
| `tiers.md` | The Patron and Premium Sponsor tiers |
| `become.md` | The button, the sponsor link and the tiers |
| `dgb.md` | The DGB address and QR code |
| `premium.md` | The Premium Sponsors row and button in the DigiNode Tools README |
| `support.md` | The "Sponsor DigiNode Tools" section of the DigiNode Tools README |

A snippet can include another one with `{{name}}`. A file says where a snippet goes with a pair of markers, and everything between them is replaced:

```markdown
<!-- sponsors:short -->
<!-- /sponsors:short -->
```

To add another README, add the markers to it and add it to `sync.json`. Files without markers are left alone. In `diginode-tools`, both `main` and `develop` are updated, so pull before editing its README.

Things that are **not** synced, so need changing by hand: the GitHub Sponsors page and tiers, the donation message in `diginode-setup.sh`, and the website home page.

Test it without changing anything: `scripts/sync-readmes.py --dry-run`. Fill in this repo's own files on disk: `scripts/sync-readmes.py --local`.

## The website

The diginode.tools website uses the **DigiNode Tools Sponsors** WordPress plugin (kept locally, not on GitHub). It reads `featured.json` and provides:

- `[diginode_premium_sponsors]` - the Premium Sponsors banner, used on the home page under the QR code. Options: `title="..."` and `heading="h3"`.
- `https://diginode.tools/premium-sponsor/1` (2 and 3) - the links on the logos in the DigiNode Tools README. They go to that sponsor's website, or to GitHub Sponsors if the place is free. The README can't change by itself, so this is how its links stay right.

The sponsors page embeds `sponsors.md`, which includes its own Premium Sponsors row.

## One-time setup

### The SPONSORS_TOKEN secret

All the Actions use a classic GitHub token saved as a repository secret called `SPONSORS_TOKEN`:

1. Go to **GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)** and create a token (or edit the existing `diginode-sponsors` one).
2. Choose **No expiration**, and tick **public_repo**, **read:org** and **read:user**. (`public_repo` is for copying the sponsor text into the other repos' READMEs.)
3. In this repo go to **Settings > Secrets and variables > Actions**, and save it as `SPONSORS_TOKEN`.

If the token stops working, the Actions fail and open an issue here. Create a new token and update the secret.

### Letting the Action open pull requests

GitHub blocks Actions from opening pull requests unless you allow it, first for the organisation and then for this repo (both done):

1. **DigiNode-Tools organisation > Settings > Actions > General > Workflow permissions**: tick **Allow GitHub Actions to create and approve pull requests**.
2. **This repo > Settings > Actions > General > Workflow permissions**: tick the same box.

## Running it yourself

```bash
scripts/update.sh                      # needs SPONSORS_TOKEN, or a gh login with read:org and read:user
scripts/update.sh --input test.json    # test with made-up sponsorships

# Check a request without GitHub: ISSUE_BODY is the issue text, SPONSORS_FILE is made-up sponsorships
ISSUE_AUTHOR=someone ISSUE_BODY="$(cat issue.md)" SPONSORS_FILE=test.json scripts/featured-request.sh
ISSUE_AUTHOR=someone ISSUE_BODY="$(cat issue.md)" SPONSORS_FILE=test.json scripts/patron-listing.sh
```

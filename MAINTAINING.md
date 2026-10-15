# Maintaining diginode-sponsors

Notes for Olly. The [README](README.md) has a summary.

## Changing the sponsor information

Everything about sponsoring - the pitch, what support pays for, the future plans, the tiers, prices and perks, the number of Featured places, the DGB address and the sponsors page cards - is kept in **one place: [`sponsor-info.json`](sponsor-info.json)**. Edit it and push. The **Build sponsor text** Action then:

1. runs `scripts/build-text.py`, which rebuilds the generated snippets (`pitch`, `helps`, `plans`, `tiers`, `tiers-all`, `dgb`), the price on the Become a Featured Sponsor form, and `platform-text.md`
2. fills in this repo's `page-intro.md` and copies the snippets into every README in `sync.json`
3. starts **Update sponsors**, which rebuilds `sponsors.md` (the diginode.tools/sponsors page)
4. if `platform-text.md` changed, opens an issue, **Update GitHub Sponsors and Ko-fi**, with what changed and a link to the text to paste. GitHub Sponsors and Ko-fi can't be updated automatically. They only carry short, stable text that points to diginode.tools/sponsors (no plans list), so this is mostly when a tier or price changes.

The scripts (`update.sh`, `featured-request.sh`, `kofi-membership.py`) and the website plugin read the prices and the number of Featured places from `sponsor-info.json` too, so nothing else needs changing. When a planned feature is finished, remove it from `plans` (and mention it in the release notes instead).

Try it locally first, if you like: `scripts/build-text.py && scripts/sync-readmes.py --local`, then look at `page-intro.md` and `platform-text.md`.

## What's where

| File | What it is |
|---|---|
| `sponsor-info.json` | **The one place the sponsor information is kept** - see above. |
| `platform-text.md` | Generated. The text to paste into GitHub Sponsors and Ko-fi. |
| `scripts/build-text.py` | Builds the generated snippets, the form's price and `platform-text.md` from `sponsor-info.json`. |
| `scripts/kofi-membership.py` | Adds or extends a Ko-fi member from a Ko-fi membership payment. Run by **Update sponsors**. |
| `snippets/` | The shared sponsor text, copied into the READMEs - see below. Some are generated from `sponsor-info.json`. |
| `page-intro.md` | The layout of the diginode.tools/sponsors page. The parts between `sponsors:` markers come from `snippets/`; edit the rest (e.g. how Featured Sponsors add their logo) here. |
| `featured-approved.json` | Approved Featured Sponsors. Normally updated for you - see below. |
| `kofi-members.json` | Ko-fi members at the Patron or Featured Sponsor tier, added automatically from Ko-fi (or by hand) - see below. |
| `patron-settings.json` | Patrons who asked to be listed without a link, or not at all. Updated by the "Change how I'm listed" form. |
| `logos/` | Featured Sponsor logo cards (made by `scripts/make-card.py`). |
| `images/` | The "Your brand here" placeholder, and the DGB donation images for the current address: `dgb-donation-qr.png` and `dgb-donation-card.png` (redrawn by the **Update DGB donations** Action whenever the address changes - don't edit them by hand), plus the logo they use. |
| `recent-supporters.json`, `kofi-recent.json` | **Generated** - Recent supporters on the sponsors page. See "Recent supporters" below. |
| `dgb-donate.json` | **Generated** by the **Update DGB donations** Action - the DGB address to donate to now, its QR code for the terminal, and the recent donations. See "DGB donations" below. |
| `sponsors.md` | Generated. The full sponsors page, embedded on diginode.tools/sponsors. |
| `featured.json` | Generated. The Featured Sponsors, read by DigiNode Setup, DigiNode Dashboard and the website plugin. |
| `slots/` | Generated. `featured-1.png` to `featured-3.png`: each a sponsor's logo card, or the placeholder. Shown in the DigiNode Tools README. |
| `sync.json` | The READMEs the shared sponsor text is copied into. |

## Actions

- **Build sponsor text** (`text.yml`) - whenever `sponsor-info.json` changes. See "Changing the sponsor information" above.
- **Update sponsors** - every day, whenever `featured-approved.json`, `patron-settings.json`, `kofi-members.json` or `page-intro.md` changes on `main`, and when Ko-fi sends a membership payment (adding the member first). Rebuilds `sponsors.md`, `featured.json` and `slots/`, and reminds Featured Sponsors who haven't sent their logo.
- **Featured Sponsor places** (part of **Update sponsors**) - opens an issue for you when all the places are taken (with a checklist to retire the Featured Sponsor tier on GitHub and unpublish it on Ko-fi, as neither can be capped across both), closes it and opens another when a place is free again, opens one when an approved Featured Sponsor stops sponsoring (still holding a place), and one when someone joins the Featured Sponsor tier on Ko-fi.
- **Featured Sponsor request** (`featured-request.yml`) - checks the "Become a Featured Sponsor" form and opens a pull request.
- **Patron listing request** - handles the "Change how I'm listed" form. No approval needed.
- **Sync sponsor text** - copies `snippets/` into every README in `sync.json` whenever a snippet changes.
- **Update DGB donations** (`dgb.yml`) - every 20 minutes. Finds the DGB address to donate to now and the recent donations, saves them in `dgb-donate.json`, and redraws the donation images when the address changes. See "DGB donations" below.

Anything that fails opens an issue here.

## Who is listed

- **Featured Sponsors** - sponsoring monthly at the Featured Sponsor tier's price or more, **and** approved in `featured-approved.json`. Shown on the diginode.tools home page and sponsors page, in the DigiNode Tools README, and in DigiNode Setup and DigiNode Dashboard. In the order they were approved.
- **Patrons** - sponsoring monthly at the Patron tier's price or more. Listed on the sponsors page, linked to their GitHub profile unless they chose otherwise. (A Featured Sponsor who hasn't been approved yet is listed here.)
- **Ko-fi members** at these tiers are listed too, automatically (`kofi-members.json`) - see below.
- Private and one-time sponsors are never listed. People stop being listed when they stop sponsoring.

If the list hasn't been checked for 7 days (e.g. because the Action has stopped working), DigiNode Tools and the website stop showing Featured Sponsors, so nobody is shown after they stop paying.

## Approving a Featured Sponsor

Featured Sponsors fill in the **Become a Featured Sponsor** issue form. The Action checks:

- the GitHub account is actively sponsoring at the Featured Sponsor tier or above, publicly (or, for Ko-fi, the Ko-fi name is a Featured member in `kofi-members.json`) (if it's an organisation, the person asking must be a public member of it)
- there's a place free (`featured_places` in `sponsor-info.json`; someone updating their own details doesn't need a new place)
- the name only uses safe characters, the website is an `https://` link, and the logo is a real PNG, JPG or WebP under 1 MB

If something's wrong, it replies on the issue explaining what. Editing the issue checks it again.

If everything is OK, it turns the logo into a card (the same size as all the others, on white) and opens a pull request adding it to `logos/` and their details to `featured-approved.json`. **Check the card and website in the pull request, then merge it.** Merging closes the issue and runs **Update sponsors**, so they appear within a few minutes. If you don't want to approve them, close the pull request, reply on the issue, and refund their sponsorship.

Public Featured-tier sponsors who haven't been approved 3 days after sponsoring get one reminder issue, tagging them with the link to the form.

To remove a Featured Sponsor early, delete their entry from `featured-approved.json` (and their logo). While all the places are taken, an issue reminds you to retire the tier on GitHub and unpublish it on Ko-fi.

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

## Ko-fi members

Patrons and Featured Sponsors who join on [Ko-fi](https://ko-fi.com/diginode) are listed automatically:

1. Ko-fi sends every payment to the **DigiNode Tools Sponsors** WordPress plugin on diginode.tools (Ko-fi's webhook).
2. The plugin checks Ko-fi's verification token, and passes on **public membership payments** to this repo (a `repository_dispatch` event, `kofi-membership`) with just the name, tier, amount, currency and time - never an email or message, as Action logs here are public. Private supporters aren't listed.
3. **Update sponsors** runs `scripts/kofi-membership.py`, which adds or extends them in `kofi-members.json`, then rebuilds the sponsors page.

Only the **Patron** and **Featured Sponsor** tiers are listed (matched by the Ko-fi tier name). Each monthly payment lists them until 35 days later, so they drop off about a month after their last payment - Ko-fi doesn't say when someone cancels. A Ko-fi **Featured Sponsor** is listed as a Patron until you approve them. They can use the **Become a Featured Sponsor** form too, giving their Ko-fi name: it's checked against `kofi-members.json` and opens a pull request as usual - before merging, check the GitHub account really is that Ko-fi supporter (e.g. they mention it in a Ko-fi message). Or, if they send their logo in a Ko-fi message, make their card and add them to `featured-approved.json` with the **same key** as in `kofi-members.json` (see "Adding one by hand" above). They take one of the places, so lower the Featured Sponsor tier's member limit on Ko-fi to match.

You can also edit `kofi-members.json` by hand, e.g. to add a `url` for someone's name (it's kept when they pay again), or to add someone yourself:

```json
"kofi-example": {"name": "Example Exchange", "url": "https://example.com", "amount": 300}
```

Leave out `until` to list someone until you remove them. To hide someone, add their key to `patron-settings.json` with `"listing": "hidden"`.

The plugin's **Settings > DigiNode Sponsors** page shows the last Ko-fi payments received and what happened to each.

### Setting up the Ko-fi webhook (one time)

1. **GitHub token:** GitHub > Settings > Developer settings > Fine-grained tokens > Generate new token. Resource owner **DigiNode-Tools**, **Only select repositories: diginode-sponsors**, permission **Contents: Read and write**, no expiry (or note the date). 
2. **Ko-fi token:** ko-fi.com > Settings > API > Advanced > copy the **Verification Token**.
3. In WordPress, **Settings > DigiNode Sponsors**: paste both tokens and save. Copy the **Ko-fi webhook URL** shown there.
4. On Ko-fi's API page, paste the URL into **Webhook URL**, save, and press **Send Single Donation Test**. It should appear under "Last Ko-fi payments received" as "Test payment from Ko-fi - received, not passed on".

### Renewing the GitHub token

The token (named **diginode-sponsors Ko-fi webhook**) expires after a year. When it does, Ko-fi payments show "GitHub error 401" in **Settings > DigiNode Sponsors**, and Ko-fi members stop being added. To renew it:

1. GitHub > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > **diginode-sponsors Ko-fi webhook** > **Regenerate token** (it keeps the same access) and copy the new token.
2. In WordPress, **Settings > DigiNode Sponsors**: paste it into **GitHub token** and save.

Ko-fi members who paid while it was expired are added again at their next monthly payment, or add them to `kofi-members.json` by hand.

## DGB donations

Each DGB donation should go to a new address. All of them are in the same Ledger account, so it all ends up in one wallet.

- **The Ledger account:** a Ledger Live account called **Donations** (DigiByte, Native SegWit). Its extended public key is the `DGB_DONATION_XPUB` repository secret. The key can only list the account's addresses - it can't spend anything - but it shows every address and payment, so keep it secret.
- **The Update DGB donations Action** works out the account's addresses from the key (`scripts/dgbaddr.py`), and checks them on the block explorers (`scripts/dgb-donations.py` - cryptoid.info first, then two others if it's down). The first address that hasn't received anything is the one to donate to now. It saves it in **`dgb-donate.json`**, with:
  - `qr_terminal` - its QR code for DigiNode Tools to show in the terminal
  - `recent` - the latest donations, for "Thanks to recent DGB donors" on the sponsors page: the amount, a shortened sender address and when. The limits are `dgb` in `sponsor-info.json`: the last 90 days, at least 50 DGB, at most 5.
- When the address changes, it redraws `images/dgb-donation-qr.png` and `images/dgb-donation-card.png` (`scripts/dgb-card.py`). Their links never change, so the card in the READMEs and on GitHub Sponsors is always for the current address.
- **Everything that shows the address reads `dgb-donate.json`:** the sponsors page (the website plugin), DigiNode Tools in the terminal, and the card. Never write the address anywhere by hand - it changes.
- **The original address** (`dgb_address` in `sponsor-info.json`, on the Ledger too) is used until `DGB_DONATION_XPUB` is set. Donations to it are always counted, as old versions of DigiNode Tools still show it.
- **Ledger Live only looks about 20 addresses ahead.** The Action always uses the first unused address, so this is normally fine. If a donation seems to be missing in Ledger Live, use **Receive** in the Donations account a few times to make it look further.

**Setting the key (one time):** in Ledger Live, open the Donations account > the wrench (Edit account) > **Advanced** > copy the key (xpub), then run `gh secret set DGB_DONATION_XPUB --repo DigiNode-Tools/diginode-sponsors` and paste it. Run the Action (Actions > Update DGB donations > Run workflow), and check the address in `dgb-donate.json` is the first one Ledger Live shows under **Receive**.

If the explorers are down, `dgb-donate.json` stays as it was. If it hasn't been checked for a day, the Action opens an issue. Readers stop showing recent donations once it's a week old.

## Recent supporters

The sponsors page shows **Patrons** in a strip at the top, and **Recent supporters** next to the tiers: people who started a monthly tier below Patron, and one-time gifts worth at least `recent.min_gift_usd` (on GitHub Sponsors, Ko-fi or in DGB), from the last `recent.days` days - the newest `recent.max` (`sponsor-info.json`).

- `scripts/recent-supporters.py` builds **`recent-supporters.json`** (run by **Update sponsors**: daily, after each Ko-fi payment, and when a new DGB donation arrives). It reads GitHub Sponsors (public sponsorships only), **`kofi-recent.json`** (public Ko-fi donations and new members, added by `kofi-membership.py`), and `dgb-donate.json` (DGB donations, with their dollar value on the day they were first seen).
- How each sponsor is shown comes from **`patron-settings.json`**: by name linked to GitHub (the default), name only, a nickname, "A supporter", without the amount, or not at all. GitHub sponsors - monthly or one-time, current or past - change it with the **Change how I'm listed** form. For a Ko-fi supporter who asks by message, add their Ko-fi key (from `kofi-members.json`, or `kofi-` + their name in lower case with dashes) by hand.
- Monthly tiers are shown by tier name, never by amount. Messages are never shown.

## The shared sponsor text

Text about sponsoring lives in `snippets/`, and is copied into the READMEs listed in `sync.json` (and this repo's `page-intro.md`) whenever it changes. The **generated** snippets are made from `sponsor-info.json` - edit that, not them, or your change is overwritten. The others (`badge`, `short`, `become`, `featured`, `support`) are edited here.

| Snippet | Used for |
|---|---|
| `badge.md` | The "Sponsor on GitHub" and "Support on Ko-fi" buttons |
| `short.md` | The buttons and one line, at the top of most READMEs |
| `become.md` | The buttons, the sponsor links and the tiers |
| `pitch.md`, `helps.md`, `plans.md` | **Generated** - the pitch, what support pays for, and "What I hope to work on next" |
| `tiers.md` | **Generated** - the Patron and Featured Sponsor tiers |
| `tiers-all.md` | **Generated** - every tier, for the sponsors page |
| `dgb.md` | **Generated** - the DGB donation card (never the address itself, as it changes) |
| `featured.md` | The Featured Sponsors row and button in the DigiNode Tools README |
| `support.md` | The "Sponsor DigiNode Tools" section of the DigiNode Tools README |

A snippet can include another one with `{{name}}`. A file says where a snippet goes with a pair of markers, and everything between them is replaced:

```markdown
<!-- sponsors:short -->
<!-- /sponsors:short -->
```

To add another README, add the markers to it and add it to `sync.json`. Files without markers are left alone. In `diginode-tools`, both `main` and `develop` are updated, so pull before editing its README.

Not synced: GitHub Sponsors and Ko-fi (paste from `platform-text.md` when an issue asks), the donation message in `diginode-setup.sh` (a short pitch and a link), and the website FAQ and home page (they only link to the sponsors page).

Test it without changing anything: `scripts/sync-readmes.py --dry-run`. Fill in this repo's own files on disk: `scripts/sync-readmes.py --local`.

## The website

The diginode.tools website uses the **DigiNode Tools Sponsors** WordPress plugin (kept locally, not on GitHub). It reads `featured.json` and provides:

- `[diginode_featured_sponsors]` - the Featured Sponsors banner, used on the home page under the QR code. Options: `title="..."` and `heading="h3"`.
- `https://diginode.tools/featured-sponsor/1` (2 and 3) - the links on the logos in the DigiNode Tools README. They go to that sponsor's website, or to the sponsors page if the place is free. The README can't change by itself, so this is how its links stay right.

The sponsors page embeds `sponsors.md`, which includes its own Featured Sponsors row. On the website, the plugin replaces the row of badges under "Become a sponsor" with a GitHub Sponsors card and a Ko-fi card; their text (and the number of Featured places) comes from `sponsor-info.json`.

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

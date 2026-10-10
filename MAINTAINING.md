# Maintaining diginode-sponsors

Notes for Olly. The [README](README.md) is for sponsors.

A GitHub Action (**Update sponsors**) checks the current sponsors every day, and whenever `featured-approved.json` or `page-intro.md` changes on `main`. It rebuilds `sponsors.md` and `featured.json`.

| File | What it is |
|---|---|
| `page-intro.md` | The text at the top of the diginode.tools/sponsors page. **Edit this** to change it. |
| `featured-approved.json` | Featured Sponsors you have approved. Normally updated for you - see below. |
| `logos/` | Logos for Featured Sponsors. |
| `sponsors.md` | Generated. The full sponsors page, embedded on diginode.tools/sponsors. The "Thank you to my sponsors" section appears once there are sponsors to list. |
| `featured.json` | Generated. The Featured Sponsors shown by DigiNode Setup and DigiNode Dashboard. |
| `images/` | The DGB donation QR code used on the page. |

## Who is listed

- **Featured Sponsors** - sponsoring monthly at $300 or more, **and** approved in `featured-approved.json`. Shown on the website and in DigiNode Tools.
- **Patrons** - sponsoring monthly at $100 or more. Listed on the website. (A $300 sponsor who hasn't been approved yet is listed here.)
- People who sponsor privately, or make one-time payments, are never listed. People stop being listed when they stop sponsoring.

If the list hasn't been checked for 7 days (e.g. because the Action has stopped working), DigiNode Tools stops showing Featured Sponsors, so nobody is shown after they stop paying.

## Approving a Featured Sponsor

Featured Sponsors fill in the **Become a Featured Sponsor** issue form. The **Featured Sponsor request** Action then checks:

- the GitHub account is actively sponsoring at $300+ a month, publicly (if it's an organisation, the person asking must be a public member of it)
- there's a place free (3 places; someone updating their own details doesn't need a new place)
- the name only uses safe characters, the website is an `https://` link, and the logo is a real PNG, JPG or WebP under 1 MB

If something's wrong, it replies on the issue explaining what. Editing the issue checks it again.

If everything is OK, it opens a pull request adding their logo to `logos/` and their details to `featured-approved.json`. **Check the logo and website in the pull request, then merge it.** Merging closes the issue and runs **Update sponsors**, so they appear within a few minutes. If you don't want to approve them, close the pull request, reply on the issue, and refund their sponsorship.

To remove a Featured Sponsor early, delete their entry from `featured-approved.json` (and their logo). Retire the $300 tier on GitHub while all 3 places are taken.

### Adding one by hand

Add their logo to `logos/`, then add them to `featured-approved.json`, using their GitHub login as the key:

```json
"their-github-login": {
  "name": "Example Exchange",
  "url": "https://example.com",
  "logo": "logos/their-github-login.png"
}
```

## One-time setup

### The SPONSORS_TOKEN secret

Both Actions need a GitHub token that can read DigiNode-Tools' sponsors, saved as a repository secret called `SPONSORS_TOKEN`:

1. Go to **GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token (classic)**.
2. Name it `diginode-sponsors`, choose **No expiration**, and tick only **read:org** and **read:user**.
3. Copy the token, then in this repo go to **Settings > Secrets and variables > Actions > New repository secret**. Name it `SPONSORS_TOKEN` and paste the token.

If the token stops working, **Update sponsors** fails and opens an issue here. Create a new token and update the secret.

### Letting the Action open pull requests

GitHub blocks Actions from opening pull requests unless you allow it, first for the organisation and then for this repo:

1. **DigiNode-Tools organisation > Settings > Actions > General > Workflow permissions**: tick **Allow GitHub Actions to create and approve pull requests**, and save.
2. **This repo > Settings > Actions > General > Workflow permissions**: tick the same box, and save.

The Action can only add files on its own branch. Nothing reaches `main` until you merge it.

## Running it yourself

```bash
scripts/update.sh                      # needs SPONSORS_TOKEN, or a gh login with read:org and read:user
scripts/update.sh --input test.json    # test with made-up sponsorships

# Check a request without GitHub: ISSUE_BODY is the issue text, SPONSORS_FILE is made-up sponsorships
ISSUE_AUTHOR=someone ISSUE_BODY="$(cat issue.md)" SPONSORS_FILE=test.json scripts/featured-request.sh
```

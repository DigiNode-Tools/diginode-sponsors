# DigiNode Tools sponsors

[![Sponsor DigiNode Tools](https://img.shields.io/badge/Sponsor-DigiNode%20Tools-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/DigiNode-Tools)

**Find this useful?** Please consider [sponsoring me on GitHub](https://github.com/sponsors/DigiNode-Tools), so I can devote more time to DigiNode Tools and projects like this one.

This repo keeps the list of [DigiNode Tools sponsors](https://github.com/sponsors/DigiNode-Tools) up to date for the [diginode.tools](https://diginode.tools) website and for DigiNode Tools itself. A GitHub Action checks the current sponsors every day.

| File | What it is |
|---|---|
| `page-intro.md` | The text at the top of the diginode.tools/sponsors page. **Edit this** to change it. |
| `featured-approved.json` | Featured Sponsors you have approved. **Edit this** - see below. |
| `logos/` | Logos for Featured Sponsors. |
| `sponsors.md` | Generated. The full sponsors page, embedded on diginode.tools/sponsors. The "Thank you to my sponsors" section appears once there are sponsors to list. |
| `featured.json` | Generated. The Featured Sponsors shown by DigiNode Setup and DigiNode Dashboard. |

## Who is listed

- **Featured Sponsors** - sponsoring monthly at $300 or more, **and** approved in `featured-approved.json`. Shown on the website and in DigiNode Tools.
- **Patrons** - sponsoring monthly at $100 or more. Listed on the website. (A $300 sponsor who hasn't been approved yet is listed here.)
- People who sponsor privately are never listed. People stop being listed when they stop sponsoring.

If the list hasn't been checked for 7 days (e.g. because the Action has stopped working), DigiNode Tools stops showing Featured Sponsors, so nobody is shown after they stop paying.

## Approving a Featured Sponsor

1. Add their logo to `logos/` (PNG or SVG, ideally on a transparent background).
2. Add them to `featured-approved.json`, using their GitHub username as the key:

   ```json
   "their-github-login": {
     "name": "Example Exchange",
     "url": "https://example.com",
     "logo": "logos/example.png"
   }
   ```

3. Run the Action from the **Actions** tab (**Update sponsors > Run workflow**), or wait for the next daily run.

If you don't approve someone, refund their sponsorship. Only 3 Featured places are available - retire the $300 tier on GitHub while they are all taken.

## The SPONSORS_TOKEN secret

The Action needs a GitHub token that can read DigiNode-Tools' sponsors, saved as a repository secret called `SPONSORS_TOKEN`:

1. Go to **GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token (classic)**.
2. Name it `diginode-sponsors`, choose an expiry (or **No expiration**), and tick only **read:org** and **read:user**.
3. Copy the token, then in this repo go to **Settings > Secrets and variables > Actions > New repository secret**. Name it `SPONSORS_TOKEN` and paste the token.

If the token expires, the Action fails and opens an issue here. Create a new token and update the secret.

## Running it yourself

```bash
scripts/update.sh                      # needs SPONSORS_TOKEN, or a gh login with read:org and read:user
scripts/update.sh --input test.json    # test with made-up sponsorships
```

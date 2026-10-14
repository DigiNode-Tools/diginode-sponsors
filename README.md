<p align="center"><a href="https://diginode.tools/sponsors/"><img src="https://raw.githubusercontent.com/DigiNode-Tools/diginode-media/main/sponsor/sponsor-banner.png" alt="Support DigiNode Tools - sponsor on GitHub Sponsors or Ko-fi, or donate DGB. diginode.tools/sponsors" width="900"></a></p>

<p align="center"><b><a href="https://diginode.tools/sponsors/">diginode.tools/sponsors</a></b> - what your support pays for, what I'm building next, the sponsor tiers, and how to donate DGB.</p>

---

# How this repo works

This repo is behind everything about sponsoring [DigiNode Tools](https://diginode.tools): the sponsors page, the sponsor text in the DigiNode Tools READMEs, the Featured Sponsors shown on the website and in DigiNode Tools, and the lists of sponsors. These notes are mostly for me (Olly). Full details are in [MAINTAINING.md](MAINTAINING.md).

## Changing anything: edit `sponsor-info.json`

[`sponsor-info.json`](sponsor-info.json) is the **one place** the sponsor information is kept: the pitch, what support pays for, the future plans, the tiers and prices, the perks, the DGB address, and the text on the sponsors page cards. Edit it on GitHub and commit, and the **Build sponsor text** Action does the rest, in a few minutes:

- rebuilds the shared text in `snippets/` and the sponsors page text (`page-intro.md`), and copies the text into the DigiNode Tools READMEs
- rebuilds [diginode.tools/sponsors](https://diginode.tools/sponsors/)
- updates the price on the Become a Featured Sponsor form - the scripts and the website plugin read the prices and the number of Featured places straight from `sponsor-info.json`
- if the text for **GitHub Sponsors** or **Ko-fi** changed, opens an issue with exactly what to paste into them ([`platform-text.md`](platform-text.md)) - they can't be updated automatically. They only carry short, stable text that points to the sponsors page, so this is rare: mainly when a tier or price changes.

When a planned feature is finished, remove it from `plans` (and mention it in the release notes instead).

## Where the sponsor information appears

| Where | Made from |
|---|---|
| [diginode.tools/sponsors](https://diginode.tools/sponsors/) | `page-intro.md` + the lists of sponsors, as `sponsors.md` (automatic) |
| The DigiNode Tools READMEs | `snippets/` (automatic, see `sync.json`) |
| Featured Sponsors on the website, in the READMEs and in DigiNode Tools | `featured.json` and `slots/` (automatic) |
| [GitHub Sponsors](https://github.com/sponsors/DigiNode-Tools) and [Ko-fi](https://ko-fi.com/diginode) | `platform-text.md` - pasted by hand when an issue asks |
| The website FAQ and home page | By hand - they only link to the sponsors page |

## Who is listed, and how

- **Featured Sponsors** (the top tier, with a limited number of places) are approved by me: they fill in the [Become a Featured Sponsor](https://github.com/DigiNode-Tools/diginode-sponsors/issues/new?template=featured-sponsor.yml) form, which is checked automatically and opens a pull request for me to merge. Ko-fi Featured Sponsors give their Ko-fi name in the form.
- **Patrons** are listed automatically, from GitHub Sponsors (every day) and from Ko-fi (within minutes, through Ko-fi's webhook and the website plugin).
- I'm told by an issue when all the Featured places are taken, when one is free again, when a Featured Sponsor stops sponsoring, and when someone joins the Featured tier on Ko-fi.

## Licence

Part of DigiNode Tools: free to use, and the code is public so anyone can see exactly what it does. Licensed under the [PolyForm Perimeter 1.0.0](LICENCE.md) licence, which doesn't allow it to be used to make a competing product - see the [Licence FAQ](https://github.com/DigiNode-Tools/diginode-tools/blob/main/docs/licence_faq.md). The DigiNode Tools name and logo are covered by [TRADEMARKS.md](https://github.com/DigiNode-Tools/diginode-tools/blob/main/TRADEMARKS.md).

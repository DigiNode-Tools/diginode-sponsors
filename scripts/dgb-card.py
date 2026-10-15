#!/usr/bin/env python3
#
# Name:    dgb-card.py
# Purpose: Draw the DGB donation images for the current donation address (from dgb-donate.json):
#            images/dgb-donation-qr.png    the address as a dotted QR code with the DigiNode Tools badge in the middle
#            images/dgb-donation-card.png  the "Donate DigiByte" card (1200x630) with that QR code and the address
#            images/dgb-donation-qr-simple.png  a plain QR code with the DigiByte logo in the middle - easier to scan when
#                                          small (the website's home page)
#          Their addresses (URLs) never change, so everything showing them - the READMEs, GitHub Sponsors - follows the
#          address as it changes. Run by the "Update DGB donations" Action when the address changes.
#
# Usage:   scripts/dgb-card.py        Needs the qrcode Python package and Google Chrome (or set CHROME).

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

import qrcode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "images")
LOGO = os.path.join(IMAGES, "diginode-logo-round.png")
DGB_LOGO = os.path.join(IMAGES, "digibyte-logo.svg")
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,500;0,600;0,800;1,800'
         '&family=JetBrains+Mono:wght@500&display=block">')


def chrome():
    for c in (os.environ.get("CHROME"), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if c and (shutil.which(c) or os.path.exists(c)):
            return shutil.which(c) or c
    sys.exit("ERROR: Google Chrome not found (set CHROME)")


def screenshot(html, width, height, out):
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "page.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        subprocess.run([chrome(), "--headless", "--hide-scrollbars", "--no-sandbox", "--disable-gpu",
                        "--virtual-time-budget=15000", f"--window-size={width},{height}", f"--screenshot={out}",
                        "file://" + page], check=True, capture_output=True)


def qr_html(address):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    qr.add_data(address)
    qr.make(fit=True)
    grid = qr.get_matrix()
    n = len(grid)
    M, QUIET, BADGE = 30, 2, 11                      # px per module, quiet zone, badge diameter (modules)
    size = (n + 2 * QUIET) * M
    c = n / 2
    finder = lambda x, y: x < 7 and y < 7 or x >= n - 7 and y < 7 or x < 7 and y >= n - 7
    in_badge = lambda x, y: (x + 0.5 - c) ** 2 + (y + 0.5 - c) ** 2 <= (BADGE / 2 + 0.6) ** 2
    dots = [f'<circle cx="{(x + QUIET + .5) * M}" cy="{(y + QUIET + .5) * M}" r="{M * .43:.1f}"/>'
            for y in range(n) for x in range(n) if grid[y][x] and not finder(x, y) and not in_badge(x, y)]
    for fx, fy in [(0, 0), (n - 7, 0), (0, n - 7)]:
        cx, cy = (fx + QUIET + 3.5) * M, (fy + QUIET + 3.5) * M
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="{3 * M}" fill="none" stroke="#000" stroke-width="{M}"/>')
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="{1.5 * M}"/>')
    cx = cy = size / 2
    R = BADGE / 2 * M
    ring = R * 0.30
    tr, inner, font = R - ring / 2, R - ring, ring * 0.52
    logo = base64.b64encode(open(LOGO, "rb").read()).decode()
    badge = f'''<circle cx="{cx}" cy="{cy}" r="{R}" fill="#0066CC"/>
<defs><path id="top" d="M {cx - tr} {cy} A {tr} {tr} 0 0 1 {cx + tr} {cy}"/><path id="bottom" d="M {cx - tr} {cy} A {tr} {tr} 0 0 0 {cx + tr} {cy}"/>
<clipPath id="clip"><circle cx="{cx}" cy="{cy}" r="{inner}"/></clipPath></defs>
<g fill="#fff" font-family="Nunito Sans, sans-serif" font-weight="800" font-size="{font:.1f}" letter-spacing="2">
<text dominant-baseline="central"><textPath href="#top" startOffset="50%" text-anchor="middle">DIGINODE TOOLS</textPath></text>
<text dominant-baseline="central"><textPath href="#bottom" startOffset="50%" text-anchor="middle">DONATE DGB</textPath></text></g>
<image href="data:image/png;base64,{logo}" x="{cx - inner}" y="{cy - inner}" width="{2 * inner}" height="{2 * inner}" clip-path="url(#clip)"/>'''
    html = (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>*{{margin:0}}html,body{{width:{size}px;height:{size}px;'
            f'overflow:hidden;background:#fff}}</style></head><body><svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
            f'height="{size}" viewBox="0 0 {size} {size}"><rect width="{size}" height="{size}" fill="#fff"/>'
            f'<g fill="#000">{"".join(dots)}</g>{badge}</svg></body></html>')
    return html, size


def simple_qr_html(address):
    """Square modules, a 2-module quiet zone, and the DigiByte logo (with a white ring) in the middle."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    qr.add_data(address)
    qr.make(fit=True)
    grid = qr.get_matrix()
    n = len(grid)
    M, QUIET, LOGO_D = 12, 2, 9                    # px per module, quiet zone, logo diameter (modules)
    size = (n + 2 * QUIET) * M
    c = n / 2
    clear = lambda x, y: (x + 0.5 - c) ** 2 + (y + 0.5 - c) ** 2 <= (LOGO_D / 2 + 0.8) ** 2
    rects = [f'<rect x="{(x + QUIET) * M}" y="{(y + QUIET) * M}" width="{M}" height="{M}"/>'
             for y in range(n) for x in range(n) if grid[y][x] and not clear(x, y)]
    d = LOGO_D * M
    logo = base64.b64encode(open(DGB_LOGO, "rb").read()).decode()
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:{size}px;height:{size}px;'
            f'overflow:hidden;background:#fff}}</style></head><body><svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
            f'height="{size}" viewBox="0 0 {size} {size}" shape-rendering="crispEdges"><rect width="{size}" height="{size}" fill="#fff"/>'
            f'<g fill="#000">{"".join(rects)}</g>'
            f'<image href="data:image/svg+xml;base64,{logo}" x="{(size - d) / 2}" y="{(size - d) / 2}" width="{d}" height="{d}"/>'
            f'</svg></body></html>'), size


def card_html(address, qr_png):
    half = (len(address) + 1) // 2
    qr = base64.b64encode(open(qr_png, "rb").read()).decode()
    return f'''<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1200px;height:630px;overflow:hidden}}
body{{font-family:"Nunito Sans",sans-serif;color:#fff;background:radial-gradient(circle at 20% 30%,#0b3a7a 0%,#002352 55%,#001631 100%)}}
.qr{{position:absolute;left:56px;top:38px;width:476px;height:476px;background:#fff;border-radius:22px;overflow:hidden}}
.qr img{{display:block;width:476px;height:476px}}
.name{{font-weight:800;font-style:italic;letter-spacing:-1px;line-height:1}}
.sub{{color:#9cc8ff;font-weight:500}}
.addr{{font-family:"JetBrains Mono",monospace;font-size:30px;color:#fff;background:rgba(255,255,255,.08);border:2px solid rgba(156,200,255,.35);border-radius:14px;padding:16px 20px;line-height:1.35}}
.bar{{background:#0066CC}}
.url{{color:#cfe4ff;font-weight:600;letter-spacing:.5px}}
</style></head><body>
<div class="qr"><img src="data:image/png;base64,{qr}"></div>
<div style="position:absolute;left:590px;top:70px;right:50px">
 <div class="name" style="font-size:76px">Donate DigiByte</div>
 <div class="sub" style="font-size:31px;margin-top:22px">Support DigiNode Tools with DGB.<br>Scan the QR code, or send it to:</div>
 <div class="addr" style="margin-top:28px">{address[:half]}<br>{address[half:]}</div>
</div>
<div class="bar" style="position:absolute;left:0;right:0;bottom:0;height:78px"></div>
<div class="url" style="position:absolute;left:0;right:0;bottom:20px;text-align:center;font-size:32px">Thank you! &nbsp;·&nbsp; diginode.tools/sponsors</div>
</body></html>'''


def main():
    with open(os.path.join(ROOT, "dgb-donate.json"), encoding="utf-8") as f:
        address = json.load(f)["address"]
    html, size = qr_html(address)
    qr_png = os.path.join(IMAGES, "dgb-donation-qr.png")
    screenshot(html, size, size, qr_png)
    screenshot(card_html(address, qr_png), 1200, 630, os.path.join(IMAGES, "dgb-donation-card.png"))
    html, size = simple_qr_html(address)
    screenshot(html, size, size, os.path.join(IMAGES, "dgb-donation-qr-simple.png"))
    print(f"Drew the donation images for {address[:8]}...")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Turn a Featured Sponsor's logo into a "card": their logo, centred on a white rounded rectangle, always the same size.
The cards are what the website, the DigiNode Tools README and the sponsors page show, so every logo looks consistent,
and re-drawing the image also strips anything in the original file that isn't the picture itself.

Usage:  make-card.py LOGO OUTPUT.png
        make-card.py --placeholder OUTPUT.png FONT_BOLD.ttf FONT_REGULAR.ttf

Exits with 2 and a message for the sponsor if the logo can't be used.
"""

import sys
from PIL import Image, ImageDraw, ImageFont

# Drawn at 2x, so they stay sharp on high resolution screens. They are shown at 300 x 100.
WIDTH, HEIGHT = 1200, 400
LOGO_BOX = (1040, 280)      # The space the logo is fitted into
RADIUS = 40
BORDER = "#d0d7de"
MAX_UPSCALE = 3             # Small logos are enlarged, but not so much they go blurry
MIN_LOGO_WIDTH = 150
MAX_PIXELS = 40_000_000

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def blank_card(dashed=False):
    card = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    if dashed:
        draw.rounded_rectangle((0, 0, WIDTH - 1, HEIGHT - 1), RADIUS, fill="#f6f8fa")
        # Dashed border: draw the solid border, then cut gaps into the straight edges
        draw.rounded_rectangle((2, 2, WIDTH - 3, HEIGHT - 3), RADIUS, outline="#8c959f", width=4)
        for x in range(RADIUS + 20, WIDTH - RADIUS, 40):
            draw.rectangle((x, 0, x + 14, 8), fill="#f6f8fa")
            draw.rectangle((x, HEIGHT - 9, x + 14, HEIGHT - 1), fill="#f6f8fa")
        for y in range(RADIUS + 20, HEIGHT - RADIUS, 40):
            draw.rectangle((0, y, 8, y + 14), fill="#f6f8fa")
            draw.rectangle((WIDTH - 9, y, WIDTH - 1, y + 14), fill="#f6f8fa")
    else:
        draw.rounded_rectangle((0, 0, WIDTH - 1, HEIGHT - 1), RADIUS, fill="white", outline=BORDER, width=3)
    return card


def make_card(logo_path, out_path):
    try:
        logo = Image.open(logo_path)
        if logo.format not in ("PNG", "JPEG", "WEBP"):
            fail("The logo must be a PNG, JPG or WebP image.")
        logo.load()
    except Image.DecompressionBombError:
        fail("The logo image is far too large. Please upload a smaller version.")
    except SystemExit:
        raise
    except Exception:
        fail("The logo couldn't be read as an image. Please upload a PNG, JPG or WebP.")

    if logo.width < MIN_LOGO_WIDTH:
        fail(f"The logo is too small ({logo.width} pixels wide). Please upload a larger version, ideally at least 400 pixels wide.")

    logo = logo.convert("RGBA")
    # Trim any empty transparent border, so the logo fills the card
    bbox = logo.getchannel("A").getbbox()
    if not bbox:
        fail("The logo is completely transparent.")
    logo = logo.crop(bbox)

    scale = min(LOGO_BOX[0] / logo.width, LOGO_BOX[1] / logo.height, MAX_UPSCALE)
    logo = logo.resize((max(1, round(logo.width * scale)), max(1, round(logo.height * scale))), Image.LANCZOS)

    card = blank_card()
    card.alpha_composite(logo, ((WIDTH - logo.width) // 2, (HEIGHT - logo.height) // 2))
    card.save(out_path, "PNG", optimize=True)


def make_placeholder(out_path, bold_font, regular_font):
    card = blank_card(dashed=True)
    draw = ImageDraw.Draw(card)
    title = ImageFont.truetype(bold_font, 92)
    subtitle = ImageFont.truetype(regular_font, 52)
    draw.text((WIDTH / 2, HEIGHT / 2 - 40), "Your brand here", font=title, fill="#002352", anchor="mm")
    draw.text((WIDTH / 2, HEIGHT / 2 + 70), "Become a Featured Sponsor", font=subtitle, fill="#0066cc", anchor="mm")
    card.save(out_path, "PNG", optimize=True)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--placeholder":
        make_placeholder(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 3:
        make_card(sys.argv[1], sys.argv[2])
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

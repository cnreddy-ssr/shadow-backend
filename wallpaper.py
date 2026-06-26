"""
SHADOW. Wallpaper Generator
Desktop: 4092x2160  |  Phone: 1440x3120

Text layout (3 elements):
  salutation  — small Quicksand Light, faded
  heading     — large Michroma, full opacity (replaces SHADOW.)
  tagline     — small Michroma, matched width to heading (replaces UNCONDITIONAL LOYALTY)

Customer input format in customText field: "salutation|heading|tagline"
e.g. "Dear|Rahul|Always in our hearts"
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, os, base64, math
import urllib.request

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

DESKTOP_W, DESKTOP_H = 4092, 2160
PHONE_W,   PHONE_H   = 1440, 3120

ACCENT_COLORS = {
    "Gold":       "#c9a84c",
    "Red":        "#e05c5c",
    "White":      "#f5f5f0",
    "Sage Green": "#a8d8a8",
    "Steel Blue": "#b0c4de",
}
BG_COLORS = {
    "Dark Black": "#0a0a0a",
    "White":      "#ffffff",
    "Beige":      "#f5f0e8",
    "Deep Blue":  "#1a2035",
    "Midnight":   "#1a1a2e",
    "Warm Brown": "#2d1a0e",
}

# ── Font download on startup ──────────────────────────────────────────────────

def ensure_fonts():
    os.makedirs(FONTS_DIR, exist_ok=True)
    fonts = {
        "Michroma-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/michroma/Michroma-Regular.ttf",
        "Quicksand-Light.ttf":  "https://fonts.gstatic.com/s/quicksand/v37/6xK-dSZaM9iE8KbpRA_LJ3z8mH9BOJvgkKEo58a-xw.ttf",
    }
    for fname, url in fonts.items():
        fpath = os.path.join(FONTS_DIR, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000:
            print(f"Downloading font: {fname}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                with open(fpath, "wb") as f:
                    f.write(r.read())

ensure_fonts()

# ── Helpers ───────────────────────────────────────────────────────────────────

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def load_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except:
        return ImageFont.load_default()

def feather_edges(img, feather_px):
    """Feather all 4 edges using cosine curve + Gaussian blur."""
    w, h = img.size
    fp   = max(1, feather_px)
    mask = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(mask)
    for i in range(fp):
        t = i / fp
        a = int(255 * (0.5 - 0.5 * math.cos(math.pi * t)))
        draw.line([(i, 0),     (i, h)],     fill=a)
        draw.line([(w-1-i, 0), (w-1-i, h)], fill=a)
        draw.line([(0, i),     (w, i)],     fill=a)
        draw.line([(0, h-1-i), (w, h-1-i)], fill=a)
    mask = mask.filter(ImageFilter.GaussianBlur(fp * 0.6))
    out  = img.copy().convert("RGBA")
    out.putalpha(mask)
    return out

def crop_fill(img, target_w, target_h):
    """Scale image to fill target dimensions, center-crop."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)
    left  = (new_w - target_w) // 2
    top   = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))

def matching_font_size(ref_font, ref_text, target_text, font_name):
    """Return font sized so target_text width == ref_text width."""
    tb = ref_font.getbbox(ref_text)
    ref_w = tb[2] - tb[0]
    lo, hi = 8, 400
    for _ in range(24):
        mid  = (lo + hi) // 2
        f    = load_font(font_name, mid)
        fb   = f.getbbox(target_text)
        if (fb[2] - fb[0]) < ref_w:
            lo = mid
        else:
            hi = mid
    return load_font(font_name, lo)

def parse_text(custom_text):
    """
    Parse 'salutation|heading|tagline' → (salutation, heading, tagline)
    All parts optional. heading is required for any text to appear.
    """
    parts = [p.strip() for p in (custom_text or "").split("|")]
    while len(parts) < 3:
        parts.append("")
    return parts[0], parts[1], parts[2]

def photo_from_base64(data_url):
    header, encoded = data_url.split(",", 1)
    return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")

def image_to_bytes(img, quality=92):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf.read()


# ── DESKTOP ───────────────────────────────────────────────────────────────────

def generate_desktop(photo_img, template, custom_text, bg_color, accent_color):
    bg_rgb  = hex_to_rgb(BG_COLORS.get(bg_color,  "#0a0a0a"))
    acc_rgb = hex_to_rgb(ACCENT_COLORS.get(accent_color, "#c9a84c"))

    canvas = Image.new("RGB", (DESKTOP_W, DESKTOP_H), bg_rgb)

    # Photo: left ~55%, vertically centered, feathered
    max_pw = int(DESKTOP_W * 0.55)
    photo  = photo_img.copy()
    photo.thumbnail((max_pw, DESKTOP_H), Image.LANCZOS)
    pw, ph     = photo.size
    photo_f    = feather_edges(photo, int(min(pw, ph) * 0.10))
    canvas.paste(photo_f, (0, (DESKTOP_H - ph) // 2), photo_f)

    if template == "photo-only":
        return canvas

    salutation, heading, tagline = parse_text(custom_text)
    if not heading:
        return canvas

    # Fonts
    heading_size    = 190
    salutation_size = 84
    heading_font    = load_font("Michroma-Regular.ttf",  heading_size)
    salutation_font = load_font("Quicksand-Light.ttf",   salutation_size)
    tagline_font    = matching_font_size(heading_font, heading, tagline, "Michroma-Regular.ttf") if tagline else None

    # Text block x: right of photo
    text_x = pw + 340
    hb     = heading_font.getbbox(heading)
    if text_x + (hb[2] - hb[0]) > DESKTOP_W - 80:
        text_x = pw + 80

    # Measure block height
    sal_line_h  = (salutation_font.getbbox("Ag")[3] - salutation_font.getbbox("Ag")[1] + 24) if salutation else 0
    head_full_h = heading_font.getbbox(heading)[3] + 28   # full glyph bottom + gap
    tag_line_h  = (tagline_font.getbbox(tagline)[3] - tagline_font.getbbox(tagline)[1]) if tagline and tagline_font else 0
    block_h     = sal_line_h + head_full_h + tag_line_h

    # Vertically center
    cur_y = (DESKTOP_H - block_h) // 2
    draw  = ImageDraw.Draw(canvas, "RGBA")

    # Salutation
    if salutation:
        draw.text((text_x, cur_y), salutation, font=salutation_font,
                  fill=(*acc_rgb, 133))
        cur_y += sal_line_h

    # Main heading
    draw.text((text_x, cur_y), heading, font=heading_font,
              fill=(*acc_rgb, 255))
    cur_y += head_full_h

    # Tagline
    if tagline and tagline_font:
        draw.text((text_x, cur_y), tagline, font=tagline_font,
                  fill=(*acc_rgb, 200))

    return canvas


# ── PHONE ─────────────────────────────────────────────────────────────────────

def generate_phone(photo_img, template, custom_text, bg_color, accent_color):
    bg_rgb  = hex_to_rgb(BG_COLORS.get(bg_color,  "#0a0a0a"))
    acc_rgb = hex_to_rgb(ACCENT_COLORS.get(accent_color, "#c9a84c"))

    canvas = Image.new("RGB", (PHONE_W, PHONE_H), bg_rgb)

    # Photo: crop-fill top 60%, shifted down 20%
    photo_zone_h = int(PHONE_H * 0.60)
    photo        = crop_fill(photo_img.copy(), PHONE_W, photo_zone_h)
    photo_f      = feather_edges(photo, int(min(PHONE_W, photo_zone_h) * 0.12))
    canvas.paste(photo_f, (0, int(PHONE_H * 0.20)), photo_f)

    if template == "photo-only":
        return canvas

    salutation, heading, tagline = parse_text(custom_text)
    if not heading:
        return canvas

    # Fonts
    heading_size    = 116
    salutation_size = 58
    heading_font    = load_font("Michroma-Regular.ttf", heading_size)
    salutation_font = load_font("Quicksand-Light.ttf",  salutation_size)
    tagline_font    = matching_font_size(heading_font, heading, tagline, "Michroma-Regular.ttf") if tagline else None

    draw = ImageDraw.Draw(canvas, "RGBA")

    # Heading block starts at 82% of canvas
    hb        = heading_font.getbbox(heading)
    heading_w = hb[2] - hb[0]
    heading_x = (PHONE_W - heading_w) // 2
    heading_y = int(PHONE_H * 0.82)

    # Salutation sits above heading
    sal_line_h = 0
    if salutation:
        sb         = salutation_font.getbbox("Ag")
        sal_line_h = sb[3] - sb[1] + 20
        sal_y      = heading_y - sal_line_h
        draw.text((heading_x, sal_y), salutation, font=salutation_font,
                  fill=(*acc_rgb, 133))

    # Main heading
    draw.text((heading_x, heading_y), heading, font=heading_font,
              fill=(*acc_rgb, 255))

    # Tagline below heading
    if tagline and tagline_font:
        head_full_h = hb[3] + 20
        tag_y       = heading_y + head_full_h
        tb          = tagline_font.getbbox(tagline)
        tag_w       = tb[2] - tb[0]
        tag_x       = heading_x + (heading_w - tag_w) // 2
        draw.text((tag_x, tag_y), tagline, font=tagline_font,
                  fill=(*acc_rgb, 200))

    return canvas


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

def generate_wallpapers(photo_data_url, template, custom_text,
                        bg_color, accent_color, formats):
    photo   = photo_from_base64(photo_data_url)
    results = {}
    if "Desktop" in formats:
        results["Desktop"] = image_to_bytes(
            generate_desktop(photo, template, custom_text, bg_color, accent_color))
    if "Phone" in formats:
        results["Phone"] = image_to_bytes(
            generate_phone(photo, template, custom_text, bg_color, accent_color))
    return results

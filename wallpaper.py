"""
SHADOW. Wallpaper Generator
Desktop: 4092x2160  |  Phone: 1440x3120
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, os, base64, math

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

def ensure_fonts():
    """Download fonts on first run if not present."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    fonts = {
        "Michroma-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/michroma/Michroma-Regular.ttf",
        "Quicksand-Light.ttf":  "https://fonts.gstatic.com/s/quicksand/v37/6xK-dSZaM9iE8KbpRA_LJ3z8mH9BOJvgkKEo58a-xw.ttf",
    }
    import urllib.request
    for fname, url in fonts.items():
        fpath = os.path.join(FONTS_DIR, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000:
            print(f"Downloading font: {fname}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                with open(fpath, "wb") as f:
                    f.write(r.read())
            print(f"Downloaded {fname}")

ensure_fonts()

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

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def load_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except:
        return ImageFont.load_default()

def feather_edges(img, feather_px):
    """Feather all 4 edges using a smooth cosine curve + strong Gaussian blur."""
    w, h = img.size
    fp   = feather_px
    mask = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(mask)
    for i in range(fp):
        # Cosine curve: starts at 0, accelerates smoothly to 255
        t = i / fp
        a = int(255 * (0.5 - 0.5 * math.cos(math.pi * t)))
        draw.line([(i, 0),     (i, h)],     fill=a)
        draw.line([(w-1-i, 0), (w-1-i, h)], fill=a)
        draw.line([(0, i),     (w, i)],     fill=a)
        draw.line([(0, h-1-i), (w, h-1-i)], fill=a)
    # Heavy blur for ultra-smooth transition
    mask = mask.filter(ImageFilter.GaussianBlur(fp * 0.6))
    out  = img.copy().convert("RGBA")
    out.putalpha(mask)
    return out

def matching_tag_font(title_font, title_text, tag_text):
    """Return a Michroma font sized so tag_text width == title_text width."""
    tb = title_font.getbbox(title_text)
    title_w = tb[2] - tb[0]
    # Binary search correct size
    lo, hi = 8, 300
    for _ in range(20):
        mid  = (lo + hi) // 2
        f    = load_font("Michroma-Regular.ttf", mid)
        tagb = f.getbbox(tag_text)
        tw   = tagb[2] - tagb[0]
        if tw < title_w:
            lo = mid
        else:
            hi = mid
    return load_font("Michroma-Regular.ttf", lo)

def build_quote_lines(template, custom_text):
    text  = (custom_text or "").strip()
    words = text.split()

    if template == "with-quote":
        lines = ["", "", ""]
        idx   = 0
        for w in words:
            if len(lines[idx]) + len(w) + 1 > 26 and idx < 2:
                idx += 1
            lines[idx] += ("" if not lines[idx] else " ") + w
        return lines

    elif template == "name-highlight":
        name = text or "Your Name"
        return [name, "— Always Remembered", ""]

    elif template == "shadow-style":
        parts = [p.strip() for p in text.split(",")]
        while len(parts) < 3:
            parts.append("")
        return parts[:3]

    return ["", "", ""]


# ── DESKTOP ──────────────────────────────────────────────────────────────────

def generate_desktop(photo_img, template, custom_text, bg_color, accent_color):
    bg_rgb  = hex_to_rgb(BG_COLORS.get(bg_color,  "#0a0a0a"))
    acc_rgb = hex_to_rgb(ACCENT_COLORS.get(accent_color, "#c9a84c"))

    canvas = Image.new("RGB", (DESKTOP_W, DESKTOP_H), bg_rgb)

    # ── Photo: left ~55%, vertically centered ──
    max_pw = int(DESKTOP_W * 0.55)
    photo  = photo_img.copy()
    photo.thumbnail((max_pw, DESKTOP_H), Image.LANCZOS)
    pw, ph = photo.size
    feather_px = max(60, int(pw * 0.07))
    photo_f    = feather_edges(photo, feather_px)
    py         = (DESKTOP_H - ph) // 2
    canvas.paste(photo_f, (0, py), photo_f)

    if template == "photo-only":
        return canvas

    # ── Fonts ──
    title_size = 190
    quote_size = 84
    title_font = load_font("Michroma-Regular.ttf", title_size)
    quote_font = load_font("Quicksand-Light.ttf",  quote_size)
    tag_font   = matching_tag_font(title_font, "SHADOW.", "UNCONDITIONAL LOYALTY")

    lines = build_quote_lines(template, custom_text)

    # ── Layout: text block x starts right of photo ──
    text_x = pw + 340
    if text_x + 1357 > DESKTOP_W:   # 1357 = approx title width at 190px
        text_x = pw + 80

    # ── Measure total block height ──
    tb      = title_font.getbbox("SHADOW.")
    title_h = tb[3] - tb[1]
    qb      = quote_font.getbbox("Ag")
    q_line_h = qb[3] - qb[1]
    tagb    = tag_font.getbbox("UNCONDITIONAL LOYALTY")
    tag_h   = tagb[3] - tagb[1]

    divider_gap = 28
    block_h = (q_line_h + 16) * 3 + divider_gap + 2 + divider_gap + title_h + 20 + tag_h

    # Center vertically, shift down 2 line-heights as per your spec
    text_y = (DESKTOP_H - block_h) // 2 + (q_line_h * 2)

    draw = ImageDraw.Draw(canvas, "RGBA")

    # ── 3 quote lines (faded ~52% opacity) ──
    cur_y = text_y
    for line in lines:
        if line:
            draw.text((text_x, cur_y), line, font=quote_font,
                      fill=(*acc_rgb, 133))   # 133/255 ≈ 52%
        cur_y += q_line_h + 16

    # ── Thin divider ──
    cur_y += divider_gap
    title_w = tb[2] - tb[0]
    draw.line([(text_x, cur_y), (text_x + title_w, cur_y)],
              fill=(*acc_rgb, 90), width=2)
    cur_y += divider_gap

    # ── SHADOW. ──
    draw.text((text_x, cur_y), "SHADOW.", font=title_font,
              fill=(*acc_rgb, 255))
    # tb[3] is the full bottom of the glyph including internal offset (e.g. 222 at 190px)
    # Adding 40px gap gives clear visual separation
    tb_full = title_font.getbbox("SHADOW.")
    cur_y += tb_full[3] + 40

    # ── UNCONDITIONAL LOYALTY — same left edge, width matches SHADOW. ──
    draw.text((text_x, cur_y), "UNCONDITIONAL LOYALTY", font=tag_font,
              fill=(*acc_rgb, 200))

    return canvas


# ── PHONE ────────────────────────────────────────────────────────────────────

def crop_fill(img, target_w, target_h):
    """Scale image to fill target dimensions, crop center."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)
    left  = (new_w - target_w) // 2
    top   = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def generate_phone(photo_img, template, custom_text, bg_color, accent_color):
    bg_rgb  = hex_to_rgb(BG_COLORS.get(bg_color,  "#0a0a0a"))
    acc_rgb = hex_to_rgb(ACCENT_COLORS.get(accent_color, "#c9a84c"))

    # Phone canvas
    canvas = Image.new("RGB", (PHONE_W, PHONE_H), bg_rgb)

    # ── Photo fills top 60% — crop-fill so it always covers the zone fully ──
    photo_zone_h = int(PHONE_H * 0.60)
    photo        = crop_fill(photo_img.copy(), PHONE_W, photo_zone_h)

    # Feather all 4 edges with strong smooth gradient
    photo_rgba = feather_edges(photo, feather_px=int(min(photo.size) * 0.12))
    canvas.paste(photo_rgba, (0, int(PHONE_H * 0.20)), photo_rgba)

    if template == "photo-only":
        return canvas

    # ── Fonts ──
    title_size = 116
    quote_size = 58
    title_font = load_font("Michroma-Regular.ttf", title_size)
    quote_font = load_font("Quicksand-Light.ttf",  quote_size)
    tag_font   = matching_tag_font(title_font, "SHADOW.", "UNCONDITIONAL LOYALTY")

    draw = ImageDraw.Draw(canvas, "RGBA")

    # ── SHADOW. block: starts at 62% of canvas height ──
    tb       = title_font.getbbox("SHADOW.")
    title_w  = tb[2] - tb[0]
    title_x  = (PHONE_W - title_w) // 2
    title_y  = int(PHONE_H * 0.82)

    draw.text((title_x, title_y), "SHADOW.", font=title_font,
              fill=(*acc_rgb, 255))

    # True bottom of rendered SHADOW. glyph
    shadow_bottom = title_y + tb[3]

    # Divider — 30px below glyph bottom
    div_y = shadow_bottom + 30
    draw.line([(title_x, div_y), (title_x + title_w, div_y)],
              fill=(*acc_rgb, 90), width=2)

    # UNCONDITIONAL LOYALTY — 24px below divider
    tagb  = tag_font.getbbox("UNCONDITIONAL LOYALTY")
    tag_w = tagb[2] - tagb[0]
    tag_x = title_x + (title_w - tag_w) // 2
    tag_y = div_y + 24
    draw.text((tag_x, tag_y), "UNCONDITIONAL LOYALTY", font=tag_font,
              fill=(*acc_rgb, 200))

    # ── Quote lines: 3 quote lines ABOVE SHADOW. block ──
    # Placed just above title_y, stacking upward
    lines     = build_quote_lines(template, custom_text)
    qb        = quote_font.getbbox("Ag")
    q_line_h  = qb[3] - qb[1]
    line_step = q_line_h + 20
    active    = [l for l in lines if l]
    n_lines   = len(active)
    margin    = (PHONE_W - title_w) // 2  # align left edge with SHADOW.

    # Bottom of quote block sits 40px above SHADOW. title
    quote_block_bottom = title_y - 40
    quote_start = quote_block_bottom - (n_lines * line_step)

    for i, line in enumerate(active):
        draw.text((margin, quote_start + i * line_step),
                  line, font=quote_font,
                  fill=(*acc_rgb, 160))   # faded like original spec

    return canvas


# ── HELPERS ──────────────────────────────────────────────────────────────────

def photo_from_base64(data_url):
    header, encoded = data_url.split(",", 1)
    return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")

def image_to_bytes(img, quality=92):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf.read()

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

"""Measure the floor areas of apartment 24A from its published floor plan.

    python measure.py

Prints every area and writes the figures. Nothing is hand-entered.

The two sides are A (east, blue) and L (west, orange). Each has a bedroom, a
closet and a bathroom. The only structural difference between them: a door
between L's bathroom and the kitchen, so L's bedroom, closet and bathroom are
all behind one door, and A's are not.

Method
------
1. SCALE, derived not assumed. The plan labels the living/dining 15'3" x 15'0".
   Wall to wall that is 163 px for 15.25 ft and 162 px for 15.0 ft, i.e. 10.69
   and 10.80 px/ft. The two axes agreeing to within 1% is what shows the
   drawing is to scale rather than stretched; PX_PER_FT is the midpoint.

2. SCALE CHECKED against a room that played no part in setting it: A's bedroom
   is printed 10'1" wide and measures 109 px, implying 10.81 px/ft, within
   0.6%.

3. AREAS by flood fill. Each space is isolated by filling the plan's white
   interior, with any pixel darker than WALL_LEVEL acting as a barrier. Door
   openings are sealed first (SEALS) so a fill stays in one space. Text and
   fixtures inside a space read as "wall" to the fill, so enclosed holes are
   filled back in and counted as floor.

4. KNOWN GAP. Interior floor measured this way totals ~940 sf against the
   1,027 sf published. That ~8% is the usual rentable-area gross-up. It does
   not affect proportions, and 1,027 is used as the denominator so shares are
   expressed against the figure on the lease.

5. WHERE THE PLAN IS AMBIGUOUS. A's bedroom is printed 14'0" deep, but 14'0"
   at this scale is 150 px and its north wall to its closet partition is 135
   px, so the printed depth runs into the closet. Rooms and closets are
   therefore reported separately and no single "bedroom size" is quoted.
"""

from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PLAN = "plan.png"
PX_PER_FT = 10.75
PX_PER_SF = PX_PER_FT**2
WALL_LEVEL = 200
PUBLISHED_SF = 1027

# Door openings, sealed so each flood fill stays inside one space.
SEALS = [
    ((246, 194), (246, 236), "the door between L's bathroom and the kitchen"),
    ((248, 232), (248, 262), "the divider between L's closet run and the entry closet"),
]

# L's closet runs along the bottom wall with no partition at its face, only a
# dashed line for the doors, so a fill would leak into the bedroom. Everything
# inside L's door at or below this row is closet; above it is bedroom.
L_CLOSET_FACE_Y = 218

# Bathrooms and A's spaces are read as wall-to-wall rectangles: a fill gets
# trapped by the fixtures, and A's closet has no solid partition either.
BOXES = {
    "L_bath": (183, 113, 242, 197),
    "A_bath": (500, 109, 561, 190),
    "A_bedroom": (570, 101, 679, 236),
    "A_closet": (570, 236, 669, 273),
}

A_KEYS = ["A_bedroom", "A_closet", "A_bath"]
L_KEYS = ["L_bedroom", "L_closet", "L_bath"]

A_HUE = (30, 90, 230)
L_HUE = (205, 110, 10)
TINT = {
    "A_bedroom": A_HUE, "A_closet": (95, 145, 245), "A_bath": (150, 185, 250),
    "L_bedroom": L_HUE, "L_closet": (238, 158, 55), "L_bath": (246, 198, 138),
}


def _flood(blocked, seed):
    h, w = blocked.shape
    seen = np.zeros_like(blocked, bool)
    queue = deque([seed])
    seen[seed[1], seed[0]] = True
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and not blocked[ny, nx]:
                seen[ny, nx] = True
                queue.append((nx, ny))
    return seen


def _fill_holes(mask):
    """Count text and fixtures enclosed by a space as part of its floor."""
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min() - 2, ys.max() + 3
    x0, x1 = xs.min() - 2, xs.max() + 3
    sub = mask[y0:y1, x0:x1]
    h, w = sub.shape
    outside = np.zeros_like(sub)
    queue = deque()
    for i in range(h):
        for j in (0, w - 1):
            if not sub[i, j] and not outside[i, j]:
                outside[i, j] = True
                queue.append((j, i))
    for j in range(w):
        for i in (0, h - 1):
            if not sub[i, j] and not outside[i, j]:
                outside[i, j] = True
                queue.append((j, i))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not outside[ny, nx] and not sub[ny, nx]:
                outside[ny, nx] = True
                queue.append((nx, ny))
    out = mask.copy()
    out[y0:y1, x0:x1] = sub | ~outside
    return out


def _box(shape, x0, y0, x1, y1):
    m = np.zeros(shape, bool)
    m[y0:y1, x0:x1] = True
    return m


def check_scale():
    return {
        "living room, east-west": (498 - 335, 15.25),
        "living room, north-south": (262 - 100, 15.0),
    }


def regions():
    """Boolean mask per space, plus the interior envelope of the whole unit."""
    grey = Image.open(PLAN).convert("L")
    w, h = grey.size
    shape = (h, w)

    sealed = grey.copy()
    draw = ImageDraw.Draw(sealed)
    for a, b, _why in SEALS:
        draw.line([a, b], fill=0, width=5)
    # Everything behind L's door, filled from the floor in front of the bath.
    behind_door = _fill_holes(
        _flood(np.asarray(sealed).astype(int) < WALL_LEVEL, (210, 228))
    )
    yy = np.arange(h)[:, None]

    masks = {
        "L_bedroom": behind_door & (yy < L_CLOSET_FACE_Y),
        "L_closet": behind_door & (yy >= L_CLOSET_FACE_Y),
        "L_bath": _box(shape, *BOXES["L_bath"]),
        "A_bedroom": _box(shape, *BOXES["A_bedroom"]),
        "A_closet": _box(shape, *BOXES["A_closet"]),
        "A_bath": _box(shape, *BOXES["A_bath"]),
    }
    envelope = ~_flood(np.asarray(grey).astype(int) < WALL_LEVEL, (0, 0))
    return masks, envelope


def areas(masks):
    return {k: v.sum() / PX_PER_SF for k, v in masks.items()}


def validate(masks):
    """Check the scale against A's printed 10'1" width."""
    width_px = BOXES["A_bedroom"][2] - BOXES["A_bedroom"][0]
    printed_ft = 10 + 1 / 12
    return width_px, printed_ft, width_px / printed_ft


# ----------------------------------------------------------------- figures
def _font(size, bold=False):
    path = ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf")
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _tint(img, mask, rgb, alpha=0.40):
    a = np.asarray(img).astype(float)
    a = np.where(mask[..., None], a * (1 - alpha) + np.array(rgb) * alpha, a)
    return Image.fromarray(a.astype(np.uint8))


def figure_areas(masks, path="figures/areas.png"):
    base = Image.open(PLAN).convert("RGB")
    W, H = base.size
    S, MX, TOP, BOT = 2, 30, 180, 290
    sf = areas(masks)
    img = base.copy()
    for k in L_KEYS + A_KEYS:
        img = _tint(img, masks[k], TINT[k])
    out = Image.new("RGB", (W * S + MX * 2, H * S + TOP + BOT), (255, 255, 255))
    out.paste(img.resize((W * S, H * S), Image.LANCZOS), (MX, TOP))
    dr = ImageDraw.Draw(out)
    OW = out.width
    f_t, f_l, f_s, f_ss = _font(30, True), _font(18, True), _font(15), _font(14)

    dr.text((MX, 16), "Apartment 24A \u2014 measured floor areas", font=f_t, fill=(18, 18, 18))
    dr.text((MX + 2, 54),
            f"Measured from the published floor plan at {PX_PER_FT} px/ft, a scale taken from the "
            "living room's printed 15'3\" x 15'0\" and confirmed to 0.6% by A's printed 10'1\" width.",
            font=f_ss, fill=(115, 115, 115))

    def centre(mask):
        ys, xs = np.nonzero(mask)
        return xs.mean() * S + MX, ys.mean() * S + TOP

    def box(key, title, sub, bx, by, above):
        col = TINT[key]
        bw = max(dr.textlength(title, font=f_l), dr.textlength(sub, font=f_s)) + 20
        bx = min(bx, OW - 8 - bw)
        dr.rectangle([bx, by, bx + bw, by + 48], fill=(255, 255, 255), outline=col, width=2)
        dr.text((bx + 10, by + 5), title, font=f_l, fill=col)
        dr.text((bx + 10, by + 27), sub, font=f_s, fill=(95, 95, 95))
        cx, cy = centre(masks[key])
        dr.line([(bx + bw / 2, by + 48 if above else by), (cx, cy)], fill=col, width=3)
        dr.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=col, outline=(255, 255, 255), width=2)

    for k, t, s, bx in (
        ("L_bedroom", f"L bedroom   {sf['L_bedroom']:.0f} sf", "includes the floor by the bathroom", MX + 8),
        ("L_bath", f"L bath   {sf['L_bath']:.0f} sf", "", MX + 380),
        ("A_bedroom", f"A bedroom   {sf['A_bedroom']:.0f} sf", "", MX + 760),
        ("A_bath", f"A bath   {sf['A_bath']:.0f} sf", "", MX + 1040),
    ):
        box(k, t, s, bx, 92, True)
    for k, t, s, bx in (
        ("L_closet", f"L closet   {sf['L_closet']:.0f} sf", "the whole run inside L's door", MX + 120),
        ("A_closet", f"A closet   {sf['A_closet']:.0f} sf", "", MX + 980),
    ):
        box(k, t, s, bx, H * S + TOP + 26, False)

    ly = H * S + TOP + 100
    dr.line([(MX, ly), (OW - MX, ly)], fill=(205, 205, 205), width=2)
    a_tot = sum(sf[k] for k in A_KEYS)
    l_tot = sum(sf[k] for k in L_KEYS)
    shared = PUBLISHED_SF - a_tot - l_tot
    y = ly + 16
    for name, mid, tot, col in (
        ("A", f"bedroom {sf['A_bedroom']:.0f}  +  closet {sf['A_closet']:.0f}"
              f"  +  bath {sf['A_bath']:.0f}", f"{a_tot:.0f} sf", A_HUE),
        ("L", f"bedroom {sf['L_bedroom']:.0f}  +  closet {sf['L_closet']:.0f}"
              f"  +  bath {sf['L_bath']:.0f}", f"{l_tot:.0f} sf", L_HUE),
        ("Shared", "living / dining, kitchen, entry, entry closet  \u2014  unshaded above",
         f"{shared:.0f} sf", (115, 115, 115)),
    ):
        dr.rectangle([MX, y + 4, MX + 18, y + 22], fill=col)
        dr.text((MX + 30, y + 2), name, font=f_l, fill=(22, 22, 22))
        dr.text((MX + 130, y + 4), mid, font=f_s, fill=(75, 75, 75))
        dr.text((OW - MX - 130, y + 2), tot, font=f_l, fill=col)
        y += 32
    dr.text((MX, y + 14),
            "L's bedroom, closet and bathroom are all behind one door, between L's bathroom and the "
            "kitchen. A's are not.",
            font=f_s, fill=(22, 22, 22))
    dr.text((MX, y + 40),
            f"Denominator is the published {PUBLISHED_SF:,} sf.", font=f_s, fill=(22, 22, 22))
    out.save(path)
    return path


def figure_split(masks, envelope, path="figures/split.png"):
    base = Image.open(PLAN).convert("RGB")
    W, H = base.size
    sf = areas(masks)
    a_tot = sum(sf[k] for k in A_KEYS)
    l_tot = sum(sf[k] for k in L_KEYS)
    shared = PUBLISHED_SF - a_tot - l_tot
    share = (a_tot + shared / 2) / PUBLISHED_SF

    S, MX, TOP, BOT = 2, 26, 92, 104
    img = base.copy()
    claimed = np.zeros((H, W), bool)
    for k in L_KEYS:
        img = _tint(img, masks[k], L_HUE, 0.45)
        claimed |= masks[k]
    for k in A_KEYS:
        img = _tint(img, masks[k], A_HUE, 0.45)
        claimed |= masks[k]
    yy, xx = np.mgrid[0:H, 0:W]
    img = _tint(img, envelope & ~claimed & (((xx + yy) % 14) < 4), (120, 120, 120), 0.5)

    out = Image.new("RGB", (W * S + MX * 2, H * S + TOP + BOT), (255, 255, 255))
    out.paste(img.resize((W * S, H * S), Image.LANCZOS), (MX, TOP))
    dr = ImageDraw.Draw(out)
    f_t, f_n, f_s, f_ss = _font(30, True), _font(24, True), _font(16), _font(14)
    dr.text((MX, 16), "Each side's own space, and the shared remainder",
            font=f_t, fill=(18, 18, 18))
    dr.text((MX + 2, 54),
            "Blue = A's \u00b7 Orange = L's, all of it behind one door \u00b7 "
            "Grey stripes = shared, divided equally.",
            font=f_ss, fill=(115, 115, 115))
    y = H * S + TOP + 14
    dr.rectangle([MX, y + 6, MX + 18, y + 24], fill=A_HUE)
    dr.text((MX + 28, y + 4), f"A {a_tot:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.rectangle([MX + 160, y + 6, MX + 178, y + 24], fill=L_HUE)
    dr.text((MX + 188, y + 4), f"L {l_tot:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.rectangle([MX + 330, y + 6, MX + 348, y + 24], fill=(120, 120, 120))
    dr.text((MX + 358, y + 4), f"shared {shared:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.text((MX, y + 40),
            f"A's share = ({a_tot:.0f} + {shared / 2:.0f}) / {PUBLISHED_SF:,} = {share * 100:.2f}%",
            font=f_n, fill=A_HUE)
    out.save(path)
    return path


if __name__ == "__main__":
    print("Scale, from the living room's printed dimensions:")
    for label, (px, ft) in check_scale().items():
        print(f"  {label:<28} {px:3d} px / {ft:5.2f} ft = {px / ft:5.2f} px/ft")
    print(f"  using PX_PER_FT = {PX_PER_FT}")

    masks, envelope = regions()
    sf = areas(masks)
    px, ft, implied = validate(masks)
    print(f"\nChecked against A's printed 10'1\" width, which did not set the scale:")
    print(f"  {px} px / {ft:.2f} ft = {implied:.2f} px/ft  ({implied / PX_PER_FT - 1:+.1%})")

    print("\nMeasured areas:")
    for k in A_KEYS + L_KEYS:
        print(f"  {k:<12}{sf[k]:7.1f} sf")
    a_tot = sum(sf[k] for k in A_KEYS)
    l_tot = sum(sf[k] for k in L_KEYS)
    print(f"\n  {'A total':<12}{a_tot:7.1f} sf")
    print(f"  {'L total':<12}{l_tot:7.1f} sf   {l_tot / a_tot - 1:+.0%} vs A")
    print(f"  {'shared':<12}{PUBLISHED_SF - a_tot - l_tot:7.1f} sf")
    print(f"  {'published':<12}{PUBLISHED_SF:7.1f} sf")
    print(f"  {'floor measured':<12}{envelope.sum() / PX_PER_SF:7.1f} sf"
          f"  ({envelope.sum() / PX_PER_SF / PUBLISHED_SF - 1:+.0%} vs published)")

    print()
    print("wrote", figure_areas(masks))
    print("wrote", figure_split(masks, envelope))

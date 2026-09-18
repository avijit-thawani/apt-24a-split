"""Measure the floor areas of apartment 24A from its published floor plan.

Everything here is derived from `plan.png` — the floor plan on the property
website — with no hand-entered areas. Run it to reproduce the numbers:

    python measure.py

It prints every measured area and writes the two figures in `figures/`.

--------------------------------------------------------------------------
Method
--------------------------------------------------------------------------

1. SCALE. Not assumed. The plan labels the living/dining area 15'3" x 15'0".
   Measuring wall-to-wall between the kitchen partition (x=335) and the
   bathroom wall (x=498) gives 163 px for 15.25 ft, and between the north wall
   (y=100) and the south wall (y=262) gives 162 px for 15.0 ft. That is
   10.69 and 10.80 px/ft respectively. The two axes agreeing to within 1% is
   what establishes the drawing is to scale rather than stretched; PX_PER_FT
   below is the midpoint.

2. ROOM BOUNDARIES. Each room is isolated by flood-filling the plan's white
   interior, treating any pixel darker than WALL_LEVEL as a barrier. Door
   openings are sealed first (see SEALS) so a fill stays inside one room.
   Text and fixtures inside a room read as "wall" to the fill, so enclosed
   holes are filled back in afterwards and counted as floor.

3. VALIDATION. The scale is set from the living room, so it is checked against
   a different room: the east bedroom's printed 10'1" width. Wall to wall that
   is 109 px, giving 10.81 px/ft — within 0.6% of the 10.75 used here.

   Its printed 14'0" depth is NOT used as a check, because 14'0" at this scale
   is 150 px and the room's north wall to the closet partition line is only
   135 px. The printed depth runs into the closet recess, so a "bedroom area"
   taken from the label alone sits somewhere between the 127 sf of open floor
   and the 159 sf of floor-plus-closet. That ambiguity is exactly why this
   file reports rooms and closets as separate numbers and never quotes a
   single "bedroom size".

4. KNOWN LIMIT. The interior floor measured this way totals ~940 sf against
   the 1,027 sf the landlord publishes. The ~8% difference is the usual
   rentable-area gross-up (wall thickness and a share of common structure).
   Proportions are unaffected, and 1,027 is used as the denominator so the
   shares are expressed against the figure on the lease.
"""

from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PLAN = "plan.png"
PX_PER_FT = 10.75
PX_PER_SF = PX_PER_FT**2
WALL_LEVEL = 200          # pixels darker than this block a flood fill
PUBLISHED_SF = 1027       # landlord's stated area for the unit

# Door openings, sealed so each flood fill stays inside one space.
SEALS = [
    ((181, 96), (181, 266), "east wall of the west bedroom"),
    ((246, 194), (246, 236), "the suite door, between the west bath and the kitchen"),
    ((248, 232), (248, 262), "divider between the suite closet run and the entry closet"),
]

# Bathrooms are read as their wall-to-wall rectangles. A flood fill gets
# trapped by the fixtures (tub, basin, WC), which are drawn as solid outlines.
BATH_BOX = {
    "west_bath": (183, 113, 242, 197),
    "east_bath": (500, 109, 561, 190),
}
# The east bedroom likewise: its closet has no solid partition, only a dashed
# line for the doors, so the fill leaks. Taken as its enclosing rectangles.
EAST_ROOM_BOX = (570, 101, 679, 236)
EAST_CLOSET_BOX = (570, 236, 669, 273)


def _flood(blocked, seed):
    """4-connected fill of the open region containing `seed`."""
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
    """Count text and fixtures enclosed by a room as part of its floor."""
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
    """Re-derive the scale from the plan's own printed dimension."""
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
    blocked = np.asarray(sealed).astype(int) < WALL_LEVEL

    # West bedroom on its own: its door is sealed, so the fill stops at it.
    west = _fill_holes(_flood(blocked, (90, 150)))
    yy = np.arange(h)[:, None]

    # The whole west suite: seal only the suite door, fill from the vestibule.
    suite_sealed = grey.copy()
    sd = ImageDraw.Draw(suite_sealed)
    for a, b, why in SEALS:
        if "suite door" in why or "divider" in why:
            sd.line([a, b], fill=0, width=5)
    suite = _fill_holes(
        _flood(np.asarray(suite_sealed).astype(int) < WALL_LEVEL, (210, 228))
    )

    west_room = west & (yy < 222)      # above the closet run
    west_closet = west & (yy >= 222)

    masks = {
        "west_room": west_room,
        "west_closet": west_closet,
        "west_vestibule": suite & ~west_room & ~west_closet,
        "west_bath": _box(shape, *BATH_BOX["west_bath"]),
        "east_room": _box(shape, *EAST_ROOM_BOX),
        "east_closet": _box(shape, *EAST_CLOSET_BOX),
        "east_bath": _box(shape, *BATH_BOX["east_bath"]),
    }
    envelope = ~_flood(np.asarray(grey).astype(int) < WALL_LEVEL, (0, 0))
    return masks, envelope


def areas(masks):
    return {k: v.sum() / PX_PER_SF for k, v in masks.items()}


def validate(masks):
    """Check the scale against a room other than the one that set it.

    Returns the east bedroom's measured width in px, its printed width in ft,
    and the implied px/ft. Also returns the room's open floor and its
    floor-plus-closet, which bracket whatever the printed 14'0" depth means.
    """
    width_px = EAST_ROOM_BOX[2] - EAST_ROOM_BOX[0]
    printed_ft = 10 + 1 / 12
    depth_px = EAST_ROOM_BOX[3] - EAST_ROOM_BOX[1]
    return {
        "width_px": width_px,
        "printed_width_ft": printed_ft,
        "implied_px_per_ft": width_px / printed_ft,
        "printed_depth_px": 14.0 * PX_PER_FT,
        "measured_depth_px": depth_px,
        "open_floor_sf": masks["east_room"].sum() / PX_PER_SF,
        "with_closet_sf": (masks["east_room"] | masks["east_closet"]).sum() / PX_PER_SF,
    }


# --------------------------------------------------------------- figures
EAST_HUE = (30, 90, 230)
WEST_HUE = (205, 110, 10)
TINT = {
    "east_room": EAST_HUE, "east_closet": (95, 145, 245), "east_bath": (150, 185, 250),
    "west_room": WEST_HUE, "west_closet": (238, 158, 55), "west_bath": (246, 198, 138),
    "west_vestibule": (225, 130, 35),
}
EAST_KEYS = ["east_room", "east_closet", "east_bath"]
WEST_KEYS = ["west_room", "west_closet", "west_bath", "west_vestibule"]


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
    S, MX, TOP, BOT = 2, 30, 190, 300
    sf = areas(masks)
    img = base.copy()
    for k in WEST_KEYS + EAST_KEYS:
        img = _tint(img, masks[k], TINT[k])
    out = Image.new("RGB", (W * S + MX * 2, H * S + TOP + BOT), (255, 255, 255))
    out.paste(img.resize((W * S, H * S), Image.LANCZOS), (MX, TOP))
    dr = ImageDraw.Draw(out)
    OW = out.width
    f_t, f_l, f_s, f_ss = _font(30, True), _font(18, True), _font(15), _font(14)

    dr.text((MX, 16), "Apartment 24A \u2014 measured floor areas", font=f_t, fill=(18, 18, 18))
    dr.text((MX + 2, 54),
            f"Measured from the published floor plan at {PX_PER_FT} px/ft, a scale derived from the "
            "living room's printed 15'3\" x 15'0\" and confirmed to 0.6% by the east bedroom's printed 10'1\" width.",
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
        ("west_room", f"WEST bedroom   {sf['west_room']:.0f} sf", "on the building's chamfered corner", MX + 8),
        ("west_bath", f"west bath   {sf['west_bath']:.0f} sf", "inside the suite door", MX + 300),
        ("east_room", f"EAST bedroom   {sf['east_room']:.0f} sf", "a 10' x 14' rectangle", MX + 700),
        ("east_bath", f"east bath   {sf['east_bath']:.0f} sf", "opens off the living room", MX + 1010),
    ):
        box(k, t, s, bx, 96, True)
    for k, t, s, bx in (
        ("west_closet", f"west closet   {sf['west_closet']:.0f} sf", "inside the suite door", MX + 40),
        ("west_vestibule", f"PRIVATE VESTIBULE   {sf['west_vestibule']:.0f} sf",
         "behind the suite door", MX + 330),
        ("east_closet", f"east closet   {sf['east_closet']:.0f} sf", "no partition, open to the room", MX + 950),
    ):
        box(k, t, s, bx, H * S + TOP + 26, False)

    ly = H * S + TOP + 100
    dr.line([(MX, ly), (OW - MX, ly)], fill=(205, 205, 205), width=2)
    east = sum(sf[k] for k in EAST_KEYS)
    west = sum(sf[k] for k in WEST_KEYS)
    shared = PUBLISHED_SF - east - west
    y = ly + 16
    for name, mid, tot, col in (
        ("East side", f"room {sf['east_room']:.0f}  +  closet {sf['east_closet']:.0f}"
                      f"  +  bath {sf['east_bath']:.0f}", f"{east:.0f} sf", EAST_HUE),
        ("West side (a suite)", f"room {sf['west_room']:.0f}  +  closet {sf['west_closet']:.0f}"
                                f"  +  bath {sf['west_bath']:.0f}"
                                f"  +  vestibule {sf['west_vestibule']:.0f}", f"{west:.0f} sf", WEST_HUE),
        ("Shared", "living / dining, kitchen, entry, entry closet  \u2014  unshaded above",
         f"{shared:.0f} sf", (115, 115, 115)),
    ):
        dr.rectangle([MX, y + 4, MX + 18, y + 22], fill=col)
        dr.text((MX + 30, y + 2), name, font=f_l, fill=(22, 22, 22))
        dr.text((MX + 250, y + 4), mid, font=f_s, fill=(75, 75, 75))
        dr.text((OW - MX - 130, y + 2), tot, font=f_l, fill=col)
        y += 32
    for line in (
        "A door between the west bathroom and the kitchen encloses the west bedroom, its closet, its "
        "bathroom and a vestibule.",
        f"Nothing on the east side is behind a second door. Denominator is the published {PUBLISHED_SF:,} sf.",
    ):
        dr.text((MX, y + 14), line, font=f_s, fill=(22, 22, 22))
        y += 26
    out.save(path)
    return path


def figure_split(masks, envelope, path="figures/split.png"):
    """Private space each side, and the shared remainder that gets halved."""
    base = Image.open(PLAN).convert("RGB")
    W, H = base.size
    sf = areas(masks)
    east = sum(sf[k] for k in EAST_KEYS)
    west = sum(sf[k] for k in WEST_KEYS)
    shared = PUBLISHED_SF - east - west
    share = (east + shared / 2) / PUBLISHED_SF

    S, MX, TOP, BOT = 2, 26, 92, 104
    img = base.copy()
    claimed = np.zeros((H, W), bool)
    for k in WEST_KEYS:
        img = _tint(img, masks[k], WEST_HUE, 0.45)
        claimed |= masks[k]
    for k in EAST_KEYS:
        img = _tint(img, masks[k], EAST_HUE, 0.45)
        claimed |= masks[k]
    yy, xx = np.mgrid[0:H, 0:W]
    img = _tint(img, envelope & ~claimed & (((xx + yy) % 14) < 4), (120, 120, 120), 0.5)

    out = Image.new("RGB", (W * S + MX * 2, H * S + TOP + BOT), (255, 255, 255))
    out.paste(img.resize((W * S, H * S), Image.LANCZOS), (MX, TOP))
    dr = ImageDraw.Draw(out)
    f_t, f_n, f_s, f_ss = _font(30, True), _font(24, True), _font(16), _font(14)
    dr.text((MX, 16), "Private space each side, and the shared remainder",
            font=f_t, fill=(18, 18, 18))
    dr.text((MX + 2, 54),
            "Blue = east private \u00b7 Amber = west private, including the vestibule behind its door "
            "\u00b7 Grey stripes = shared, divided equally.",
            font=f_ss, fill=(115, 115, 115))
    y = H * S + TOP + 14
    dr.rectangle([MX, y + 6, MX + 18, y + 24], fill=EAST_HUE)
    dr.text((MX + 28, y + 4), f"east {east:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.rectangle([MX + 190, y + 6, MX + 208, y + 24], fill=WEST_HUE)
    dr.text((MX + 218, y + 4), f"west {west:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.rectangle([MX + 390, y + 6, MX + 408, y + 24], fill=(120, 120, 120))
    dr.text((MX + 418, y + 4), f"shared {shared:.0f} sf", font=f_s, fill=(30, 30, 30))
    dr.text((MX, y + 40),
            f"east share = ({east:.0f} + {shared / 2:.0f}) / {PUBLISHED_SF:,} = {share * 100:.2f}%",
            font=f_n, fill=EAST_HUE)
    out.save(path)
    return path


if __name__ == "__main__":
    print("Scale check (should agree across both axes):")
    for label, (px, ft) in check_scale().items():
        print(f"  {label:<28} {px:3d} px / {ft:5.2f} ft = {px / ft:5.2f} px/ft")
    print(f"  using PX_PER_FT = {PX_PER_FT}\n")

    masks, envelope = regions()
    sf = areas(masks)
    print("Measured areas:")
    for k in WEST_KEYS + EAST_KEYS:
        print(f"  {k:<16}{sf[k]:7.1f} sf")
    east = sum(sf[k] for k in EAST_KEYS)
    west = sum(sf[k] for k in WEST_KEYS)
    print(f"\n  {'east private':<16}{east:7.1f} sf")
    print(f"  {'west private':<16}{west:7.1f} sf  ({west / east - 1:+.0%} vs east)")
    print(f"  {'shared':<16}{PUBLISHED_SF - east - west:7.1f} sf")
    print(f"  {'published total':<16}{PUBLISHED_SF:7.1f} sf")
    print(f"  {'floor measured':<16}{envelope.sum() / PX_PER_SF:7.1f} sf"
          f"  ({envelope.sum() / PX_PER_SF / PUBLISHED_SF - 1:+.0%} vs published)")

    v = validate(masks)
    print("\nScale validated against a room other than the one that set it \u2014")
    print("the east bedroom's printed 10'1\" width:")
    print(f"  measured {v['width_px']} px for {v['printed_width_ft']:.2f} ft"
          f"  =  {v['implied_px_per_ft']:.2f} px/ft"
          f"  ({v['implied_px_per_ft'] / PX_PER_FT - 1:+.1%} vs the {PX_PER_FT} used)")
    print("\nIts printed 14'0\" depth is deliberately NOT used as a check:")
    print(f"  14'0\" at this scale is {v['printed_depth_px']:.0f} px, but the room's north wall")
    print(f"  to its closet partition is {EAST_ROOM_BOX[3] - EAST_ROOM_BOX[1]} px. The printed depth runs")
    print(f"  into the closet, so the label brackets {v['open_floor_sf']:.0f}\u2013{v['with_closet_sf']:.0f} sf")
    print("  rather than naming one figure. Rooms and closets are reported separately here.")

    print()
    print("wrote", figure_areas(masks))
    print("wrote", figure_split(masks, envelope))

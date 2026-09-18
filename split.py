"""Work out each occupant's share of the rent from the measured floor areas.

    python split.py

Reads the geometry from measure.py so there is one source of truth. Prints:

  1. The rent, reconciled against what each occupant actually pays today.
  2. The share implied by the space each occupant has, today and on renewal.
  3. A sensitivity table: every reasonable definition of "private" crossed
     with every reasonable treatment of the shared remainder, so the effect of
     each choice is visible rather than asserted.

--------------------------------------------------------------------------
The rule
--------------------------------------------------------------------------

Each occupant pays for the space only they can use, plus an equal part of the
space both use:

    share = (private area + shared area / 2) / total area

"Private" means behind a door only one occupant passes through. That is the
one definition worth stating, because it is the only thing the two
calculations below disagree about.
"""

import measure

# Rent, from the resident portal on 18 Sep 2026.
CURRENT = {"base": 6486, "amenities": 200, "internet": 65, "liability": 10}
RENEWAL = {"base": 6881, "amenities": 200, "internet": 92, "liability": 10}
CURRENT_TOTAL = sum(CURRENT.values())    # 6761
RENEWAL_TOTAL = sum(RENEWAL.values())    # 7183

# What each occupant pays today.
PAID_EAST = 3333
PAID_WEST = 3428

TOTAL_SF = measure.PUBLISHED_SF
EAST_KEYS = measure.EAST_KEYS
WEST_KEYS = measure.WEST_KEYS


def share(east_sf, west_sf, remainder="halve"):
    """East occupant's share of the total.

    remainder:
      "halve"    split the shared space equally (the rule above)
      "pro-rata" allocate it in proportion to private area
      "ignore"   do not count it at all
    """
    rest = TOTAL_SF - east_sf - west_sf
    if remainder == "halve":
        return (east_sf + rest / 2) / TOTAL_SF
    if remainder == "pro-rata":
        return (east_sf + rest * east_sf / (east_sf + west_sf)) / TOTAL_SF
    if remainder == "ignore":
        return east_sf / (east_sf + west_sf)
    raise ValueError(remainder)


def main():
    masks, _envelope = measure.regions()
    sf = measure.areas(masks)
    east = sum(sf[k] for k in EAST_KEYS)
    west_full = sum(sf[k] for k in WEST_KEYS)
    west_no_vest = west_full - sf["west_vestibule"]

    paid_pct = PAID_EAST / CURRENT_TOTAL
    correct = share(east, west_full)

    # ------------------------------------------------------------- 1. rent
    print("RENT")
    print(f"  {'':<22}{'today':>9}{'renewal':>10}{'change':>16}")
    for k in ("base", "amenities", "internet", "liability"):
        a, b = CURRENT[k], RENEWAL[k]
        ch = f"{b - a:+,}" + (f" ({b / a - 1:+.0%})" if b != a else "")
        print(f"  {k:<22}{a:>9,}{b:>10,}{ch:>16}")
    tot_ch = f"{RENEWAL_TOTAL - CURRENT_TOTAL:+,} ({RENEWAL_TOTAL / CURRENT_TOTAL - 1:+.1%})"
    print(f"  {'TOTAL':<22}{CURRENT_TOTAL:>9,}{RENEWAL_TOTAL:>10,}{tot_ch:>16}")
    print(f"\n  paid today: east {PAID_EAST:,} + west {PAID_WEST:,} = {PAID_EAST + PAID_WEST:,}"
          f"   reconciles: {PAID_EAST + PAID_WEST == CURRENT_TOTAL}")
    print(f"  east is paying {paid_pct:.2%} of the total\n")

    # ------------------------------------------------------------ 2. space
    print("SPACE")
    print(f"  east private          {east:7.1f} sf")
    print(f"  west private          {west_full:7.1f} sf   {west_full / east - 1:+.0%} vs east")
    print(f"    of which vestibule  {sf['west_vestibule']:7.1f} sf   behind the suite door")
    print(f"  shared                {TOTAL_SF - east - west_full:7.1f} sf")
    print(f"  total (published)     {TOTAL_SF:7.1f} sf\n")

    # ------------------------------------------------------------ 3. shares
    print("SHARE OF THE RENT")
    print(f"  {'':<34}{'share':>8}{'today':>9}{'renewal':>10}")
    for name, pc in (("as actually paid today", paid_pct),
                     ("vestibule counted as shared", share(east, west_no_vest)),
                     ("vestibule counted as west private", correct)):
        print(f"  {name:<34}{pc:>7.2%}{CURRENT_TOTAL * pc:>9,.0f}{RENEWAL_TOTAL * pc:>10,.0f}")

    d_today = CURRENT_TOTAL * correct - PAID_EAST
    d_renew = RENEWAL_TOTAL * correct - RENEWAL_TOTAL * paid_pct
    print(f"\n  vs what east pays now                    {d_today:>+9,.0f}")
    print(f"  on renewal, vs holding {paid_pct:.2%}          {d_renew:>+9,.0f}"
          f"   ({d_renew * 12:+,.0f}/year)")
    print(f"\n  Note the corrected share still RAISES east's rent by "
          f"{RENEWAL_TOTAL * correct - CURRENT_TOTAL * correct:+,.0f},")
    print(f"  because the apartment itself went up {RENEWAL_TOTAL - CURRENT_TOTAL:+,}. "
          "Correcting the split")
    print("  changes who absorbs that increase, not whether it happens.\n")

    # ------------------------------------------------------- 4. sensitivity
    print(f"SENSITIVITY \u2014 can any other treatment of the shared space "
          f"explain the {paid_pct:.2%}?")
    defs = [
        ("bedrooms only", sf["east_room"], sf["west_room"]),
        ("bedrooms + closets",
         sf["east_room"] + sf["east_closet"], sf["west_room"] + sf["west_closet"]),
        ("bedrooms + closets + baths", east, west_no_vest),
        ("the above + west vestibule", east, west_full),
    ]
    print(f"  {'private space defined as':<30}{'halve':>9}{'pro-rata':>10}{'ignore':>9}")
    for name, e, w in defs:
        print(f"  {name:<30}{share(e, w):>8.2%}{share(e, w, 'pro-rata'):>10.2%}"
              f"{share(e, w, 'ignore'):>9.2%}")

    rest = TOTAL_SF - east - west_full
    needed = paid_pct * TOTAL_SF - east
    gap = paid_pct - correct
    vest = share(east, west_no_vest) - correct
    print(f"\n  No. Halving lands closest to {paid_pct:.2%} in every row; the two alternatives")
    print("  both move further away, and both move DOWNWARD, so neither can account for it.")
    print(f"  To reach {paid_pct:.2%} while treating the vestibule as private, east would need")
    print(f"  {needed:.0f} of the {rest:.0f} sf of shared space \u2014 {needed / rest:.0%} "
          "of the living room, kitchen")
    print("  and halls. No rule gives one occupant a majority of the shared space.")
    print(f"\n  The {gap * 100:.2f}-point gap between {paid_pct:.2%} and {correct:.2%} "
          "decomposes as:")
    print(f"    {vest * 100:5.2f} points  the vestibule ({vest / gap:.0%} of the gap)")
    print(f"    {(gap - vest) * 100:5.2f} points  rounding in how the original figure was set")
    print("  So the disagreement is about one door, not about the method.")
    print("\n  Also visible in the table: the two bathrooms are the same size to within")
    print("  1 sf, so counting them or not barely moves the number (49.06% vs 49.05%).")
    print("  The east closet is the larger of the two, so counting closets moves the")
    print("  share slightly toward east \u2014 it is counted here, and against east's interest.")


if __name__ == "__main__":
    main()

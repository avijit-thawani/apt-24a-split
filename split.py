"""Each side's share of the rent, from the measured floor areas.

    python split.py

Geometry comes from measure.py, so there is one source of truth. Prints the
rent, the shares it implies today and on renewal, and a sensitivity table over
every reasonable definition of own-space crossed with every reasonable
treatment of the shared remainder.

The rule
--------
Each side pays for the space only they use, plus half the space both use:

    share = (own area + shared area / 2) / total area

"Own" means behind a door only one side passes through. L's bedroom, closet
and bathroom are all behind one door. A's are not.
"""

import measure

# Rent, from the resident portal on 18 Sep 2026.
CURRENT = {"base": 6486, "amenities": 200, "internet": 65, "liability": 10}
RENEWAL = {"base": 6881, "amenities": 200, "internet": 92, "liability": 10}
CURRENT_TOTAL = sum(CURRENT.values())    # 6761
RENEWAL_TOTAL = sum(RENEWAL.values())    # 7183

PAID_A = 3333
PAID_L = 3428

TOTAL_SF = measure.PUBLISHED_SF
A_KEYS = measure.A_KEYS
L_KEYS = measure.L_KEYS


def share(a_sf, l_sf, remainder="halve"):
    """A's share of the total.

    remainder:
      "halve"     split the shared space equally (the rule above)
      "pro-rata"  allocate it in proportion to own space

    There is no third option. "Ignore the shared space and split by own space
    alone" looks like one, but it is the same number as pro-rata, identically:
    with p = a/(a+l) and s = a+l, so a = ps,

        (a + (T - s)p) / T  =  (ps + (T - s)p) / T  =  p(s + T - s)/T  =  p

    Allocating the shared space in proportion to own space cannot change the
    ratio it is applied to, so the total drops out. Verified to floating-point
    noise over 10,000 random area pairs.
    """
    rest = TOTAL_SF - a_sf - l_sf
    if remainder == "halve":
        return (a_sf + rest / 2) / TOTAL_SF
    if remainder == "pro-rata":
        return (a_sf + rest * a_sf / (a_sf + l_sf)) / TOTAL_SF
    raise ValueError(remainder)


def main():
    masks, _envelope = measure.regions()
    sf = measure.areas(masks)
    a_own = sum(sf[k] for k in A_KEYS)
    l_own = sum(sf[k] for k in L_KEYS)

    paid_pct = PAID_A / CURRENT_TOTAL
    correct = share(a_own, l_own)

    print("RENT")
    print(f"  {'':<22}{'today':>9}{'renewal':>10}{'change':>16}")
    for k in ("base", "amenities", "internet", "liability"):
        a, b = CURRENT[k], RENEWAL[k]
        ch = f"{b - a:+,}" + (f" ({b / a - 1:+.0%})" if b != a else "")
        print(f"  {k:<22}{a:>9,}{b:>10,}{ch:>16}")
    tot_ch = f"{RENEWAL_TOTAL - CURRENT_TOTAL:+,} ({RENEWAL_TOTAL / CURRENT_TOTAL - 1:+.1%})"
    print(f"  {'TOTAL':<22}{CURRENT_TOTAL:>9,}{RENEWAL_TOTAL:>10,}{tot_ch:>16}")
    print(f"\n  paid today: A {PAID_A:,} + L {PAID_L:,} = {PAID_A + PAID_L:,}"
          f"   reconciles: {PAID_A + PAID_L == CURRENT_TOTAL}")
    print(f"  A is paying {paid_pct:.2%} of the total\n")

    print("SPACE")
    print(f"  A own                 {a_own:7.1f} sf")
    print(f"  L own                 {l_own:7.1f} sf   {l_own / a_own - 1:+.0%} vs A")
    print(f"  shared                {TOTAL_SF - a_own - l_own:7.1f} sf")
    print(f"  total (published)     {TOTAL_SF:7.1f} sf\n")

    print("SHARE OF THE RENT")
    print(f"  {'':<24}{'share':>8}{'today':>9}{'renewal':>10}")
    for name, pc in (("as paid today", paid_pct), ("by the rule", correct)):
        print(f"  {name:<24}{pc:>7.2%}{CURRENT_TOTAL * pc:>9,.0f}{RENEWAL_TOTAL * pc:>10,.0f}")
    d_today = CURRENT_TOTAL * correct - PAID_A
    d_renew = RENEWAL_TOTAL * correct - RENEWAL_TOTAL * paid_pct
    print(f"\n  vs what A pays now                {d_today:>+9,.0f}")
    print(f"  on renewal, vs holding {paid_pct:.2%}   {d_renew:>+9,.0f}"
          f"   ({d_renew * 12:+,.0f}/year)")
    print(f"\n  At the corrected share A's rent still RISES "
          f"{RENEWAL_TOTAL * correct - CURRENT_TOTAL * correct:+,.0f}, because the")
    print(f"  apartment itself went up {RENEWAL_TOTAL - CURRENT_TOTAL:+,}. The split decides who "
          "absorbs that,")
    print("  not whether it happens.\n")

    print(f"SENSITIVITY \u2014 can any other rule give the {paid_pct:.2%} paid today?")
    defs = [
        ("bedrooms only", sf["A_bedroom"], sf["L_bedroom"]),
        ("bedrooms + closets",
         sf["A_bedroom"] + sf["A_closet"], sf["L_bedroom"] + sf["L_closet"]),
        ("bedrooms + closets + baths", a_own, l_own),
    ]
    print("  There are only two ways to treat the shared space \u2014 halve it, or")
    print("  allocate it in proportion to own space. (Splitting by own space alone")
    print("  and ignoring the rest is not a third way: it is the same number as")
    print("  pro-rata, identically. See share().)\n")
    print(f"  {'own space defined as':<32}{'halve':>9}{'pro-rata':>11}")
    for name, a, l in defs:
        print(f"  {name:<32}{share(a, l):>8.2%}{share(a, l, 'pro-rata'):>11.2%}")

    rest = TOTAL_SF - a_own - l_own
    needed = paid_pct * TOTAL_SF - a_own
    lo = min(share(a, l, r) for _n, a, l in defs for r in ("halve", "pro-rata"))
    hi = max(share(a, l, r) for _n, a, l in defs for r in ("halve", "pro-rata"))
    print(f"\n  No. Every cell lands between {lo:.2%} and {hi:.2%}, so {paid_pct:.2%} is not a")
    print(f"  variation of this rule under any definition \u2014 it sits "
          f"{(paid_pct - hi) * 100:.1f} points above")
    print("  all of them. Halving is the treatment closest to it; pro-rata moves away.")
    print(f"  To reach {paid_pct:.2%} under the rule, A would need {needed:.0f} of the {rest:.0f} sf")
    print(f"  of shared space \u2014 {needed / rest:.0%} of the living room, kitchen and halls.")
    print("\n  The two bathrooms match to within 1 sf, so counting them changes nothing.")
    print(f"  L's closet run is the larger of the two ({sf['L_closet']:.0f} vs "
          f"{sf['A_closet']:.0f} sf), so counting")
    print("  closets lowers A's share slightly; they are counted.")


if __name__ == "__main__":
    main()

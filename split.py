"""Each side's share of the rent, from the measured floor areas.

    python split.py

Geometry comes from measure.py, so there is one source of truth. Prints the
rent and the shares it implies today and on renewal.

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


def share(a_sf, l_sf):
    """A's share of the total."""
    rest = TOTAL_SF - a_sf - l_sf
    return (a_sf + rest / 2) / TOTAL_SF


def main():
    masks, _envelope = measure.regions()
    sf = measure.areas(masks)
    a_own = sum(sf[k] for k in A_KEYS)
    l_own = sum(sf[k] for k in L_KEYS)

    paid_pct = PAID_A / CURRENT_TOTAL
    by_rule = share(a_own, l_own)

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
    for name, pc in (("as paid today", paid_pct), ("by the rule", by_rule)):
        print(f"  {name:<24}{pc:>7.2%}{CURRENT_TOTAL * pc:>9,.0f}{RENEWAL_TOTAL * pc:>10,.0f}")
    d_today = CURRENT_TOTAL * by_rule - PAID_A
    d_renew = RENEWAL_TOTAL * by_rule - RENEWAL_TOTAL * paid_pct
    print(f"\n  vs what A pays now                {d_today:>+9,.0f}")
    print(f"  on renewal, vs holding {paid_pct:.2%}   {d_renew:>+9,.0f}"
          f"   ({d_renew * 12:+,.0f}/year)")
    print("\n  This is area only. It does not yet represent that the master bedroom,")
    print("  L's, has a south-facing window and an in-bedroom bathroom.")


if __name__ == "__main__":
    main()

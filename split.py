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

The share applies to the base rent only. Amenities, internet and liability are
split 50:50, and so are the metered utilities, which are billed on top and are
not in the totals here.
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
    """A's share of the base rent."""
    rest = TOTAL_SF - a_sf - l_sf
    return (a_sf + rest / 2) / TOTAL_SF


def a_parts(charges, base_share):
    """A's part of each charge: base_share of the base rent, half of the rest."""
    return {k: v * (base_share if k == "base" else 0.5) for k, v in charges.items()}


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

    renew = a_parts(RENEWAL, by_rule)
    rule_today = sum(a_parts(CURRENT, by_rule).values())
    rule_renew = sum(renew.values())
    hold_renew = RENEWAL_TOTAL * paid_pct

    print("SHARE OF THE RENT \u2014 base rent by area, everything else 50:50")
    print(f"  {'on renewal':<22}{'A share':>9}{'total':>9}{'A':>8}{'L':>8}")
    for k, v in RENEWAL.items():
        a = renew[k]
        print(f"  {k:<22}{a / v:>9.2%}{v:>9,}{a:>8,.0f}{v - a:>8,.0f}")
    print(f"  {'TOTAL':<22}{'':>9}{RENEWAL_TOTAL:>9,}{rule_renew:>8,.0f}"
          f"{RENEWAL_TOTAL - rule_renew:>8,.0f}")

    print(f"\n  {'A pays':<24}{'today':>9}{'renewal':>10}")
    print(f"  {'as paid today, ' + format(paid_pct, '.2%'):<24}{PAID_A:>9,}{hold_renew:>10,.0f}")
    print(f"  {'by the rule':<24}{rule_today:>9,.0f}{rule_renew:>10,.0f}")
    d_today = rule_today - PAID_A
    d_renew = rule_renew - hold_renew
    print(f"\n  vs what A pays now                {d_today:>+9,.0f}")
    print(f"  on renewal, vs holding {paid_pct:.2%}   {d_renew:>+9,.0f}"
          f"   ({d_renew * 12:+,.0f}/year)")
    print("\n  The base-rent split is area only. It does not yet represent that the")
    print("  master bedroom, L's, has a south-facing window and an in-bedroom bathroom.")


if __name__ == "__main__":
    main()

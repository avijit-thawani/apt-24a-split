# Apartment 24A — floor areas and rent split

Each occupant's share of the rent, from floor areas measured off the published
plan rather than estimated. Reproducible — no area or share below was typed in
by hand:

```
python measure.py      # areas, scale checks, figures
python split.py         # rent, shares, sensitivity
```

Needs `numpy` and `pillow`.

## The rule

Each occupant pays for the space only they can use, plus half the space both
use:

```
share = (private area + shared area / 2) / total area
```

"Private" means behind a door only one occupant passes through.

## The rent

Resident portal, 18 September 2026. Current lease ends 17 Nov 2026.

| | Today | Renewal |
|---|---|---|
| Base rent | $6,486 | $6,881 |
| Amenities | $200 | $200 |
| Internet | $65 | $92 |
| Liability | $10 | $10 |
| **Total** | **$6,761** | **$7,183** (+6.2%) |

Today's payments reconcile exactly: east $3,333 + west $3,428 = $6,761, so east
pays **49.30%**.

## The areas

![Measured floor areas](./figures/areas.png)

| | Bedroom | Closet | Bath | Private hall | **Private** |
|---|---|---|---|---|---|
| **East** | 127 | 32 | 43 | — | **202 sf** |
| **West** | 160 | 19 | 43 | 34 | **255 sf** |
| Shared | living/dining, kitchen, entry | | | | **570 sf** |

Total published: **1,027 sf**.

**The west side is a suite.** A door between the west bathroom and the kitchen
encloses its bedroom, closet, bathroom *and* a 34 sf vestibule. Nothing on the
east side is behind a second door. West holds **26% more private space**.

Two details that cut the other way and are counted anyway: the bathrooms match
to within 1 sf, and the **east closet is the larger** of the two, 32 against 19.

## The result

![The split](./figures/split.png)

| | Share | Today | Renewal |
|---|---|---|---|
| As paid today | 49.30% | $3,333 | $3,541 |
| **By the rule above** | **47.42%** | **$3,206** | **$3,406** |

East is paying **$127/month more than the rule gives**; carrying 49.30% into
the renewal rather than recalculating makes that **$135/month, $1,620 a year**.

Note this is not a claim that east's rent should fall — at 47.42% east still
pays **$200 more** on renewal than today, because the apartment itself rose
$422. The split decides who absorbs that, not whether it happens.

## Could any other rule give 49.30%?

`split.py` tests every reasonable definition of "private" against every
reasonable treatment of the remainder:

| Private space defined as | Halve rest | Pro-rata | Ignore rest |
|---|---|---|---|
| bedrooms only | 48.43% | 44.38% | 44.38% |
| bedrooms + closets | 49.06% | 47.13% | 47.13% |
| bedrooms + closets + baths | 49.05% | 47.69% | 47.69% |
| **+ west vestibule** | **47.42%** | 44.19% | 44.19% |

**No.** Halving is closest to 49.30% in every row; both alternatives move
further away and always downward. To reach 49.30% *while* counting the
vestibule as private, east would need 304 of the 570 shared sf — 53% of the
living room, kitchen and halls.

Of the 1.88-point gap, **1.63 points is the vestibule** and 0.25 is rounding in
how the original figure was set.

## Method

Commented in full in `measure.py`. In short:

1. **Scale is derived, not assumed.** The plan labels the living/dining
   15'3" × 15'0"; wall-to-wall that measures 163 px for 15.25 ft and 162 px for
   15.0 ft — 10.69 and 10.80 px/ft. The axes agreeing to within 1% is what
   shows the drawing is to scale. 10.75 px/ft is used.
2. **Checked against a different room.** The east bedroom's printed 10'1"
   width measures 109 px → 10.81 px/ft, within **0.6%**.
3. **Areas are flood-filled**, not estimated. Doors are sealed first so a fill
   stays in one room; text and fixtures inside a room are counted as floor.
4. **Known gap:** interior floor measures 940 sf against the published 1,027 —
   the usual rentable-area gross-up. Proportions are unaffected; 1,027 is the
   denominator so shares match the lease.
5. **Where the plan is ambiguous:** the east bedroom's printed 14'0" depth is
   150 px at this scale but only 135 px to its closet partition, so the label
   runs into the closet. That is why rooms and closets are reported separately
   and no single "bedroom size" is quoted.

**To dispute the result**, in order of leverage: whether the vestibule is
private (1.63 of the 1.88 points — answerable by standing in the hallway); the
`SEALS` coordinates in `measure.py`, which decide where one room ends; then the
denominator, where using 940 instead of 1,027 moves the share by 0.24 points.
Changing the scale does almost nothing — it cancels out of a ratio of areas.

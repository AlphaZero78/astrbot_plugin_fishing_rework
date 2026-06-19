# Balance Model

The economy is evaluated with `scripts/analyze_balance.py`.

## Fishing zones

Zone cost is charged on every attempt, including failed attempts. Baseline
analysis therefore uses:

- 70% success rate
- no rod, accessory, bait, buff, quality bonus, or rare bonus
- 180 second cooldown
- the real within-rarity fish selection weights
- the real zone fish mappings

The baseline target is roughly 1.55x to 1.60x gross return. Higher zones still
produce much more net value per hour, but entering them requires enough liquid
coins to absorb failed attempts.

## Gacha pools

Coins are valued at face value. Rods, baits, and general items use their
catalog cost. Accessories use the configured rarity sale price because the
schema has no purchase-cost column.

Normal pools target about 0.90x to 0.98x catalog return. This leaves a modest
currency sink while preserving the utility value of rare equipment.

## Known follow-up

The runtime currently calculates catch value modifiers but the fish inventory
does not persist the generated multiplier. Balance reports model the intended
effect; persistence must be fixed before the new values are released to live
instances.

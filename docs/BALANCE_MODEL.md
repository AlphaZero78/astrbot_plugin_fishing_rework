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

The baseline target is roughly 6x to 8x gross return, centered near 7x.
Higher zones still produce much more net value per hour, while failed attempts
and bait costs remain meaningful currency sinks.

Base rods and accessories use a tier ladder: each higher rarity's shared
attributes are approximately the previous rarity at refine level 5. The three
6-star accessories share the 5-star refine-5 baseline and differ only in their
quality, rarity, or quantity specialization.

## Gacha pools

Coins are valued at face value. Rods, baits, and general items use their
catalog cost. Accessories use the configured rarity sale price because the
schema has no purchase-cost column.

Pool prices are operator-controlled inputs rather than a fixed return target.
At the current prices `13 / 1000 / 1000 / 20000`, catalog returns are roughly
`0.75x / 1.20x / 0.65x / 0.59x`. Utility value can differ from catalog value
because rare equipment may be worth more to a player than its liquidation
price.

Generated catch value is persisted through pond, aquarium, market, steal, and
electric-fishing inventory flows.

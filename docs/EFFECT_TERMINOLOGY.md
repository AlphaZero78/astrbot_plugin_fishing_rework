# Effect Terminology

Player-facing text and WebUI labels must use the following terms.
Database field names remain unchanged during migration compatibility work.

| Runtime field | Display term | Meaning |
| --- | --- | --- |
| `bonus_fish_quality_modifier` | High-quality trigger multiplier | Multiplied across equipment, then converted to a high-quality trigger probability with the configured logarithmic formula. |
| `bonus_fish_quantity_modifier` / `quantity_modifier` | Catch quantity multiplier | Controls expected catch count. `1.30` means one guaranteed catch plus a 30% chance for one extra catch. `2.00` means one guaranteed extra catch. |
| `bonus_rare_fish_chance` / `rare_chance_modifier` | Rare-fish weight bonus | Additive share of low-rarity distribution weight transferred to four- and five-star fish, subject to the global cap. |
| `bonus_coin_modifier` / `value_modifier` | Catch weight/base-value multiplier | Multiplies both generated fish weight and base value. The legacy database field names are retained for compatibility. |
| `fishing_cooldown_modifier` | Fishing cooldown multiplier | Multiplies the base cooldown. `0.75` means 25% less waiting time. |

## Wording Rules

- Show multipliers as `x1.30`, not `130%` or an ambiguous `+30%`.
- Show additive probabilities or weight transfers as `+5%`.
- Do not use "fish count bonus"; use "catch quantity multiplier".
- Do not describe `bonus_coin_modifier` as only a coin bonus.
- Descriptions must state whether an effect changes probability, expected count,
  guaranteed count, weight, base value, or cooldown.

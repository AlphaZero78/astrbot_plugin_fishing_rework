# Architecture Audit

## Migration Goal

This repository is a standalone migration of the current playable plugin state.
It intentionally starts with a new Git history and no upstream fork remote.
The existing `D:\astrbot_plugin_fishing` repository remains the rollback
baseline until the migration passes the full test matrix.

## Current High-Risk Areas

- `core/services/inventory_service.py` contains inventory, selling, refinement,
  item use, equipment protection, pond upgrades, and commodity operations.
- `core/services/fishing_service.py` contains catch resolution, probability
  calculation, daily tasks, taxes, automatic fishing, equipment wear, and
  notifications.
- `core/services/game_mechanics_service.py` contains unrelated wipe-bomb,
  stealing, electric fishing, wheel-of-fate, and price calculation rules.
- Game values are split across `_conf_schema.json`, `main.py`,
  `core/initial_data.py`, database JSON fields, and service-level defaults.
- Item behavior is split between `effect_type`, JSON `effect_payload`, effect
  handlers, and special cases embedded in unrelated services.
- The existing tests cover only amount parsing, font fallback, and exchange
  inventory tax behavior.

## Target Module Boundaries

- `core/config`: typed configuration loading, validation, defaults, and
  database-backed runtime settings.
- `core/mechanics`: pure calculation modules for fishing, refinement, gacha,
  shops, and wipe-bomb behavior.
- `core/services`: orchestration only; no duplicated formulas or hidden
  defaults.
- `core/effects`: item-effect definitions, schemas, validation, and execution.
- `core/analytics`: expected-value calculators and balance validation.
- `manager`: WebUI forms and APIs generated from the same schemas used by the
  runtime.

## Compatibility Requirements

- Preserve the current shared `fish.db` data while migrations are developed.
- Keep existing item, fish, bait, rod, accessory, shop, and pool identifiers
  stable unless an explicit data migration updates every reference.
- New runtime settings must have database defaults and validation.
- Both AstrBot instances must be able to load the same migrated plugin code and
  shared database without running duplicate background jobs.

## Completion Evidence

- Unit tests for pure mechanics and item effects.
- Migration tests from a copy of the current shared database.
- Expected-value reports for every fishing zone and gacha pool.
- WebUI API and form tests for all editable settings and item effects.
- Concurrent shared-database tests for background tasks.
- Plugin import and startup smoke tests in both AstrBot instance environments.

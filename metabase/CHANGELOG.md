# Metabase Dashboard Version History & Changelog

## [2026-03-09] - Landscape Parameter Fix & Automation Hardening (by Agent)
### Bug Fix & History
- **Issue**: "Landscape" filter was appearing as a text box instead of a dropdown UI. Metabase sync script (`setup.py`) also crashed with `ClassCastException` earlier when applying `type: "id"` with string defaults.
- **Root Cause**: Metabase `v0.47+` API requires specific configuration structure for `static-list` dropdown parameters. 
  1. `type` must be `"string/="` (not id or category).
  2. The parameter must declare `"values_query_type": "list"`.
  3. The array of actual items must be deeply nested inside `"values_source_config": { "values": [...] }`.
- **Resolution**: Updated `provisioning.json` to properly declare the `static-list` filter structure according to the actual API specification.
- **Documentation**: Appended specific JSON rules for Dropdown logic to `README.md` Section 4 to prevent future mistakes.

## [Initial Setup Notes]
- **Automated Provisioning Flow**: The system relies on `provisioning.json` as the Single Source of Truth.
- **Script logic**: `setup.py` iterates `provisioning.json`, automatically parses `{{...}}` into `template-tags`, and merges/updates cards and layouts. 
- **Idempotency**: All Python scripts in this folder (`manager.py`, `setup.py`, `verify_setup.py`) are strictly structured to be repeatable across ephemeral containers. When rebuilding the DB or Docker, running `python3 metabase/setup.py` successfully resets the entire dashboard logic without duplicate entity creation.

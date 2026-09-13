---
name: code-review
description: Use when reviewing pull requests or changes in this ESPHome configs repo. Checks the bilingual (PL/EN) layout, ${lbl_*} label/substitution parity, secrets hygiene, Home Assistant metadata (device_class/state_class/unit), Modbus register details, ESPHome config validity, and shared-package layout (common.yaml vs web_server: !remove).
license: MIT
---

# Code review — esphome-configs

Review ESPHome device configurations in this repository. The project uses a
bilingual layout: logic is written once in `packages/<device>/logic.yaml` and
translated labels live in `labels/pl/<device>.yaml` and `labels/en/<device>.yaml`.
Thin entries in `devices/<device>.<lang>.yaml` wire them together. Read
`AGENTS.md` for the full conventions.

Comment only on real problems. Prefer concrete, minimal suggestions with the
corrected YAML. Do not restate what the diff already makes obvious.

Read the matching language entries together with `logic.yaml` — a component
removed from one file is often supplied by a package include in the other.

## Structure and layout

- Device behaviour belongs in `packages/<device>/logic.yaml`, not in the entry
  files. Flag logic duplicated across `.pl`/`.en` entries.
- Entry files (`devices/<device>.<lang>.yaml`) should stay thin: identity
  substitutions plus `packages:` includes of the label pack and logic (and
  shared `common.yaml`/`wifi.yaml` only when the device actually uses them).
- Canonical package keys are `labels`, `wifi`, `common`, `logic`. Flag a key
  that does not match the file it includes (`comment: !include …/common.yaml`
  still loads, but hides which package supplies logger/API/OTA).
- Prefer including `packages/common.yaml` and `packages/wifi.yaml` from the
  entries. Do not copy `logger`/`api`/`ota`/`web_server` into `logic.yaml`
  unless the device must override a nested field (e.g. `logger.baud_rate: 0`
  or `web_server.include_internal: true`). Nested overrides merge with the
  package; they are not YAML duplicate-key errors.
- Tight flash (typical 1 MB ESP8285): include `common.yaml` and strip only the
  heavy component on the entry:

  ```yaml
  packages:
    labels: !include ../labels/<lang>/<device>.yaml
    wifi: !include ../packages/wifi.yaml
    common: !include ../packages/common.yaml
    logic: !include ../packages/<device>/logic.yaml

  web_server: !remove
  ```

  Do **not** ask to restore inlined `api:`/`ota:`/`logger:` blocks that were
  removed from `logic.yaml` if both language entries now include `common.yaml`.
  Logger/API/OTA then come from the shared package; that is the intended layout.
- Flag these as real problems:
  - The generated node has neither `common.yaml` nor inline `api:`/`ota:`
    (Home Assistant `platform: homeassistant` sensors and OTA updates break).
  - `common.yaml` is omitted and API/OTA are copied into `logic.yaml` instead
    of `web_server: !remove` on the entry.
  - Comments that contradict the includes (e.g. "common.yaml is omitted" or
    "API/OTA live in logic.yaml" next to `common: !include` and
    `web_server: !remove`).

## How to phrase comments

Write what is wrong, why it matters, and the preferred fix. Name the shared
package or `!remove` tag when that is the layout to use.

- Avoid: "Restore the inline API and OTA configuration."
  Prefer: "This `logic.yaml` no longer defines `api:`/`ota:`. Include
  `packages/common.yaml` from both language entries and strip only
  `web_server` with `web_server: !remove` so logger/API/OTA stay shared
  and the 1 MB image still fits an OTA slot."
- Avoid: "Do not include `common.yaml` on this 1 MB device."
  Prefer: "Including `common.yaml` is right; drop `web_server` with
  `web_server: !remove` rather than omitting the whole package."
- Avoid: "Update the stale description."
  Prefer: "The header still says `common.yaml` is omitted and API/OTA live
  in `logic.yaml`, but this entry includes `common.yaml` and strips
  `web_server`. Say that, so the next edit looks in the correct file."

## Bilingual parity (most common defect)

- Every `${lbl_*}` referenced in `logic.yaml` must exist in BOTH `labels/pl/…`
  and `labels/en/…` for that device. Flag any key that is missing in one
  language or present in only one. The key sets must be identical.
  `scripts/check-conventions.py` (run by CI) already fails on this, so focus the
  review on whether the *translation* is right rather than whether it is present.
- Flag hard-coded user-facing strings in `logic.yaml`: any entity `name:` or
  text-sensor state string that is a literal Polish/English word instead of a
  `${lbl_*}` reference. Exception: entities with `internal: true` are not
  user-facing and are named in plain English on purpose.
- Comments and `id:` values must be English. Flag Polish comments or ids.
- When a PR adds/renames a label key on one side, verify the other language and
  the `logic.yaml` reference were updated too.

## YAML correctness

- Substituted names must be quoted: `name: "${lbl_x}"`. Flag unquoted
  `name: ${lbl_x}` (labels can contain `: ` or `%` and break unquoted YAML).
- 2-space indentation, no tabs.

## Home Assistant metadata

- Prefer `device_class` + `state_class` + `unit_of_measurement` on measurement
  entities (correct units, statistics, and localized quantities). Flag a numeric
  sensor missing an obvious `device_class`/`unit_of_measurement`.
- `device_class` alone cannot disambiguate multiple entities of the same class
  (e.g. several temperatures) — those still need distinct names via labels. Do
  not suggest dropping names in favour of `device_class` for such entities.

## Secrets

- No real secret values in any committed file, log, or example.
- Any new `!secret <key>` must be added to `secrets.yaml.example`.
- `secrets.yaml` (including `devices/secrets.yaml`) must never be committed;
  confirm `.gitignore` still covers it.

## Modbus / device specifics

- Sanity-check `register_type`, `address`, `value_type`, `bitmask` and `filters`
  against the surrounding comments/register map; flag obvious mismatches
  (e.g. a `multiply` scale that contradicts the documented unit).
- Writable `number`/`switch` on `modbus_controller` should generally set
  `use_write_multiple: true`.
- `S_WORD_S`/`U_WORD_S` (byte-swapped) value types require ESPHome ≥ 2026.8.0;
  a config using them must pin `min_version: 2026.8.0`. Do not flag this as an
  error, and do not suggest removing `min_version` or downgrading the types.

## ESPHome validity & CI

- Changes to a device must keep `esphome config devices/<device>.<lang>.yaml`
  valid. The exception is a config pinned to an unreleased `min_version`
  (currently `kospel-hpi4` → 2026.8.0), which is known-failing until CI's pinned
  ESPHome is bumped.
- The pinned ESPHome version must match in `scripts/setup-esphome.sh`
  (`ESPHOME_VERSION`) and `.github/workflows/validate.yml`. Flag drift.
- A newly pinned tool version should carry a `# renovate: datasource=… depName=…`
  comment on the preceding line, otherwise Renovate cannot update it.

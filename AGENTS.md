# Agent instructions — esphome-configs

Guidance for automated agents (Cursor, Copilot code review, Copilot cloud agent)
working in this repository. Human contributors should also follow it. These
rules reflect the conventions agreed for this multirepo; keep them in sync when
the conventions change.

## What this repo is

A monorepo of [ESPHome](https://esphome.io/) device configurations with a
**bilingual (Polish/English) layout**: each device's behaviour is written once,
and the labels shown in Home Assistant are provided by per-language files. The
core workflow is validating device YAML with `esphome config`.

## Repository layout

```
packages/
  common.yaml              # shared infra: api, ota, logger, web_server
  wifi.yaml                # shared infra: wifi + captive_portal
  <device>/
    logic.yaml             # device behaviour; entity names via ${lbl_*}
labels/
  pl/<device>.yaml         # Polish labels (substitutions block)
  en/<device>.yaml         # English labels (substitutions block)
devices/
  <device>.pl.yaml         # thin entry: identity + labels/pl + logic
  <device>.en.yaml         # thin entry: identity + labels/en + logic
```

## Conventions (must follow)

- **One logic file per device.** All components/behaviour live in
  `packages/<device>/logic.yaml`. Do not duplicate logic per language.
- **English source, translated labels only.** Every comment and every `id:`
  stays in English. The only translated content is the `substitutions` in
  `labels/<lang>/<device>.yaml`.
- **User-visible strings come from labels.** Any string shown in Home Assistant
  — entity `name:` values and text-sensor state strings — must be referenced in
  `logic.yaml` as `${lbl_*}` and defined in the label packs. Never hard-code a
  Polish (or English) user-facing string in `logic.yaml`.
- **Keep label keys in sync.** Every `${lbl_*}` used in a device's `logic.yaml`
  must exist in **both** `labels/pl/<device>.yaml` and `labels/en/<device>.yaml`
  with identical keys. A missing key breaks `esphome config`.
- **Quote substituted names.** Always write `name: "${lbl_x}"` (quoted), because
  a label may contain characters such as `: ` or `%` that break unquoted YAML.
- **Always set metadata.** Use `device_class`, `state_class` and
  `unit_of_measurement` where applicable. They give correct units, long-term
  statistics and localized quantities regardless of display language.
- **Internal/debug entities stay English.** Entities with `internal: true` are
  not user-facing; name them in plain English (no label needed).
- **Thin entry files.** `devices/<device>.<lang>.yaml` only sets identity
  substitutions (`device_name`, `friendly_name`, `board`, …) and includes the
  label pack + logic (+ shared packages if the device uses them). Adding a
  language = copy the entry and swap the `labels` include.
- **YAML style.** 2-space indentation, no tabs.

## Secrets

- Real secrets live in `secrets.yaml` (gitignored, incl. `devices/secrets.yaml`).
- The seedable template is `secrets.yaml.example`; when a config introduces a
  new `!secret <key>`, add that key to `secrets.yaml.example`.
- ESPHome resolves `!secret` relative to each config file's directory. Entries
  live in `devices/`, so `devices/secrets.yaml` is the resolvable location; keep
  device entries in `devices/` (not in subfolders) unless you also relocate the
  secrets file.
- Never commit real secret values (in configs, logs, or chat).

## Commands

- Set up the toolchain (idempotent): `bash scripts/setup-esphome.sh`
  (installs the pinned ESPHome into `~/.esphome-venv` and symlinks `esphome`).
- Validate one config: `esphome config devices/<device>.<lang>.yaml`
- Validate everything like CI does:
  ```bash
  for c in devices/*.yaml; do [ "$c" = "devices/secrets.yaml" ] && continue; esphome config "$c"; done
  ```
- Check the conventions `esphome config` cannot see (label parity across
  languages, `${lbl_*}` coverage, `!secret` keys documented in
  `secrets.yaml.example`, quoted substituted names):
  `python3 scripts/check-conventions.py` — stdlib only, no venv needed.
- Lint: `yamllint --strict .` and `shellcheck scripts/*.sh`.
- The pinned ESPHome version lives in **two** places that must match:
  `scripts/setup-esphome.sh` (`ESPHOME_VERSION`) and
  `.github/workflows/validate.yml` (`pip install esphome==…`). CI fails on drift.

## Dependency updates (Renovate)

- Renovate detects GitHub Actions and the workflow's `python-version` on its own.
  Everything else — versions pinned inside shell scripts, `run:` steps, etc. —
  is picked up by the custom manager in `renovate.json`, which reads an
  annotation comment on the line above the version:

  ```bash
  # renovate: datasource=pypi depName=esphome versioning=pep440
  ESPHOME_VERSION="2026.7.4"
  ```

- When you introduce a new pinned tool version, add such a comment (see the
  [datasource list](https://docs.renovatebot.com/modules/datasource/)) so the
  dependency does not silently go stale. Both ESPHome pins share `depName:
  esphome`, so Renovate bumps them in one PR. If the pin lives in a file type
  the manager does not scan yet, extend `managerFilePatterns` in `renovate.json`.
- Validate config changes with
  `npx --yes --package renovate renovate-config-validator`, and preview what
  Renovate would find with `npx --yes renovate --platform=local --dry-run=lookup`
  (needs Node 24).
- `min_version:` in `packages/<device>/logic.yaml` is deliberately **not**
  annotated: it is a minimum requirement of the device config, not a dependency
  to keep current.
- GitHub Actions are pinned to a commit digest with the version in a trailing
  comment (`uses: actions/checkout@<sha> # v7.0.1`). Keep that shape — Renovate
  (`helpers:pinGitHubActionDigests`) relies on it, and a moving tag is a supply
  chain risk. Never replace a digest with a bare tag. The same rule applies to
  container steps (`uses: docker://rhysd/actionlint:<tag>@sha256:<digest>`);
  Renovate updates tag and digest together.
- ESPHome updates wait `minimumReleaseAge: 7 days`, so a release that gets
  pulled or hot-fixed never reaches a PR.

## Adding a device

1. `packages/<device>/logic.yaml` — components, user-visible names as `${lbl_*}`.
2. `labels/pl/<device>.yaml` and `labels/en/<device>.yaml` — same keys, translated.
3. `devices/<device>.pl.yaml` and `devices/<device>.en.yaml` — identity + includes.
4. Add any new `!secret` keys to `secrets.yaml.example`.
5. Run `esphome config` for both language entries and
   `python3 scripts/check-conventions.py`.

## ESPHome version notes

- `kospel-hpi4` targets `min_version: 2026.8.0` because it uses the byte-swapped
  `S_WORD_S` / `U_WORD_S` Modbus value types introduced in that release. It will
  fail `esphome config` until the pinned ESPHome (CI + install script) is bumped
  to `2026.8.0`. This is expected; do not "fix" it by downgrading the value
  types or removing `min_version`.

## Testing expectations

- Treat `esphome config` on the changed device entries as the required check.
  A change is not done until the affected `devices/*.yaml` validate (except
  configs pinned to an unreleased `min_version`, which are known-failing).
- `python3 scripts/check-conventions.py` must report zero errors; it is what CI
  runs, and it catches the cross-language defects `esphome config` cannot.
- Do not weaken CI or add temporary hacks to make validation pass. Adding a
  `# yamllint disable` or a checker exception counts as weakening it.

## Cursor Cloud specific instructions

- The Cloud Agent environment runs `scripts/setup-esphome.sh` on setup, which
  installs `esphome` on `PATH` and seeds `devices/secrets.yaml` from the example.
- If `esphome` is missing (e.g. a fresh shell), run `bash scripts/setup-esphome.sh`
  first, then validate with `esphome config …`.

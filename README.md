# esphome-configs

Multi-device [ESPHome](https://esphome.io/) configuration monorepo with a
bilingual (Polish/English) layout: device **logic** is written once, and the
**labels** shown in Home Assistant live in per-language files.

## Layout

```
packages/
  common.yaml              # shared infra: api, ota, logger, web_server
  wifi.yaml                # shared infra: wifi + captive_portal
  <device>/
    logic.yaml             # device behaviour; entity names via ${lbl_*}
labels/
  pl/<device>.yaml         # Polish labels (substitutions)
  en/<device>.yaml         # English labels (substitutions)
devices/
  <device>.pl.yaml         # thin entry: identity + labels/pl + logic
  <device>.en.yaml         # thin entry: identity + labels/en + logic
```

Conventions:

- Comments and every `id:` stay in **English**. Only the label packs under
  `labels/<lang>/` are translated.
- Home Assistant-visible strings (entity names and text-sensor states) are
  referenced in `logic.yaml` as `${lbl_*}` and defined in the label packs.
- Always set `device_class` / `state_class` / `unit_of_measurement`: they give
  correct units, long-term statistics, and localized quantities regardless of
  the display language.
- Internal/debug entities (`internal: true`) keep plain English names.
- A device is single-language at flash time; pick the `.pl` or `.en` entry.

## Adding a device

1. Create `packages/<device>/logic.yaml` with the components, using `${lbl_*}`
   for user-visible names.
2. Add `labels/pl/<device>.yaml` and `labels/en/<device>.yaml` with the same
   substitution keys translated.
3. Create `devices/<device>.pl.yaml` and `devices/<device>.en.yaml` that set the
   identity substitutions and include the label pack + logic (+ shared packages
   if the device uses them).

## Secrets

Copy `secrets.yaml.example` to `secrets.yaml` next to the device entries
(`devices/secrets.yaml`) and fill in real values. `secrets.yaml` is gitignored.
ESPHome resolves `!secret` relative to each config file's directory.

## Validation

```bash
esphome config devices/<device>.<lang>.yaml   # one config
python3 scripts/check-conventions.py          # cross-language conventions
yamllint --strict .                           # YAML style
```

`scripts/check-conventions.py` covers what `esphome config` structurally cannot:
it loads one language at a time, so it never notices a label key that exists in
`labels/pl/` but not in `labels/en/`, a `${lbl_*}` with no definition, or a
`!secret` key missing from `secrets.yaml.example`.

CI runs the same checks (`lint` job) plus ESPHome validation of every
`devices/*.yaml` on push/PR (`validate` job). The pinned ESPHome version lives
in `.github/workflows/validate.yml` and `scripts/setup-esphome.sh`; both are
annotated with a `# renovate:` comment, so Renovate bumps them in a single PR,
and CI fails if the two pins ever drift apart.

> Note: `kospel-hpi4` targets `min_version: 2026.8.0` (it uses the byte-swapped
> `S_WORD_S`/`U_WORD_S` Modbus value types introduced in that release). It will
> fail validation until CI's pinned ESPHome is bumped to `2026.8.0`.

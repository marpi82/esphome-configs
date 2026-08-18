<!--
Thanks for contributing! Keep changes focused and follow AGENTS.md.
Remember the bilingual layout: logic in packages/<device>/logic.yaml,
labels in labels/pl and labels/en, thin entries in devices/.
-->

## Summary

<!-- What does this change and why? -->

## Type of change

- [ ] New device
- [ ] Device logic change (registers, entities, behaviour)
- [ ] Labels / translation only
- [ ] Shared package or infrastructure
- [ ] CI / tooling / docs

## Affected device(s)

<!-- e.g. kospel-hpi4 -->

- Device:
- Board / platform:
- ESPHome version tested:

## Validation

<!-- Paste the result of validating the affected entries. -->

```
$ esphome config devices/<device>.pl.yaml
INFO Configuration is valid!
$ esphome config devices/<device>.en.yaml
INFO Configuration is valid!
```

## Checklist

- [ ] Logic lives in `packages/<device>/logic.yaml`; comments and `id:` are in English
- [ ] User-visible strings use `${lbl_*}` (entity names quoted: `name: "${lbl_x}"`)
- [ ] `labels/pl/<device>.yaml` and `labels/en/<device>.yaml` have identical keys, both updated
- [ ] `device_class` / `state_class` / `unit_of_measurement` set where applicable
- [ ] Any new `!secret` keys added to `secrets.yaml.example`; no real secrets committed
- [ ] `esphome config` passes for the affected `devices/*.yaml` (or the config pins an unreleased `min_version` — note it below)

## Notes

<!-- Known-failing until an ESPHome release, breaking changes, follow-ups, HA screenshots, etc. -->

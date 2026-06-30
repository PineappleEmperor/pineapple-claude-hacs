#!/usr/bin/env bash
# SessionStart: in an HA custom-integration repo, re-arm the ha-integration skill rule.
if ls custom_components/*/manifest.json >/dev/null 2>&1; then
  cat <<'MSG'
[ha-integration] This repo is a Home Assistant custom integration. Invoke the `ha-integration` skill via the Skill tool BEFORE modifying any integration code this session, and re-invoke after every /compact.
MSG
fi

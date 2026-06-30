#!/usr/bin/env bash
# UserPromptSubmit: per-turn anchors. Independent, each marker-gated.

# HA-integration repos: skill + quality anchors.
if ls custom_components/*/manifest.json >/dev/null 2>&1; then
  msg="[ha-integration] ha-integration skill active before integration edits · keep quality_scale.yaml honest · verify HA APIs at developers.home-assistant.io"
  [ -d firmware ] && msg="$msg · run scripts/sync_render.py after firmware/ edits"
  echo "$msg."
fi

# Any repo on this workflow stack (the skill repo AND scaffolded integrations):
# the commit/PR conventions that drift down-context mid-session.
if [ -f .github/workflows/create-dev-pr.yml ]; then
  echo "[ci-conventions] commit & PR subject = ONE tight imperative (lowercase after the colon, no trailing period, no comma-joined dual subject). create-dev-pr.yml OWNS the PR — never hand-create it with gh pr create; push the branch and let the action open/update it (PR title mirrors the winning commit subject). Branch off main; bump the manifest/plugin version once, as the last commit before merge."
fi

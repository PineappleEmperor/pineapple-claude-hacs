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
if [ -f .github/workflows/pr-checks.yml ]; then
  echo "[ci-conventions] commit & PR subject = ONE tight imperative (lowercase after the colon, no trailing period, no comma-joined dual subject). auto_draft_pr.yml opens the draft PR with a title derived from the commits; no job writes the PR body, so a description is yours to write or leave empty. PR TITLE must use a labellable type: feat|feature, fix, or chore|docs|refactor|perf|test|build|ci|style (all label as chore), or type! for breaking. revert: passes lint_pr but maps to NO label and NO release category. Branch off main; the release tag sets the version, so no PR carries a manifest bump."
fi

#!/usr/bin/env bash
# skill-audit: local-tool
#
# One-time repo setup for a scaffolded integration. Everything here is a GitHub-side
# setting that no file in the repo can carry, and each one fails quietly until the
# first CI run: HACS checks the description, topics and licence; the ruleset is what
# makes every workflow more than advisory; the hook is inert until core.hooksPath
# points at it.
#
# Run from the repo root, once, after the first push:
#   bash scripts/bootstrap_repo.sh "One-line description of the integration"
#
# Needs a gh login with admin on the repo. RELEASE_TOKEN is prompted for, never
# passed as an argument, so it stays out of shell history and process listings.
set -euo pipefail

DESC="${1:-}"
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
DOMAIN=$(basename "$(ls -d custom_components/*/ | head -1)")

echo "Setting up $REPO (domain: $DOMAIN)"

if [ -n "$DESC" ]; then
  gh repo edit "$REPO" --description "$DESC"
  echo "  description set"
else
  echo "  no description given — HACS will fail its description check"
fi

gh repo edit "$REPO" \
  --add-topic home-assistant \
  --add-topic hacs \
  --add-topic home-assistant-custom-component \
  --enable-issues
echo "  topics and issues set"

# dependency_review.yml FAILS rather than skipping when the graph is off, so a repo
# that never enabled it carries a permanently red required check. Observed on a test
# repo: every other workflow passed and Dependency review failed alone.
if gh api "repos/$REPO/dependency-graph/sbom" >/dev/null 2>&1; then
  echo "  dependency graph already enabled"
elif gh api -X PATCH "repos/$REPO" -F security_and_analysis[dependency_graph][status]=enabled \
     >/dev/null 2>&1; then
  echo "  dependency graph enabled"
else
  echo "  COULD NOT enable the dependency graph — do it at Settings -> Advanced Security,"
  echo "  or Dependency review stays red on every PR"
fi

if [ ! -f LICENSE ]; then
  echo "  no LICENSE — HACS fails with SPDX: NOASSERTION until one exists"
fi

# The hook is a file until this points at it.
git config core.hooksPath .githooks
echo "  commit-msg hook enabled"

if [ -f ruleset.json ]; then
  if gh api "repos/$REPO/rulesets" --jq '.[].name' | grep -qx "Protect main"; then
    echo "  ruleset already present"
  else
    gh api -X POST "repos/$REPO/rulesets" --input ruleset.json >/dev/null
    echo "  ruleset applied"
  fi
else
  echo "  no ruleset.json in the repo root — copy it from the skill's templates/"
fi

if gh secret list --json name --jq '.[].name' | grep -qx RELEASE_TOKEN; then
  echo "  RELEASE_TOKEN already set"
else
  echo
  echo "RELEASE_TOKEN is required by auto_draft_pr.yml. Create a fine-grained PAT with"
  echo "Contents: Read and write, Pull requests: Read and write, scoped to this repo."
  read -rsp "Paste it (or press Enter to skip): " TOKEN
  echo
  if [ -n "$TOKEN" ]; then
    printf '%s' "$TOKEN" | gh secret set RELEASE_TOKEN
    echo "  RELEASE_TOKEN set"
  else
    echo "  skipped — draft PRs will not open until it exists"
  fi
fi

echo
echo "Done. Remaining by hand: nothing, unless a step above said otherwise."

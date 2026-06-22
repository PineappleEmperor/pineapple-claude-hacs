# pineapple-claude-hacs

Custom [Claude Code](https://claude.com/claude-code) skills for building and maintaining
**Home Assistant custom integrations** — from scaffold to Platinum quality scale, plus
native-looking custom panels.

These are the skills behind the AI-assistance note you'll find on my HA integrations (e.g.
[ocado-ha](https://github.com/PineappleEmperor/ocado-ha),
[ha-pimoroni-unicorn](https://github.com/PineappleEmperor/ha-pimoroni-unicorn)). They encode
the conventions I've learned the hard way so each new session starts with them instead of
rediscovering them.

## Skills

| Skill | What it does |
|-------|--------------|
| [`ha-integration`](plugins/ha/skills/ha-integration/SKILL.md) | Scaffold, modify, and lint a HA custom integration targeting **Platinum** quality scale. Covers config flows, the `DataUpdateCoordinator` pattern, modern entity/notify platforms, diagnostics, `quality_scale.yaml` discipline, manifest/version bumping, and the full Conventional-Commits → release-drafter → semantic-release CI flow. |
| [`ha-panel-design`](plugins/ha/skills/ha-panel-design/SKILL.md) | Size, type, spacing, and colour for HA **custom panels** (Lit/TS web components). Material 3 type scale, 48px touch targets, and HA theme CSS custom properties — tokens over hardcoded literals. |

Both ship in a single **`ha`** plugin in this marketplace.

Both skills **fetch the authoritative HA / Material 3 docs before acting** rather than coding
from memory, since these APIs and rules change.

## Install

### Plugin marketplace (recommended)

Add this repo as a marketplace and install the `ha` plugin from inside Claude Code:

```
/plugin marketplace add PineappleEmperor/pineapple-claude-hacs
/plugin install ha@pineapple-claude-hacs
```

Both skills come with it. Claude auto-invokes them when relevant (the trigger is in each
skill's `description`), or call them explicitly — plugin skills are namespaced:

```
/ha:ha-integration
/ha:ha-panel-design
```

Update later with `/plugin marketplace update pineapple-claude-hacs`.

### Manual (symlink)

Prefer the files loose as plain `/ha-integration` and `/ha-panel-design` commands? Symlink the
`SKILL.md` files into your commands directory:

```bash
git clone git@github.com:PineappleEmperor/pineapple-claude-hacs.git
ln -s "$PWD/pineapple-claude-hacs/plugins/ha/skills/ha-integration/SKILL.md"  ~/.claude/commands/ha-integration.md
ln -s "$PWD/pineapple-claude-hacs/plugins/ha/skills/ha-panel-design/SKILL.md" ~/.claude/commands/ha-panel-design.md
```

To have Claude invoke them automatically when relevant, add a rule to your global
`~/.claude/CLAUDE.md`:

```markdown
## Home Assistant integrations
When the task touches a HA custom integration (a `custom_components/<domain>/` package,
a `manifest.json` with a `domain`, a config/options flow, or platform code), invoke the
`ha-integration` skill before writing or modifying integration code. Re-invoke after a
`/compact`, since compaction can drop the skill's guidance from context.

## Home Assistant panels
When the task touches a HA custom panel or any display/UI layer, invoke the
`ha-panel-design` skill before changing it. Re-invoke after a `/compact`.
```

## Why

I'm a programmer; my HA integrations are built with AI (Claude, via Claude Code) under human
direction. These skills are how I keep that collaboration consistent — the AI and I challenge
each other's choices, and the hard-won conventions live here rather than in my head. Every
change to an integration is still human-reviewed before it merges.

## License

[Creative Commons Attribution-NonCommercial 4.0 International](LICENSE) (CC BY-NC 4.0) —
share and adapt with credit, **non-commercial use only**.

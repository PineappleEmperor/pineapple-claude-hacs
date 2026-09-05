# Versioning this marketplace repo

Repo-local, deliberately outside `plugins/`: it describes how **this** repository ships,
not anything a scaffolded integration does. An integration's version rides the release
zip and never touches its repo; none of the below applies there.

## No version is declared anywhere

`plugin.json` has no `version` field and neither does the marketplace entry. From the
[plugin marketplace reference](https://code.claude.com/docs/en/plugin-marketplaces):

> For git-based sources, if you omit `version`, Claude Code uses the source's resolved
> commit SHA, so users get an update whenever that commit changes; this is the simplest
> setup for internal or actively developed plugins.

So the plugin's version **is** the commit on `main`, and users pick up changes as they
land. Releases and tags still exist — they carry the changelog and mark what shipped —
they simply no longer gate who receives what.

## Why not semantic versions

A declared version pins updates: users receive a new copy only when that string changes,
so the string has to be written into a committed file by *someone*. Every way of doing
that costs something:

| Writer | Cost |
|---|---|
| A human, once per cycle | a manual step in a release process built to have none |
| CI, by opening a PR | a bot PR per release, and a jam when two releases land close together |
| CI, pushing to `main` | a standing bypass of branch protection for the release token |

The last was rejected on a specific ground worth recording: a permanent bypass is
available at exactly the moment someone is under pressure to land a red PR. The guard
against using it is not having it.

Semantic versions are nicer to read. They are not worth a machine that writes to `main`,
and this repo is developed continuously rather than in discrete supported releases, which
is the case the SHA fallback is designed for.

## What this removed

`sync_plugin_version.yml`, `scripts/sync_plugin_version.py` and its tests, the
`Manifests agree` gate step, the version comparison in `version-gate`, and the hand-bump
convention. `Version validation` survives as an advisory that prints what the merged
labels imply for the next release tag; it cannot fail.

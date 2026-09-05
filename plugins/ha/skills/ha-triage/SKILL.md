---
name: ha-triage
description: Use when something in a Home Assistant instance is misbehaving and the question is what is actually wrong — most often from a log (`home-assistant.log`, a Settings → System → Logs download, a pasted dump), but also from a symptom with no log at hand. Reach for it on "thousands of errors after restart", "what is spamming my log", "is this error real or noise", a repeating `websocket_api` pending-messages burst, `extra keys not allowed` from a script or automation, a `notify.mobile_app_*` service that stopped existing, or a Z-Wave value id that no longer resolves. Also when a companion-app notification image works on Wi-Fi but fails on cellular. NOT for writing integration code — that is the `ha-integration` skill.
---

# Home Assistant Triage

Input is a `home-assistant.log`, a **Settings → System → Logs** download, or a pasted dump.
Turn thousands of log lines into a short ranked list of *actionable* issues, separating real
faults from the background noise HA emits constantly.

**A raw error count is meaningless** — one slow client emits 1000+ identical lines; one config
typo emits one. Rank by distinct root cause, never by line count.

Most of what a log reports is config, automation or external-device trouble rather than
integration code. When a cluster does land under `custom_components.<domain>`, hand off to the
`ha-integration` skill.

## Cached facts — re-derive before trusting

Every row below was verified against `home-assistant/core@dev` and the companion-app docs
on **2026-08-24**. They are the claims most likely to rot; check any older than ~3 months
before acting on one.

| Fact | Value | Verify at |
|---|---|---|
| `color_temp` / `kelvin` removed from `light.turn_on` | HA **2026.3**; state attributes `color_temp`, `min_mireds`, `max_mireds` went too | developers.home-assistant.io/blog/2026/02/23/remove-deprecate-light-features |
| websocket pending-message limit | `MAX_PENDING_MSG = 4096`, peak warning at 1024 held 10s | `websocket_api/const.py` |
| log line format | `%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s] %(message)s` | `homeassistant/bootstrap.py` |
| notification size caps | image 10 MB both platforms · video 50 MB both · audio 5 MB iOS | companion.home-assistant.io/docs/notifications/notification-attachments |
| `/local` cache header | `Cache-Control: public, max-age=2678400` (31 days) | `homeassistant/components/http/static.py` |

## Step 1 — Build (or load) the device inventory FIRST

Logs identify clients/devices by **opaque tokens** — an IP, a browser user-agent, a Z-Wave `node_id`, a `notify.mobile_app_*` slug, a UniFi/camera hostname. Triage stalls every time on "what *is* `192.168.1.42`?". Resolve it **once**, up front, into a persistent map so every future triage is instant.

**The map is user/environment-specific — it does NOT belong in this (shareable) skill repo.** Keep it in a **local, git-ignored file next to the logs** (e.g. `device_map.md` in the log directory) or in Claude auto-memory. Never commit a home's IP/device layout to a public repo.

**Up-front Q&A** — when no map exists, extract the distinct tokens from the log and ask the user to name each once:

```bash
# Web/app clients: IP + device fingerprint (SM-X210 = Galaxy Tab, KFTRPWI = Amazon Fire, etc.)
grep -oE "from [0-9.]+ \([^)]*\)" LOG | sort -u   # every client, not just those with a Build/ token
# All LAN IPs by frequency
grep -oE "\b(10|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9.]+" LOG | sort | uniq -c | sort -rn
# Named device tokens worth resolving
grep -oE "mobile_app_[a-z0-9_]+|node_id=[0-9]+|notify\.[a-z0-9_]+" LOG | sort | uniq -c | sort -rn
```

Then ask the user to fill **device · room/owner · role** for each token. Store as a table:

```markdown
| Token | Device | Room / owner | Role |
|-------|--------|--------------|------|
| 192.168.1.42 (SM-X210) | Android tablet | Kitchen | Wall dashboard |
| node_id=3 | Z-Wave keypad | Front door | Alarm panel entry |
| notify.mobile_app_pixel | Phone | (owner) | Alarm notifications |
```

Decode common fingerprints without asking: `SM-*` = Samsung Galaxy (Tab/phone), `KF*` or `Silk/` = Amazon Fire (current Silk user-agents often omit the `Build/` token entirely), `Pixel*` = Google Pixel, `iPad`/`iPhone` = Apple. Ask only for room/role.

## Step 2 — Aggregate by logger, not by line

```bash
grep -oE "(ERROR|WARNING|CRITICAL) \([^)]+\) \[[^]]+\]" LOG | sort | uniq -c | sort -rn
# Tracebacks are attributed to their header line only — count them separately:
grep -c "^Traceback" LOG
```

Collapse each logger cluster to one row. Then read **one representative line** per cluster — not all of them.

## Step 3 — Classify each cluster: noise vs actionable

**Known noise — acknowledge once, do not chase:**

| Pattern | Why it's noise |
|---------|----------------|
| `[homeassistant.loader] We found a custom integration X which has not been tested` | Boot banner, **one per directory under `custom_components/`** — not per HACS install, so a hand-copied or installed-but-unconfigured integration warns too. Once per restart. Benign. |
| `[websocket_api.http.connection] … Reached 4096 pending messages` | A client that cannot keep up. **One line per connection** — the socket is then closed (`_cancel()`), and the code explicitly suppresses further logging, so a high count means many reconnect cycles, not one noisy client. Also grep the earlier warning: `Stayed over 1024 for 10 seconds`, which fires before the kill. Resolve the connection's IP via the map before concluding. |
| cloud-relay and transient network errors (`ClientConnectionResetError`, `Task exception was never retrieved`) | Remote-access and network transients. Ignore unless frequent **and** correlated with an outage. |
| a cloud integration's one-off fetch failure | API/device blips. Ignore unless sustained — sustained means that integration's reauth or availability handling, not the log. |

**Actionable — real bugs to fix:**

- **`extra keys not allowed @ data['<key>']`** in a script/automation `call_service` → a **service-schema deprecation**. The live one: `light.turn_on` **removed `color_temp` and `kelvin` in HA 2026.3** — use **`color_temp_kelvin`** (kelvin = `1000000 / mired`, floored). The same release removed the `color_temp`, `min_mireds` and `max_mireds` **state attributes**, so templates and dashboards break too, not just service calls. Grep the config for all four names.
- **`Action notify.mobile_app_* not found`** / **`Service … not found`** → a referenced entity/service was renamed or its device removed (re-onboarded phone, deleted integration). Update the automation to the current slug.
- **Z-Wave `NotFoundError: Value N-CC-… not found on node Node(node_id=N)`** → a `zwave_js.set_value` targets a value id the node no longer exposes (most often a re-interview, a firmware change, or the wrong endpoint — heuristics from community reports, not documented behaviour). Resolve `node_id` via the map, re-check the value id in the device's Z-Wave page.
- **`Bad credentials` / auth errors** from any integration holding a token → expired credential. Reconfigure that integration; it will not recover on its own.
- **Anything under `custom_components.<your_domain>`** → your code. Trace it (publish→subscribe→handler) per *Debugging discipline* in the `ha-integration` skill (`ha-integration/reference/discipline.md`); this is the only cluster the rest of this skill directly acts on.

## Step 4 — Report

Ranked table: **severity · cluster · root cause · fix · evidence (`timestamp` / `file:line`)**. State explicitly which clusters are *known noise* (so the user stops worrying about a scary count) and which are *actionable*. Resolve every opaque token through the device map so the report reads in plain device names ("Kitchen wall tablet", not `192.168.1.42`). If a fix is config-side (scripts/automations/integration settings) and you only have the log, say so and offer to apply it once given the config path.

## Companion-app notification images (off-network delivery)

⚠️ **This section is verified against the companion-app docs, not against a live instance,
and a user reports images failing in practice.** Treat the fixes below as candidates, not
settled answers, until reproduced. In particular: fetching an image at notification time
adds a round trip that can time out on a slow link, so *storing* the image and serving it
may be the more reliable shape — which then makes authenticated file access the thing to
get right, rather than URL form. Re-derive before advising.

Recurring config-side fix: a `notify.mobile_app_*` image "works on Wi-Fi, fails on cellular". Root cause is always that the **phone** downloads the attachment over the internet through Nabu Casa — so anything only reachable on the LAN, or served stale, breaks off-network. Two causes:

1. **Hardcoded LAN / internal URL** (`http://192.168.x.x…`, an `internal_url`-based absolute) — unreachable off-network. Use a **relative** path; the companion app prepends the *active* base URL (cloud when remote) and adds auth. Attachments must be reachable from the internet, but not necessarily unauthenticated — the app supplies the auth headers.
2. **Stale cached image** — the killer, and the mechanism is usually misdiagnosed. A snapshot written to a **fixed** `/config/www/…` filename and served via `/local/…` is sent with `Cache-Control: public, max-age=2678400` — HA's own 31-day header on static paths, not a CDN. The phone/OS/app HTTP cache then serves you the *previous* image (or a pre-first-write 404). It does **not** go away off Nabu Casa. Compounded by a write→push race, where the push beats the file flush.

**Fixes, best first:**

- **Live camera frame, per platform.** Android: `image: /api/camera_proxy/camera.<name>`. iOS: the camera stream via `data: entity_id: camera.<name>`. The `camera_proxy` path is documented Android-only — using it as a universal answer silently fails on iOS. Either form beats a snapshot: no file, no race, no static cache, framed at fetch time.
- **Point at a public URL** when the image is already internet-hosted — skips HA entirely, and lets you drop any `downloader` + `delay` steps.
- **Keep a frozen local snapshot** only if you must: add a cache-buster `?v={{ now().timestamp() | int }}` and a ~1 s `delay` after `camera.snapshot` so the write flushes.

**Keys, sizes and replacement — check the docs before "modernising" a working config:**

- **`attachment:` is not legacy.** It is a current, iOS-specific block (`hide-thumbnail`, `lazy`, `url`, `content-type`) and its `url` deliberately overrides `image`/`video`/`audio`. Replacing it with `image:` loses `hide-thumbnail` and `lazy`, which have no equivalent.
- **`content-type: jpeg` is valid.** It is used when the URL carries no usable extension; a bare extension is what the docs ask for. Do not "fix" it to `image/jpeg`.
- **Size caps:** image **10 MB on both platforms**, video 50 MB both, audio 5 MB iOS-only. iOS 2021.5+ retries a larger file when the content is opened.
- **A reused `tag:` replaces the previous notification** on both platforms — give each alert source a distinct one. iOS cannot replace *critical* notifications, and on Android a tag reused across different `group`s misbehaves.

> **Scope note:** most HA log errors are **config / automation / external-device** issues, *not* custom-integration code. This skill triages and routes them; the editing patterns in the `ha-integration` skill apply only to the `custom_components.<your_domain>` cluster.

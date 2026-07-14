# Implementing a workspacer plugin (shared context)

You are turning ONE plugin scaffold in this folder into a real, working plugin.

## Rules of engagement

- **Only modify files inside your own plugin directory** (`workspacer-plugins/<name>/`). It's a standalone git repo with a private GitHub remote (`origin`, branch `main`).
- You MAY **read** (never write) reference files elsewhere under `/home/djtouchette/Work/worky/workspacer/` to learn the platform.
- Do NOT touch the main `workspacer` repo, other plugin dirs, or anything outside your directory.

## Platform reference — read these to get exact protocol + payload shapes

- `/home/djtouchette/Work/worky/workspacer/services/hub/docs/rules-engine-plugin.md` — bus protocol (§3), events + capabilities + commands reference (§4). **Read this first.**
- `/home/djtouchette/Work/worky/workspacer/services/hub/README.md` — the capability tables (main + brain) and authorization model.
- `/home/djtouchette/Work/worky/workspacer/apps/desktop/src/main/services/hubCapabilities.ts` — **source of truth for capability parameters.** Grep it for the exact method names you call (e.g. `registerCapability('agents.sendMessage'`, `'claude.approve'`, `'sessions.snapshot'`) to see the params each expects and returns.
- `/home/djtouchette/Work/worky/workspacer/services/hub/examples/editor/` — reference bus-native **webview** (capability-scoped).
- The implemented sibling plugins in this folder — `fleet-radar/ui/index.html` is a reference **webview**, `fleet-guardian/server.js` a reference **sidecar** (bus framing, capability calls, settings, the `agents.list` poll pattern).

## Bus protocol (WebSocket `ws://127.0.0.1:7895/bus?token=<t>`)

- **subscribe:** `{op:'subscribe', topics:[...]}` — topics support `ns.*` and `*`.
- **call a capability:** `{op:'call', id, method, params}` → reply `{op:'result', id, result}` or `{op:'error', id, error}`.
- **publish an event/command:** `{op:'publish', event:{type, source, data}}`.
- **inbound events:** `{op:'event', event:{type, source, data}}`.

Key event payloads (see the docs for the full list):
- `agent.state_changed` → `{sessionId, hookEvent, mode, cwd}`; `mode ∈ unknown|input|responding|approval|question|stopped`; `hookEvent` is the raw Claude hook (`SessionStart`,`PreToolUse`,`PostToolUse`,`Stop`,`SessionEnd`,`Notification`,…).
- `agent.snapshot` / `agent.statusline` → per-session snapshot / live `{sessionId, statusLine}` (model, context %, cost, rate-limit windows).
- `workflow.completed`/`workflow.failed` → `{sessionId, cwd, runId, name, status, durationMs, totalTokens, totalToolCalls, agents}`.
- `ui.pane.focused`/`ui.tab.focused`/`ui.workspace.focused` → `{paneId,type,workspaceId,tabId}` / `{tabId}` / `{workspaceId}`.
- `fs.changed` → file-watch notifications (you must first `call('fs.watch', {paths:[...]})`).

## The scaffold

- `plugin.json` — the manifest. Its `consumes`, `capabilities`, `emits`, `settings` are already declared. **A plugin can only subscribe to / call / publish what it declares** — if your implementation genuinely needs another capability or event, add it to the manifest too (and mention it in the README). For `fs.*`/`search.project`, capabilities MUST be object form `{method, paths:["${agentCwd}"]}`.
- **Sidecar** (`server.js`): the stub connects to the bus and logs events in `onEvent()`. It exposes `call(method, params)`, `publish(type, data)`, `log(msg)`, and `settings` (parsed from `process.env.WKS_SETTINGS`). Replace `onEvent` with real logic. Keep it **zero-dependency** — Node ≥22 built-ins only (`WebSocket`, `fetch`, `http`, `fs`, `path`, `child_process`).
- **Webview** (`ui/index.html`): the stub connects and logs in `onEvent()`. It exposes `call`, `publish`, `log`. Read host settings from `window.__WKS_SETTINGS__` if needed; theme via `--wks-*` CSS vars. Note: a webview only runs while its pane is open.

## Deliverable

1. Implement the **real behavior** in your task (not just logging). Be robust: try/catch around capability calls, tolerate malformed events, keep the reconnect behavior.
2. Update the README's **Implement** section to describe what you actually built and which settings it uses.
3. Verify: sidecars must pass `node --check server.js`; briefly `node server.js` to confirm it starts and *retries* (rather than crashing) when the hub isn't up. Webviews: confirm the HTML parses and has no obvious JS errors.
4. Commit everything and push:
   ```
   git add -A
   git commit -m "<clear message>"   # end the message with the trailer below
   git push
   ```
   Trailer (last line of the commit message):
   `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

You can't run a full live end-to-end test (the hub may not be running). Implement carefully against the documented protocol/payloads and static-verify.

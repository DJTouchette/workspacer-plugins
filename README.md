# workspacer plugins

Official plugin catalog for [workspacer](https://github.com/DJTouchette/workspacer) — a local-first control plane for running many coding agents side by side.

Each plugin lives in its own repo and installs straight from the app: **command palette → "Install Plugin…" → paste the repo** (e.g. `DJTouchette/workspacer-plugin-fleet-radar`). The hub downloads it, wires its bus token, and supervises it. All plugins are zero-dependency (Node ≥ 22 built-ins only) and MIT licensed.

A machine-readable version of this catalog lives in [`index.json`](index.json) (fetch it at `https://raw.githubusercontent.com/DJTouchette/workspacer-plugins/main/index.json`) — one entry per plugin with id, category, kind, one-line description, install ref, and the permissions its manifest declares. Regenerate it with `python3 build_index.py` after adding or changing a plugin.

## The plugins

### Dashboards (webview panes)

| Plugin | Repo | What it does |
|---|---|---|
| 📡 **Fleet Radar** | [`workspacer-plugin-fleet-radar`](https://github.com/DJTouchette/workspacer-plugin-fleet-radar) | Always-on big-screen view of your whole agent fleet — attention rings, context bars, live cost. |
| 💰 **Cost HUD** | [`workspacer-plugin-cost-hud`](https://github.com/DJTouchette/workspacer-plugin-cost-hud) | Slim always-on spend + rate-limit heads-up display (5h / weekly / monthly windows). |
| 🎯 **Focus Tracker** | [`workspacer-plugin-focus-tracker`](https://github.com/DJTouchette/workspacer-plugin-focus-tracker) | Wakatime-style view of where your attention goes across agents and panes. |

### Workbench (webview panes)

| Plugin | Repo | What it does |
|---|---|---|
| 🗒️ **Project Notes** | [`workspacer-plugin-project-notes`](https://github.com/DJTouchette/workspacer-plugin-project-notes) | Per-project markdown notes with tags — saved in the project, shared by every agent working in it. |

### Automation (sidecars — always on, even with their pane closed)

| Plugin | Repo | What it does |
|---|---|---|
| ⚖️ **Policy Approver** | [`workspacer-plugin-policy-approver`](https://github.com/DJTouchette/workspacer-plugin-policy-approver) | Supervise by exception: auto-approve read-only tools, hard-block dangerous ones (`rm -rf`, force-push, …). |
| 🛡 **Fleet Guardian** | [`workspacer-plugin-fleet-guardian`](https://github.com/DJTouchette/workspacer-plugin-fleet-guardian) | Autonomy with brakes: pause the spendiest agent near a rate limit, downgrade models past a budget. |
| 🔗 **Escalation Chains** | [`workspacer-plugin-escalation-chains`](https://github.com/DJTouchette/workspacer-plugin-escalation-chains) | Self-healing fleet: auto-spawn a successor (with a handoff brief) when an agent or workflow fails. |
| 🚪 **Typecheck Gate** | [`workspacer-plugin-typecheck-gate`](https://github.com/DJTouchette/workspacer-plugin-typecheck-gate) | Don't let an agent "finish" red: gate the turn on a passing check command and feed errors back. |
| 🧪 **Test on Save** | [`workspacer-plugin-test-on-save`](https://github.com/DJTouchette/workspacer-plugin-test-on-save) | Run the test suite when an agent edits code; failing output goes straight back to the agent. |
| 🚦 **CI Watcher** | [`workspacer-plugin-ci-watcher`](https://github.com/DJTouchette/workspacer-plugin-ci-watcher) | Watch GitHub CI after a push (`gh` CLI) and report the verdict back into the agent's loop. |

### Reach (getting workspacer off the desktop)

| Plugin | Repo | What it does |
|---|---|---|
| 💬 **Slack Bridge** | [`workspacer-plugin-slack-bridge`](https://github.com/DJTouchette/workspacer-plugin-slack-bridge) | Monitor and steer the fleet from Slack/Discord — approvals, questions, and workflow results, bidirectional. |
| 📱 **Phone Push** | [`workspacer-plugin-phone-push`](https://github.com/DJTouchette/workspacer-plugin-phone-push) | The lightest remote awareness: push "needs you" moments to your phone via ntfy / Pushover / webhook. |
| 📰 **Standup Digest** | [`workspacer-plugin-standup-digest`](https://github.com/DJTouchette/workspacer-plugin-standup-digest) | A nightly report of what the fleet did — workflows, diffs, top agents — to Slack/Discord or a notification. |

## How plugins work

A plugin is a folder with a `plugin.json` manifest plus either a **webview** (a static UI the hub serves into a pane) or a **sidecar** (a supervised process). Both talk to the hub's WebSocket bus with a token scoped to exactly the capabilities and events the manifest declares — a plugin only gets what it asks for, and you can inspect a repo's manifest from the install dialog before any code runs.

Settings declared in the manifest get a generated UI in workspacer's Settings; sidecars receive the values as `WKS_SETTINGS` and are restarted when you change them.

## Writing your own

Start from any repo above (the sidecars share a ~70-line zero-dep scaffold) and see the platform docs in the main repo: [`services/hub/README.md`](https://github.com/DJTouchette/workspacer/blob/master/services/hub/README.md) for the bus protocol, capabilities, and authorization model, and [`services/hub/docs/rules-engine-plugin.md`](https://github.com/DJTouchette/workspacer/blob/master/services/hub/docs/rules-engine-plugin.md) for a worked build spec.

## License

MIT — each plugin repo carries its own LICENSE file.

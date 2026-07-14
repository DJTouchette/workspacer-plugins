#!/usr/bin/env python3
"""Generate runnable workspacer plugin scaffolds.

Two shared code templates (a zero-dep Node sidecar and a bus-native webview),
plus per-plugin manifest + README. Grounded in the real hub bus protocol:
  connect ws://127.0.0.1:7895/bus?token=<t>; {op:subscribe|call|publish};
  receive {op:event|result|error}. Sidecars read WKS_BUS_TOKEN / .bus-token.
"""
import json
import os
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
VENDOR = "djtouchette"

# ── Shared: zero-dependency Node sidecar (Node >=22 for global WebSocket) ──────
SERVER_JS = r'''#!/usr/bin/env node
// Generic workspacer plugin sidecar scaffold — zero dependencies.
// Node >= 22 (global WebSocket) and >= 18 (global fetch). Reads its own
// plugin.json for the bus topics it subscribes to and the capabilities it may
// call, connects to the hub bus, logs events, and serves a tiny status pane.
// Implement your logic in onEvent(). See README for events + capabilities.
const http = require('http');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const manifest = JSON.parse(fs.readFileSync(path.join(DIR, 'plugin.json'), 'utf8'));
const PORT = Number(process.env.PORT || (manifest.server && manifest.server.port) || 9200);

// The hub injects the bus URL + this plugin's scoped token. Accept the common
// conventions so the scaffold runs however your hub wires it.
const BUS_URL = process.env.WKS_BUS_URL || 'ws://127.0.0.1:7895/bus';
function readToken() {
  if (process.env.WKS_BUS_TOKEN) return process.env.WKS_BUS_TOKEN;
  try { return fs.readFileSync(path.join(DIR, '.bus-token'), 'utf8').trim(); } catch { return ''; }
}
// Host-injected settings (from manifest `settings`), passed as JSON in env.
let settings = {};
try { settings = JSON.parse(process.env.WKS_SETTINGS || '{}'); } catch {}

const TOPICS = manifest.consumes || [];
const recent = [];
let ws = null, connected = false, callSeq = 0;
const pending = new Map();

function log(msg) {
  console.log('[' + manifest.id + '] ' + msg);
  recent.unshift(new Date().toISOString() + '  ' + msg);
  if (recent.length > 100) recent.pop();
}

// Call a hub capability (must be declared in plugin.json `capabilities`).
function call(method, params) {
  return new Promise((resolve, reject) => {
    if (!connected) return reject(new Error('not connected'));
    const id = 'c' + (++callSeq);
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ op: 'call', id, method, params: params || {} }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout')); } }, 8000);
  });
}
// Publish an event/command (must be declared in `emits`).
function publish(type, data) {
  if (connected) ws.send(JSON.stringify({ op: 'publish', event: { type, source: manifest.id, data: data || {} } }));
}

function connect() {
  const tok = readToken();
  ws = new WebSocket(BUS_URL + (tok ? '?token=' + encodeURIComponent(tok) : ''));
  ws.addEventListener('open', () => {
    connected = true;
    if (TOPICS.length) ws.send(JSON.stringify({ op: 'subscribe', topics: TOPICS }));
    log('connected; subscribed to ' + (TOPICS.join(', ') || '(nothing)'));
  });
  ws.addEventListener('message', (ev) => {
    let f; try { f = JSON.parse(ev.data); } catch { return; }
    if (f.op === 'event' && f.event) onEvent(f.event).catch((e) => log('onEvent error: ' + e.message));
    else if (f.op === 'result' && pending.has(f.id)) { pending.get(f.id).resolve(f.result); pending.delete(f.id); }
    else if (f.op === 'error' && pending.has(f.id)) { pending.get(f.id).reject(new Error(f.error)); pending.delete(f.id); }
  });
  ws.addEventListener('close', () => { connected = false; setTimeout(connect, 1500); });
  ws.addEventListener('error', () => { try { ws.close(); } catch {} });
}

// ── Your plugin logic ─────────────────────────────────────────────────────────
async function onEvent(event) {
  log('event ' + event.type);
  // TODO: react to `event`. Use call('cap.method', {...}) for capabilities,
  // publish('command.x', {...}) for commands, or fetch(...) to reach outside.
}

const server = http.createServer((req, res) => {
  if (req.url === '/health') { res.writeHead(200); return res.end('ok'); }
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end('<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=2>'
    + '<title>' + manifest.name + '</title><body style="font-family:system-ui;'
    + 'background:var(--wks-bg-base,#161616);color:var(--wks-text-primary,#e8e8e8);margin:0;padding:14px">'
    + '<h2 style="font-size:1rem">' + manifest.name + '</h2>'
    + '<p style="color:var(--wks-text-muted,#888);font-size:.8rem">'
    + (connected ? '\u{1F7E2} connected to hub' : '\u{1F534} disconnected')
    + ' · subscribed to ' + (TOPICS.join(', ') || '(nothing)') + '</p>'
    + '<pre style="font-size:.7rem;color:var(--wks-text-faint,#777);white-space:pre-wrap">'
    + (recent.map(escapeHtml).join('\n') || 'waiting for events…') + '</pre>'
    + '<p style="color:var(--wks-text-faint,#777);font-size:.7rem">Scaffold — edit '
    + '<code>server.js</code> (onEvent) to implement.</p>');
});
function escapeHtml(s) { return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }
server.listen(PORT, '127.0.0.1', () => log('pane on http://127.0.0.1:' + PORT));
connect();
'''

# ── Shared: bus-native webview (only runs while its pane is open) ──────────────
WEBVIEW_HTML = r'''<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>__TITLE__</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, sans-serif;
           background: var(--wks-bg-base, #161616); color: var(--wks-text-primary, #e8e8e8); }
    header { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
             border-bottom: 1px solid var(--wks-border-subtle, #2a2a2a); }
    header h1 { font-size: 0.95rem; margin: 0; font-weight: 600; }
    #conn { font-size: 0.65rem; color: var(--wks-text-muted, #888); display: flex; align-items: center; gap: 5px; margin-left: auto; }
    #conn .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--wks-text-faint, #666); }
    #conn.on .dot { background: var(--wks-success, #3fb950); box-shadow: 0 0 5px var(--wks-success, #3fb950); }
    #log { font-size: 0.66rem; color: var(--wks-text-tertiary, #aaa); padding: 12px 14px;
           font-family: ui-monospace, monospace; white-space: pre-wrap; }
    .hint { padding: 10px 14px; color: var(--wks-text-faint, #777); font-size: 0.72rem; }
  </style>
</head>
<body>
  <header>
    <h1>__ICON__ __TITLE__</h1>
    <div id="conn"><span class="dot"></span><span id="ct">connecting…</span></div>
  </header>
  <div class="hint">Scaffold — subscribes to <code>__TOPICS_TEXT__</code>. Edit <code>ui/index.html</code> to render your view.</div>
  <div id="log"></div>
  <script>
    // Bus-native webview: the host injects this plugin's scoped token as
    // ?busToken=… in our URL; present it so the hub scopes us to our manifest.
    const BUS_TOKEN = new URLSearchParams(location.search).get('busToken') || '';
    const BUS = 'ws://127.0.0.1:7895/bus' + (BUS_TOKEN ? '?token=' + encodeURIComponent(BUS_TOKEN) : '');
    const TOPICS = __TOPICS__;
    let ws, connected = false, callSeq = 0;
    const pending = new Map();
    const lines = [];
    const $ = (id) => document.getElementById(id);
    function log(m) { lines.unshift(new Date().toLocaleTimeString() + '  ' + m); if (lines.length > 200) lines.pop(); $('log').textContent = lines.join('\n'); }
    function call(method, params) {
      return new Promise((resolve, reject) => {
        if (!connected) return reject(new Error('not connected'));
        const id = 'c' + (++callSeq); pending.set(id, { resolve, reject });
        ws.send(JSON.stringify({ op: 'call', id, method, params: params || {} }));
        setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout')); } }, 8000);
      });
    }
    function publish(type, data) { if (connected) ws.send(JSON.stringify({ op: 'publish', event: { type, source: '__ID__', data: data || {} } })); }
    function setConn(on) { connected = on; $('conn').classList.toggle('on', on); $('ct').textContent = on ? 'connected' : 'disconnected'; }
    function connect() {
      ws = new WebSocket(BUS);
      ws.onopen = () => { setConn(true); if (TOPICS.length) ws.send(JSON.stringify({ op: 'subscribe', topics: TOPICS })); log('connected; subscribed to ' + (TOPICS.join(', ') || '(nothing)')); };
      ws.onmessage = (e) => {
        let f; try { f = JSON.parse(e.data); } catch { return; }
        if (f.op === 'event' && f.event) { onEvent(f.event); }
        else if (f.op === 'result' && pending.has(f.id)) { pending.get(f.id).resolve(f.result); pending.delete(f.id); }
        else if (f.op === 'error' && pending.has(f.id)) { pending.get(f.id).reject(new Error(f.error)); pending.delete(f.id); }
      };
      ws.onclose = () => { setConn(false); setTimeout(connect, 1000); };
      ws.onerror = () => { try { ws.close(); } catch {} };
    }
    // ── Your view logic ──────────────────────────────────────────────────────
    function onEvent(event) {
      log(event.type + '  ' + JSON.stringify(event.data || {}).slice(0, 120));
      // TODO: render your dashboard from these events. call('agents.list') etc.
    }
    connect();
  </script>
</body>
</html>
'''

README_TMPL = """# {title}

{tagline}

A [workspacer](https://github.com/DJTouchette/workspacer) hub plugin ({kind}). **Runnable scaffold** — it loads, connects to the hub bus, and shows live activity; the real logic is stubbed with clear TODOs.

## What it does

{desc}

## Bus wiring

- **Subscribes to:** {consumes}
- **Calls capabilities:** {capabilities}
- **Emits:** {emits}
{settings_doc}
## Run it

1. Copy this folder to `~/.config/workspacer/plugins/{name}/` (or install from GitHub via the workspacer command palette → *Install from GitHub…* → `DJTouchette/{repo}`).
2. Reload plugins in workspacer.{run_extra}
3. Open the **{title}** pane{hotkey_doc}.

{impl_section}

## Layout

```
{layout}
```

## License

MIT
"""

GITIGNORE = "node_modules/\n.bus-token\n.disabled\n.install-source\n*.log\n.DS_Store\n"

# ── Plugin definitions ────────────────────────────────────────────────────────
# capability entries: str, or (method, [paths]) for fs.*/search.* (object form).
PLUGINS = [
    # id, type, title, icon, hotkey, port, consumes, capabilities, emits, tagline, desc, settings
    dict(name="fleet-radar", type="webview", title="Fleet Radar", icon="\U0001F4E1",
         hotkey="ctrl+shift+r", scope="global",
         consumes=["agent.snapshot", "agent.state_changed", "workflow.*"],
         capabilities=["agents.list"], emits=["command.focus_agent"],
         tagline="Always-on big-screen view of your whole agent fleet.",
         desc="A TV-style grid of every agent — who's working, who needs you, live cost/context — driven by `agent.snapshot` + `agent.state_changed`. Click an agent to focus it in workspacer (`command.focus_agent`).",
         settings=[]),
    dict(name="cost-hud", type="webview", title="Cost HUD", icon="\U0001F4B0",
         hotkey="ctrl+shift+u", scope="global",
         consumes=["agent.statusline", "agent.snapshot"],
         capabilities=["agents.list"], emits=[],
         tagline="A slim always-on spend + rate-limit heads-up display.",
         desc="Shows fleet-wide cost and the 5h / weekly / monthly usage windows from `agent.statusline`, so you can see how close you are to a limit at a glance.",
         settings=[]),
    dict(name="focus-tracker", type="webview", title="Focus Tracker", icon="\U0001F3AF",
         hotkey="ctrl+shift+f", scope="global",
         consumes=["ui.pane.focused", "ui.tab.focused", "ui.workspace.focused", "agent.state_changed"],
         capabilities=[], emits=[],
         tagline="Wakatime-style view of where your attention goes across agents.",
         desc="Consumes the `ui.*` focus events to track which agents/panes you spend time in, and correlates with `agent.state_changed` to show where you're actually engaged.",
         settings=[]),
    dict(name="slack-bridge", type="sidecar", title="Slack Bridge", icon="\U0001F4AC",
         hotkey=None, scope="global", port=9201,
         consumes=["agent.state_changed", "workflow.completed", "workflow.failed"],
         capabilities=["notifications.post", "claude.approve", "claude.answer", "claude.setPermissionMode", "sessions.snapshot"],
         emits=[],
         tagline="Monitor and steer your fleet from Slack/Discord — bidirectionally.",
         desc="Pushes needs-you moments (`agent.state_changed` → approval/question/stopped) and workflow results to a Slack/Discord webhook. Bidirectional: a reply calls `claude.approve` / `claude.answer` / `claude.setPermissionMode` so you approve tools and answer questions from your phone.",
         settings=[dict(key="webhookUrl", label="Incoming webhook URL", type="string", default="", help="Slack/Discord incoming webhook for outbound messages."),
                   dict(key="botToken", label="Bot token (for replies)", type="string", default="", help="Optional: a bot token to receive replies and act on them."),
                   dict(key="channel", label="Channel", type="string", default="", help="Channel to post to.")]),
    dict(name="fleet-guardian", type="sidecar", title="Fleet Guardian", icon="\U0001F6E1",
         hotkey=None, scope="global", port=9202,
         consumes=["agent.snapshot", "agent.statusline"],
         capabilities=["agents.list", "claude.signal", "claude.setModel", "notifications.post"],
         emits=[],
         tagline="Autonomy with brakes: pause on rate limits, downgrade on budget.",
         desc="Watches account usage (`agent.statusline`). When you approach a rate-limit threshold it can `claude.signal` to pause spendy agents; when a session blows its budget it can `claude.setModel` it down to a cheaper model instead of stopping. NOTE: continuous per-session cost is not yet a bus event — until then this polls `agents.list`.",
         settings=[dict(key="rateLimitPct", label="Rate-limit pause threshold (%)", type="number", default=90, help="Pause spendy agents when a window crosses this utilization."),
                   dict(key="budgetUSD", label="Per-session budget (USD)", type="number", default=0, help="0 = off. Downgrade a session's model past this spend."),
                   dict(key="downgradeModel", label="Downgrade model", type="string", default="claude-haiku-4-5", help="Model to switch to on budget overrun.")]),
    dict(name="policy-approver", type="sidecar", title="Policy Approver", icon="⚖️",
         hotkey=None, scope="global", port=9203,
         consumes=["agent.state_changed"],
         capabilities=[("sessions.snapshot", None), "claude.approve", "claude.gate", "notifications.post"],
         emits=[],
         tagline="Auto-approve safe tools, hard-block dangerous ones.",
         desc="On `agent.state_changed` → approval, reads the pending tool (`sessions.snapshot`) and decides by policy: auto-`claude.approve` read-only tools and edits inside the agent's cwd, hard-block `rm -rf` / `git push --force`. Turns the fleet from babysit-every-prompt into supervise-by-exception.",
         settings=[dict(key="autoApproveReadonly", label="Auto-approve read-only tools", type="boolean", default=True, help="Approve Read/Grep/Glob etc. without prompting."),
                   dict(key="blockPatterns", label="Block patterns (comma-sep)", type="string", default="rm -rf,git push --force,:(){", help="Bash substrings that are always blocked.")]),
    dict(name="escalation-chains", type="sidecar", title="Escalation Chains", icon="\U0001F517",
         hotkey=None, scope="global", port=9204,
         consumes=["workflow.failed", "agent.state_changed"],
         capabilities=["agents.spawn", "claude.handoffBrief", "notifications.post"],
         emits=["command.spawn_agent"],
         tagline="Self-healing fleet: auto-spawn a successor when an agent fails.",
         desc="On `workflow.failed` or a session going `stopped`, automatically `agents.spawn` a successor (or `claude.handoffBrief` to hand off context) so a stuck agent escalates instead of silently dying.",
         settings=[dict(key="maxRetries", label="Max auto-retries", type="number", default=1, help="How many successors to spawn before giving up."),
                   dict(key="successorModel", label="Successor model", type="string", default="", help="Model for the spawned successor ('' = default).")]),
    dict(name="ci-watcher", type="sidecar", title="CI Watcher", icon="\U0001F6A6",
         hotkey=None, scope="global", port=9205,
         consumes=["workflow.completed", "agent.state_changed"],
         capabilities=["git.status", "agents.sendMessage", "notifications.post"],
         emits=[],
         tagline="Watch CI after a push and feed failures back to the agent.",
         desc="After an agent pushes, polls CI (e.g. `gh` / a CI API) and `agents.sendMessage`s the check results back to the agent that opened the PR — bridging external CI state into the agent loop.",
         settings=[dict(key="pollSeconds", label="Poll interval (s)", type="number", default=30, help="How often to poll CI."),
                   dict(key="repo", label="Repo (owner/name)", type="string", default="", help="Repo to watch ('' = infer from cwd).")]),
    dict(name="standup-digest", type="sidecar", title="Standup Digest", icon="\U0001F4F0",
         hotkey=None, scope="global", port=9206,
         consumes=["workflow.completed", "workflow.failed"],
         capabilities=["analytics.summary", "analytics.recent", ("git.numstat", None), "notifications.post"],
         emits=[],
         tagline="A nightly report of what the fleet did.",
         desc="Aggregates `workflow.completed` plus `analytics.summary` and `git.numstat` into a daily digest — agents run, tokens, cost, files changed — posted to a webhook or the notifications surface.",
         settings=[dict(key="postTime", label="Daily post time (HH:MM)", type="string", default="18:00", help="Local time to emit the digest."),
                   dict(key="webhookUrl", label="Webhook URL", type="string", default="", help="Where to post the digest ('' = notifications.post only).")]),
    dict(name="test-on-save", type="sidecar", title="Test on Save", icon="\U0001F9EA",
         hotkey=None, scope="agent", port=9207,
         consumes=["fs.changed"],
         capabilities=[("fs.watch", ["${agentCwd}"]), ("search.project", ["${agentCwd}"]), "agents.sendMessage", "notifications.post"],
         emits=[],
         tagline="Run the test suite when an agent edits code; feed results back.",
         desc="Watches the agent's working tree (`fs.watch` → `fs.changed`), debounces, runs your test command, and `agents.sendMessage`s failures back to the agent so it self-corrects.",
         settings=[dict(key="testCommand", label="Test command", type="string", default="npm test", help="Command run on change."),
                   dict(key="debounceMs", label="Debounce (ms)", type="number", default=1500, help="Wait this long after the last change before running.")]),
    dict(name="typecheck-gate", type="sidecar", title="Typecheck Gate", icon="\U0001F6AA",
         hotkey=None, scope="agent", port=9208,
         consumes=["agent.state_changed"],
         capabilities=["claude.gate", "notifications.post"],
         emits=[],
         tagline="Don't let an agent 'finish' with a red typecheck.",
         desc="When an agent reaches Stop, runs your typecheck/lint command and uses `claude.gate` to hold the turn open (with the errors) if it fails — so 'done' actually means green.",
         settings=[dict(key="checkCommand", label="Check command", type="string", default="npm run typecheck", help="Command that must exit 0 to pass the gate.")]),
    dict(name="phone-push", type="sidecar", title="Phone Push", icon="\U0001F4F1",
         hotkey=None, scope="global", port=9209,
         consumes=["agent.state_changed"],
         capabilities=["notifications.post"],
         emits=[],
         tagline="The lightest possible remote awareness — push needs-you to your phone.",
         desc="On any needs-you `agent.state_changed` (approval/question/stopped), sends a push via ntfy / Pushover / a webhook so you know an agent is waiting even away from the machine.",
         settings=[dict(key="provider", label="Provider", type="select", default="ntfy", options=["ntfy", "pushover", "webhook"], help="Push provider."),
                   dict(key="target", label="Topic / token / URL", type="string", default="", help="ntfy topic, Pushover user key, or webhook URL.")]),
]


def cap_manifest(caps):
    """Manifest capabilities: object form for fs.*/search.* (with paths)."""
    out = []
    for c in caps:
        if isinstance(c, tuple):
            method, paths = c
            if paths:
                out.append({"method": method, "paths": paths})
            else:
                out.append(method)
        else:
            out.append(c)
    return out


def cap_names(caps):
    return [c[0] if isinstance(c, tuple) else c for c in caps]


def build():
    names = []
    for p in PLUGINS:
        name = p["name"]
        repo = "workspacer-plugin-" + name
        names.append((name, repo, p["type"], p["title"], p["tagline"]))
        d = os.path.join(ROOT, name)
        os.makedirs(d, exist_ok=True)
        pid = VENDOR + "." + name
        is_sidecar = p["type"] == "sidecar"

        pane = {"type": pid, "title": p["title"], "icon": p["icon"], "scope": p["scope"]}
        if is_sidecar:
            pane["path"] = "/"
        manifest = {
            "id": pid,
            "name": p["title"],
            "apiVersion": "1",
        }
        if is_sidecar:
            manifest["server"] = {"command": "node", "args": ["server.js"], "port": p["port"], "health": "/health"}
        else:
            manifest["ui"] = "ui"
        manifest["panes"] = [pane]
        if p["hotkey"]:
            manifest["hotkeys"] = [{"id": "open-" + name, "default": p["hotkey"], "command": "open-pane:" + pid}]
        if p["settings"]:
            manifest["settings"] = p["settings"]
        if p["capabilities"]:
            manifest["capabilities"] = cap_manifest(p["capabilities"])
        if p["emits"]:
            manifest["emits"] = p["emits"]
        if p["consumes"]:
            manifest["consumes"] = p["consumes"]

        with open(os.path.join(d, "plugin.json"), "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")

        # Code
        if is_sidecar:
            with open(os.path.join(d, "server.js"), "w") as f:
                f.write(SERVER_JS)
            layout = "{n}/\n  plugin.json      # manifest (events + capabilities)\n  server.js        # zero-dep Node sidecar; implement onEvent()\n  README.md".format(n=name)
            run_extra = "\n   The hub supervises `node server.js` and injects the bus token."
            hotkey_doc = " from the command palette"
            impl = "## Implement\n\nEdit `server.js` → `onEvent(event)`. Subscribed topics arrive there; use `call('method', params)` for capabilities and `publish('command.x', data)` for commands. `settings` holds the host-injected config above."
        else:
            os.makedirs(os.path.join(d, "ui"), exist_ok=True)
            html = (WEBVIEW_HTML
                    .replace("__TITLE__", p["title"])
                    .replace("__ICON__", p["icon"])
                    .replace("__ID__", pid)
                    .replace("__TOPICS_TEXT__", ", ".join(p["consumes"]))
                    .replace("__TOPICS__", json.dumps(p["consumes"])))
            with open(os.path.join(d, "ui", "index.html"), "w") as f:
                f.write(html)
            layout = "{n}/\n  plugin.json      # manifest (events + capabilities)\n  ui/index.html    # bus-native webview; implement onEvent()\n  README.md".format(n=name)
            run_extra = ""
            hotkey_doc = (" (`%s`)" % p["hotkey"]) if p["hotkey"] else ""
            impl = "## Implement\n\nEdit `ui/index.html` → `onEvent(event)`. The webview only runs while its pane is open; use `call('method', params)` for capabilities and `publish('command.x', data)` for commands."

        settings_doc = ""
        if p["settings"]:
            rows = "\n".join("- `%s` (%s) — %s" % (s["key"], s["type"], s.get("help", "")) for s in p["settings"])
            settings_doc = "- **Settings:**\n" + rows + "\n"

        readme = README_TMPL.format(
            title=p["title"], tagline=p["tagline"], kind=p["type"], desc=p["desc"],
            consumes=", ".join("`%s`" % c for c in p["consumes"]) or "—",
            capabilities=", ".join("`%s`" % c for c in cap_names(p["capabilities"])) or "—",
            emits=", ".join("`%s`" % c for c in p["emits"]) or "—",
            settings_doc=settings_doc, name=name, repo=repo,
            run_extra=run_extra, hotkey_doc=hotkey_doc, impl_section=impl, layout=layout)
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write(readme)
        with open(os.path.join(d, ".gitignore"), "w") as f:
            f.write(GITIGNORE)
        print("scaffolded", name, "(" + p["type"] + ")")

    # Index README for the container
    idx = ["# workspacer-plugins\n",
           "Scaffolds for [workspacer](https://github.com/DJTouchette/workspacer) hub plugins. Each subfolder is its own GitHub repo (`workspacer-plugin-<name>`).\n",
           "| Plugin | Type | Repo | What |", "|---|---|---|---|"]
    for name, repo, typ, title, tagline in names:
        idx.append("| **%s** | %s | [`%s`](https://github.com/DJTouchette/%s) | %s |" % (title, typ, repo, repo, tagline))
    with open(os.path.join(ROOT, "README.md"), "w") as f:
        f.write("\n".join(idx) + "\n")
    print("wrote index README")


if __name__ == "__main__":
    build()

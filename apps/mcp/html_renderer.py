"""Static MCP App HTML for the attestation form.

Self-contained HTML with an inline MCP Apps bridge (JSON-RPC 2.0 over
postMessage). Applies host theme tokens from hostContext on connect and
on theme change. Field data arrives at runtime via ontoolresult.

Layout strategy: after rendering, measures content vs viewport height.
If content overflows, progressively enables multi-column grids and
tighter spacing to fit everything without scrolling. Uses
sendSizeChanged to request ideal height from the host.
"""

ATTESTATION_APP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Concord — Health Information</title>
<style>
:root { color-scheme: light dark; }
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif);
  background: var(--color-background-primary, transparent);
  color: var(--color-text-primary, #1a1a1a);
  padding: 12px 16px;
  line-height: 1.4;
  min-height: 60px;
  font-size: 0.8125rem;
}


#loading {
  text-align: center;
  padding: 24px 12px;
  color: var(--color-text-tertiary, #999);
  font-size: 0.75rem;
}

#form-container { display: none; }

.section {
  background: var(--color-background-secondary, rgba(0,0,0,0.02));
  border: 1px solid var(--color-border-primary, rgba(0,0,0,0.08));
  border-radius: var(--border-radius-lg, 10px);
  padding: 10px 12px;
  margin-bottom: 8px;
}

.fields-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px 12px;
}

.field { min-width: 0; }
.field-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  margin-bottom: 3px;
  color: var(--color-text-primary, #1a1a1a);
}
.help-text {
  display: block;
  font-size: 0.625rem;
  color: var(--color-text-tertiary, #999);
  font-weight: 400;
  margin-top: 1px;
  line-height: 1.3;
}

input[type="number"], input[type="text"], input[type="date"], select {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid var(--color-border-primary, rgba(0,0,0,0.15));
  border-radius: var(--border-radius-md, 6px);
  font-size: 0.75rem;
  font-family: inherit;
  background: var(--color-background-secondary, rgba(0,0,0,0.02));
  color: var(--color-text-primary, #1a1a1a);
  transition: border-color 0.15s;
}
input:focus, select:focus {
  outline: none;
  border-color: var(--color-ring-primary, #6366f1);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-ring-primary, #6366f1) 15%, transparent);
}

.field-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  gap: 6px;
  flex-shrink: 0;
}
.toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
.slider {
  width: 34px; height: 18px;
  background: var(--color-border-primary, rgba(0,0,0,0.2));
  border-radius: 9px;
  transition: background 0.2s;
  position: relative;
  flex-shrink: 0;
}
.slider::after {
  content: '';
  position: absolute;
  top: 2px; left: 2px;
  width: 14px; height: 14px;
  background: var(--color-background-primary, #fff);
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.toggle input:checked + .slider { background: var(--color-background-info, #6366f1); }
.toggle input:checked + .slider::after { transform: translateX(16px); }
.toggle-labels {
  font-size: 0.6875rem;
  color: var(--color-text-secondary, #666);
  min-width: 22px;
}
.toggle input:checked ~ .toggle-labels .lbl-no { display: none; }
.toggle input:not(:checked) ~ .toggle-labels .lbl-yes { display: none; }
.toggle input:checked ~ .toggle-labels .lbl-yes {
  color: var(--color-background-info, #6366f1);
  font-weight: 500;
}

.submit-row { text-align: center; margin-top: 10px; }
.btn-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background-info, #6366f1);
  color: #fff;
  border: none;
  border-radius: var(--border-radius-md, 6px);
  padding: 7px 24px;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-submit:hover { opacity: 0.88; }
.btn-submit:active { opacity: 0.76; }
.btn-submit:disabled {
  background: var(--color-text-tertiary, #999);
  cursor: not-allowed;
  opacity: 0.6;
}

.status {
  text-align: center;
  padding: 8px 12px;
  margin-top: 8px;
  border-radius: var(--border-radius-md, 6px);
  font-size: 0.6875rem;
}
.status-success {
  background: var(--color-background-success, rgba(34,197,94,0.08));
  color: var(--color-text-success, #16a34a);
  border: 1px solid var(--color-border-success, rgba(34,197,94,0.2));
}
.status-error {
  background: var(--color-background-danger, rgba(239,68,68,0.08));
  color: var(--color-text-danger, #dc2626);
  border: 1px solid var(--color-border-danger, rgba(239,68,68,0.2));
}

/* Compact density — applied by JS when content overflows viewport */
.compact .section { padding: 8px 10px; margin-bottom: 6px; }
.compact .fields-grid { gap: 4px 10px; }
.compact .field-label { font-size: 0.6875rem; margin-bottom: 2px; }
.compact input[type="number"], .compact input[type="text"],
.compact input[type="date"], .compact select { padding: 4px 6px; font-size: 0.6875rem; }
.compact .slider { width: 30px; height: 16px; border-radius: 8px; }
.compact .slider::after { width: 12px; height: 12px; }
.compact .toggle input:checked + .slider::after { transform: translateX(14px); }
.compact .submit-row { margin-top: 8px; }
.compact .btn-submit { padding: 5px 20px; }
</style>
</head>
<body>
<div id="loading">Loading form data&#x2026;</div>
<div id="form-container">
  <div id="sections"></div>
  <div class="submit-row">
    <button class="btn-submit" id="submit-btn" onclick="submitForm()">Submit</button>
  </div>
  <div id="status"></div>
</div>

<script type="module">
class App {
  constructor({ name, version }) {
    this._appInfo = { name, version };
    this._nextId = 1;
    this._pending = new Map();
    this._handlers = {};
    this._target = window.parent;
    window.addEventListener("message", (e) => {
      if (e.source !== this._target) return;
      const msg = e.data;
      if (!msg || typeof msg !== "object" || msg.jsonrpc !== "2.0") return;
      if ("id" in msg && this._pending.has(msg.id)) {
        const { resolve, reject } = this._pending.get(msg.id);
        this._pending.delete(msg.id);
        msg.error ? reject(new Error(msg.error.message || "RPC error")) : resolve(msg.result);
        return;
      }
      if (msg.method) this._handlers[msg.method]?.(msg.params);
    });
  }

  set ontoolresult(cb)         { this._handlers["ui/notifications/tool-result"] = cb; }
  set ontoolinput(cb)          { this._handlers["ui/notifications/tool-input"] = cb; }
  set ontoolcancelled(cb)      { this._handlers["ui/notifications/tool-cancelled"] = cb; }
  set onhostcontextchanged(cb) { this._handlers["ui/notifications/host-context-changed"] = cb; }

  async connect() {
    const result = await this._request("ui/initialize", {
      appInfo: this._appInfo, appCapabilities: {}, protocolVersion: "2026-01-26",
    });
    this._notify("ui/notifications/initialized", {});
    if (result?.hostContext) this._applyTheme(result.hostContext);
    return result;
  }

  async callServerTool(params)    { return this._request("tools/call", params); }
  async updateModelContext(params) { return this._request("ui/update-model-context", params); }
  async sendMessage(params)       { return this._request("ui/message", params); }
  sendSizeChanged(params)         { this._notify("ui/notifications/size-changed", params); }

  _applyTheme(ctx) {
    if (ctx.theme) {
      document.documentElement.setAttribute("data-theme", ctx.theme);
      document.documentElement.style.colorScheme = ctx.theme;
    }
    if (ctx.styles?.variables) {
      const root = document.documentElement;
      for (const [k, v] of Object.entries(ctx.styles.variables)) {
        if (v != null) root.style.setProperty(k, v);
      }
    }
  }

  _request(method, params) {
    return new Promise((resolve, reject) => {
      const id = this._nextId++;
      this._pending.set(id, { resolve, reject });
      this._target.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
    });
  }

  _notify(method, params) {
    this._target.postMessage({ jsonrpc: "2.0", method, params }, "*");
  }
}

const app = new App({ name: "concord-attestation", version: "1.0.0" });
app.onhostcontextchanged = (p) => { if (p?.hostContext) app._applyTheme(p.hostContext); };

let formData = null;

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

const CATEGORY_LABELS = {
  "condition": "Medical Conditions",
  "laboratory-blood-test": "Lab Values",
  "vital-sign": "Vital Signs",
  "demographics": "Demographics",
  "question": "Health Questions",
};
const INPUT_TYPE_GROUPS = {
  toggle: "Medical Conditions",
  number: "Clinical Values",
  select: "Demographics",
  date: "Other Information",
  text: "Other Information",
};

function sectionName(f) {
  return (f.category && CATEGORY_LABELS[f.category]) || INPUT_TYPE_GROUPS[f.input_type] || "Other Information";
}

function helpSpan(f) {
  return f.help_text ? `<span class="help-text">${esc(f.help_text)}</span>` : "";
}

function renderToggle(f) {
  return `<div class="field" data-var-id="${esc(f.variable_id)}"><div class="field-row">
    <div class="field-label"><span>${esc(f.label)}</span>${helpSpan(f)}</div>
    <label class="toggle"><input type="checkbox" />
      <span class="slider"></span>
      <span class="toggle-labels"><span class="lbl-no">No</span><span class="lbl-yes">Yes</span></span>
    </label>
  </div></div>`;
}

function renderSelect(f) {
  const opts = (f.options || []).map(o => `<option value="${esc(o.value)}">${esc(o.label || o.value)}</option>`).join("");
  return `<div class="field" data-var-id="${esc(f.variable_id)}">
    <label class="field-label">${esc(f.label)}${helpSpan(f)}</label>
    <select${f.required ? " required" : ""}><option value="">Select&#x2026;</option>${opts}</select>
  </div>`;
}

function renderNumber(f) {
  const v = f.validation || {};
  let a = "";
  if (v.min != null) a += ` min="${v.min}"`;
  if (v.max != null) a += ` max="${v.max}"`;
  if (v.step != null) a += ` step="${v.step}"`;
  return `<div class="field" data-var-id="${esc(f.variable_id)}">
    <label class="field-label">${esc(f.label)}${helpSpan(f)}</label>
    <input type="number"${a}${f.required ? " required" : ""} />
  </div>`;
}

function renderDate(f) {
  return `<div class="field" data-var-id="${esc(f.variable_id)}">
    <label class="field-label">${esc(f.label)}${helpSpan(f)}</label>
    <input type="date"${f.required ? " required" : ""} />
  </div>`;
}

function renderText(f) {
  return `<div class="field" data-var-id="${esc(f.variable_id)}">
    <label class="field-label">${esc(f.label)}${helpSpan(f)}</label>
    <input type="text"${f.required ? " required" : ""} />
  </div>`;
}

const RENDERERS = { toggle: renderToggle, select: renderSelect, number: renderNumber, date: renderDate, text: renderText };

function renderForm(data) {
  formData = data;
  const sections = {};
  for (const f of data.fields || []) {
    const sec = sectionName(f);
    (sections[sec] = sections[sec] || []).push(f);
  }

  let html = "";
  for (const [, flds] of Object.entries(sections)) {
    html += `<div class="section"><div class="fields-grid">`;
    for (const f of flds) html += (RENDERERS[f.input_type] || renderText)(f);
    html += `</div></div>`;
  }

  document.getElementById("sections").innerHTML = html;
  document.getElementById("loading").style.display = "none";
  document.getElementById("form-container").style.display = "block";

  fitToViewport();
}

function fitToViewport() {
  const vh = window.innerHeight;
  const contentH = document.body.scrollHeight;
  const container = document.getElementById("form-container");

  if (contentH <= vh) {
    app.sendSizeChanged({ height: contentH });
    return;
  }

  // Step 1: try multi-column grids (toggles can go 2-3 wide, inputs 2 wide)
  document.querySelectorAll(".fields-grid").forEach(grid => {
    const fields = grid.querySelectorAll(".field");
    const hasInputs = grid.querySelector("input[type=number], input[type=text], input[type=date], select");
    const count = fields.length;

    if (count >= 6 && !hasInputs) {
      grid.style.gridTemplateColumns = "repeat(3, 1fr)";
    } else if (count >= 3) {
      grid.style.gridTemplateColumns = "repeat(2, 1fr)";
    }
  });

  if (document.body.scrollHeight <= vh) {
    app.sendSizeChanged({ height: document.body.scrollHeight });
    return;
  }

  // Step 2: enable compact density
  document.body.classList.add("compact");

  if (document.body.scrollHeight <= vh) {
    app.sendSizeChanged({ height: document.body.scrollHeight });
    return;
  }

  // Step 3: widen input grids too
  document.querySelectorAll(".fields-grid").forEach(grid => {
    const count = grid.querySelectorAll(".field").length;
    if (count >= 2 && !grid.style.gridTemplateColumns.includes("3")) {
      grid.style.gridTemplateColumns = "repeat(2, 1fr)";
    }
  });

  // Request whatever height we ended up at
  app.sendSizeChanged({ height: document.body.scrollHeight });
}

app.ontoolresult = (result) => {
  try {
    const t = (result.content || []).find(c => c.type === "text");
    if (t) renderForm(JSON.parse(t.text));
  } catch (e) {
    document.getElementById("loading").textContent = "Error loading form: " + e.message;
  }
};

app.connect();

window.submitForm = async function() {
  if (!formData) return;
  const btn = document.getElementById("submit-btn");
  const statusEl = document.getElementById("status");
  btn.disabled = true;
  btn.textContent = "Submitting\u2026";
  statusEl.innerHTML = "";

  const attestations = [];
  document.querySelectorAll(".field").forEach(el => {
    const varId = el.dataset.varId;
    const input = el.querySelector("input, select");
    if (!input) return;
    let value;
    if (input.type === "checkbox") value = input.checked;
    else if (input.type === "number") { if (input.value === "") return; value = parseFloat(input.value); }
    else { if (input.value === "") return; value = input.value; }
    attestations.push({ variable_id: varId, value });
  });

  try {
    await app.callServerTool({
      name: "submit_attestation",
      arguments: { session_id: formData.session_id, cpg_id: formData.cpg_id, attestations },
    });
    statusEl.innerHTML = '<div class="status status-success">Submitted. Re-evaluating with your data.</div>';
    btn.textContent = "Submitted";
    await app.sendMessage({
      role: "user",
      content: [{ type: "text",
        text: `I've submitted my health data via the form (${attestations.length} fields). Please call evaluate_patient again with session_id="${formData.session_id}" and cpg_id="${formData.cpg_id}" to get my updated results.`,
      }],
    });
  } catch (e) {
    statusEl.innerHTML = `<div class="status status-error">Error: ${esc(e.message)}</div>`;
    btn.disabled = false;
    btn.textContent = "Submit";
  }
};
</script>
</body>
</html>"""


def get_attestation_app_html() -> str:
    return ATTESTATION_APP_HTML

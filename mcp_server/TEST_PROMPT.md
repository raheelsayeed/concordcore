# Test Prompt for mcp_server

Copy-paste the text below into Claude Desktop to test the MCP Apps attestation flow.

## HTTP mode setup (for MCP Apps UI)

MCP Apps iframes only render over HTTP transport (not stdio). Use this setup:

1. Start the server:
   ```bash
   source .venv/bin/activate
   python -m mcp_server --transport streamable-http
   ```
2. In another terminal, start a cloudflared tunnel:
   ```bash
   npx cloudflared tunnel --url http://localhost:3001
   ```
3. Copy the generated `https://xxx.trycloudflare.com` URL
4. In Claude: **Settings → Connectors → Add custom connector** → paste the URL + `/mcp`
   (e.g. `https://abc-xyz.trycloudflare.com/mcp`)
5. Test with the prompt below

---

## Claude Desktop config (stdio — no MCP Apps UI)

```json
{
  "mcpServers": {
    "concord-ui": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/Users/raheel/claude-projects/concordcore"
    }
  }
}
```

---

## Primary test prompt

```
I'm a 55-year-old woman. Evaluate me for statin use using Concord.

My lab values:
- Total cholesterol: 240 mg/dL
- LDL: 165 mg/dL
- HDL: 45 mg/dL
- Triglycerides: 180 mg/dL
- Blood pressure: 138/88 mmHg

I do NOT have the following information handy, so you will need to ask me:
ethnicity, diabetes status, hypertension status, smoking status, and current medications.

Use the interactive form to collect whatever is missing.
```

## What to verify

1. **Guidelines acknowledged** — LLM calls `acknowledge_guidelines` first
2. **Partial context created** — `create_health_context` with the 7 values above
3. **Missing data detected** — `evaluate_patient` returns `status: "missing_data"`
4. **Interactive form renders** — `collect_attestation` returns JSON field specs AND an iframe appears with:
   - A "Demographics" section with an Ethnicity dropdown
   - A "Medical Conditions" section with toggle switches (diabetes, hypertension, smoking, medications)
   - A blue "Submit" button
5. **Form submits via MCP Apps** — clicking Submit calls `submit_attestation` via `app.callServerTool()`
6. **Re-evaluation** — `evaluate_patient` runs again with complete data

## Architecture (MCP Apps standard)

The `collect_attestation` tool has `_meta.ui.resourceUri` pointing to `ui://concord/attestation-form`.
Claude Desktop pre-fetches the resource (static HTML with `text/html;profile=mcp-app` MIME type),
renders it in a sandboxed iframe, then pushes the tool result (JSON field specs) into the app
via `app.ontoolresult`. The HTML dynamically builds the form from this data. Submission goes
through `app.callServerTool()` back to the MCP server.

## Shorter prompt

```
Evaluate me for statin use. I'm 55, female, LDL 165, HDL 45, total cholesterol 240, triglycerides 180, BP 138/88. Ask me about anything else you need using the form.
```

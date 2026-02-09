"""Tests for mcp_server — MCP Apps architecture."""

import asyncio
import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAttestationAppHTML:
    @pytest.fixture(autouse=True)
    def _load_html(self):
        from mcp_server.html_renderer import get_attestation_app_html
        self.html = get_attestation_app_html()

    def test_valid_html_structure(self):
        assert "<!DOCTYPE html>" in self.html
        assert "<html" in self.html
        assert "</html>" in self.html

    def test_inline_mcp_apps_bridge(self):
        assert "class App" in self.html
        assert "ui/initialize" in self.html
        assert "postMessage" in self.html

    def test_app_connect(self):
        assert "app.connect()" in self.html

    def test_ontoolresult_handler(self):
        assert "app.ontoolresult" in self.html

    def test_call_server_tool(self):
        assert "app.callServerTool" in self.html

    def test_submit_attestation_target(self):
        assert "submit_attestation" in self.html

    def test_send_message(self):
        assert "app.sendMessage" in self.html

    def test_loading_state(self):
        assert "loading" in self.html.lower()

    def test_submit_button(self):
        assert "Submit" in self.html

    def test_form_container(self):
        assert "form-container" in self.html

    def test_field_renderers(self):
        assert "renderToggle" in self.html
        assert "renderSelect" in self.html
        assert "renderNumber" in self.html

    def test_xss_escape(self):
        assert "function esc" in self.html

    def test_min_height(self):
        assert "min-height" in self.html

    def test_section_grouping(self):
        assert "CATEGORY_LABELS" in self.html
        assert "Medical Conditions" in self.html

    def test_adaptive_grid_layout(self):
        assert "fields-grid" in self.html
        assert "fitToViewport" in self.html
        assert "gridTemplateColumns" in self.html

    def test_compact_density_class(self):
        assert ".compact" in self.html
        assert 'classList.add("compact")' in self.html

    def test_sends_size_changed(self):
        assert "sendSizeChanged" in self.html

    def test_theme_css_variables(self):
        for token in (
            "var(--color-background-primary",
            "var(--color-text-primary",
            "var(--color-background-secondary",
            "var(--color-border-primary",
            "var(--color-text-secondary",
            "var(--color-text-tertiary",
            "var(--color-background-info",
            "var(--color-text-success",
            "var(--color-text-danger",
        ):
            assert token in self.html, f"Missing theme token: {token}"

    def test_theme_font_variable(self):
        assert "var(--font-sans" in self.html

    def test_theme_border_radius(self):
        assert "var(--border-radius-lg" in self.html
        assert "var(--border-radius-md" in self.html

    def test_bridge_applies_host_theme(self):
        assert "_applyTheme" in self.html
        assert "hostContext" in self.html
        assert "data-theme" in self.html
        assert "colorScheme" in self.html

    def test_theme_change_handler(self):
        assert "onhostcontextchanged" in self.html


class TestServerArchitecture:
    def test_collect_attestation_has_meta_ui(self):
        from mcp_server.server import mcp
        tools = asyncio.run(mcp.list_tools())
        ca = next(t for t in tools if t.name == "collect_attestation")
        d = ca.model_dump(by_alias=True, exclude_none=True)
        assert "_meta" in d
        assert d["_meta"]["ui"]["resourceUri"].startswith("ui://")

    def test_resource_at_ui_uri(self):
        from mcp_server.server import mcp, ATTESTATION_UI_URI
        resources = asyncio.run(mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert ATTESTATION_UI_URI in uris

    def test_resource_mime_type(self):
        from mcp_server.server import mcp, MCP_APP_MIME
        resources = asyncio.run(mcp.list_resources())
        r = next(r for r in resources if "attestation" in str(r.uri))
        assert r.mimeType == MCP_APP_MIME

    def test_resource_serves_html(self):
        from mcp_server.server import mcp, ATTESTATION_UI_URI
        content = asyncio.run(mcp.read_resource(ATTESTATION_UI_URI))
        html = content if isinstance(content, str) else str(content)
        assert "<!DOCTYPE html>" in html
        assert "app.connect()" in html

    def test_seven_tools_registered(self):
        from mcp_server.server import mcp
        names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert len(names) == 7
        for name in ("acknowledge_guidelines", "list_cpgs", "get_cpg_info",
                      "create_health_context", "evaluate_patient",
                      "collect_attestation", "submit_attestation"):
            assert name in names


class TestTransportConfig:
    def test_host_and_port_writable(self):
        from mcp_server.server import mcp
        orig = (mcp.settings.host, mcp.settings.port)
        try:
            mcp.settings.host = "127.0.0.1"
            mcp.settings.port = 9999
            assert mcp.settings.host == "127.0.0.1"
            assert mcp.settings.port == 9999
        finally:
            mcp.settings.host, mcp.settings.port = orig


class TestToolBehavior:
    def test_list_cpgs(self):
        from mcp_server.server import list_cpgs
        result = json.loads(list_cpgs())
        assert "available_cpgs" in result
        assert isinstance(result["total_count"], int)

    def test_acknowledge_guidelines(self):
        from mcp_server.server import acknowledge_guidelines
        result = json.loads(acknowledge_guidelines("test-ack-2"))
        assert result["status"] == "acknowledged"
        assert "guidelines" in result

    def test_get_cpg_info(self):
        from mcp_server.server import list_cpgs, get_cpg_info
        cpgs = json.loads(list_cpgs())
        if cpgs["total_count"] > 0:
            result = json.loads(get_cpg_info(cpgs["available_cpgs"][0]["identifier"]))
            assert "identifier" in result
            assert "variables" in result

    def test_guidelines_interactive_form_language(self):
        from mcp_server.guidelines import MANDATORY_GUIDELINES
        assert "renders an INTERACTIVE FORM" in MANDATORY_GUIDELINES
        assert "DO NOT create your own UI" in MANDATORY_GUIDELINES
        assert "DO NOT list, describe, or enumerate the form fields" in MANDATORY_GUIDELINES
        assert "ask the user each question conversationally" not in MANDATORY_GUIDELINES

    def test_collect_attestation_docstring(self):
        from mcp_server.server import collect_attestation
        doc = collect_attestation.__doc__
        assert "interactive" in doc.lower()
        assert "DO NOT ask the user questions yourself" in doc
        assert "DO NOT list or describe the form fields" in doc

    def test_imports_from_own_package(self):
        import mcp_server.server as mod
        source = inspect.getsource(mod)
        assert "from .state import" in source
        assert "from .guidelines import" in source
        assert "from .form_builder import" in source
        assert "sys.path.insert" not in source

    def test_guidelines_required_before_health_context(self):
        from mcp_server.server import create_health_context
        result = json.loads(create_health_context(
            session_id="blocked-session-2",
            health_data=[{"variable_id": "Age", "value": 55}],
        ))
        assert result["error"] == "GUIDELINES_NOT_ACKNOWLEDGED"

    def test_collect_attestation_returns_str(self):
        from mcp_server.server import (
            acknowledge_guidelines, create_health_context,
            evaluate_patient, collect_attestation, list_cpgs,
        )
        sid = "ca-test-str"
        acknowledge_guidelines(sid)
        cpgs = json.loads(list_cpgs())
        if cpgs["total_count"] == 0:
            pytest.skip("No CPGs available")
        cpg_id = cpgs["available_cpgs"][0]["identifier"]
        create_health_context(session_id=sid, health_data=[{"variable_id": "Age", "value": 55}])
        evaluate_patient(session_id=sid, cpg_id=cpg_id)

        result = collect_attestation(session_id=sid, cpg_id=cpg_id)
        assert isinstance(result, str)
        data = json.loads(result)
        assert "fields" in data and len(data["fields"]) > 0
        assert "session_id" in data and "cpg_id" in data

    def test_collect_attestation_field_keys(self):
        from mcp_server.server import (
            acknowledge_guidelines, create_health_context,
            evaluate_patient, collect_attestation, list_cpgs,
        )
        sid = "ca-test-keys"
        acknowledge_guidelines(sid)
        cpgs = json.loads(list_cpgs())
        if cpgs["total_count"] == 0:
            pytest.skip("No CPGs available")
        cpg_id = cpgs["available_cpgs"][0]["identifier"]
        create_health_context(session_id=sid, health_data=[{"variable_id": "Age", "value": 55}])
        evaluate_patient(session_id=sid, cpg_id=cpg_id)
        data = json.loads(collect_attestation(session_id=sid, cpg_id=cpg_id))

        for field in data["fields"]:
            assert "variable_id" in field
            assert "label" in field
            assert "input_type" in field

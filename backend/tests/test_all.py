"""
Formatly backend test suite.
Run from the backend/ directory:
    python tests/test_all.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# ── path setup ──────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Load .env before importing app modules
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# ── colour helpers ───────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0
skipped = 0


def ok(name: str, detail: str = ""):
    global passed
    passed += 1
    print(f"  {GREEN}PASS{RESET} {name}" + (f"  {YELLOW}({detail}){RESET}" if detail else ""))


def fail(name: str, err: str):
    global failed
    failed += 1
    print(f"  {RED}FAIL{RESET} {name}")
    for line in err.splitlines():
        print(f"      {RED}{line}{RESET}")


def skip(name: str, reason: str):
    global skipped
    skipped += 1
    print(f"  {YELLOW}SKIP{RESET} {name}  {YELLOW}(skipped: {reason}){RESET}")


def section(title: str):
    bar = "-" * max(0, 50 - len(title))
    print(f"\n{BOLD}{CYAN}-- {title} {bar}{RESET}")


# ════════════════════════════════════════════════════════════════════════════
# 1. GROQ CONNECTIVITY
# ════════════════════════════════════════════════════════════════════════════
section("1. Groq API Connectivity")

api_key = os.environ.get("GROQ_API_KEY", "")
model   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

if not api_key or api_key == "your_groq_api_key_here":
    skip("Groq ping", "GROQ_API_KEY not set")
    skip("Groq JSON generation", "GROQ_API_KEY not set")
else:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
            max_tokens=10,
        )
        elapsed = time.time() - t0
        reply = (resp.choices[0].message.content or "").strip().lower()
        if "pong" in reply:
            ok("Groq ping", f"{elapsed:.2f}s · model={model}")
        else:
            ok("Groq ping", f"responded in {elapsed:.2f}s (reply: {reply[:40]})")
    except Exception as e:
        fail("Groq ping", str(e))

    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a document generator. Return ONLY valid JSON with keys: "
                        "title (string), outline (array of 3 strings), sections (array of "
                        "{heading: string, content: string} with 3 items)."
                    ),
                },
                {"role": "user", "content": "Generate a short report on renewable energy."},
            ],
            max_tokens=800,
        )
        elapsed = time.time() - t0
        raw = resp.choices[0].message.content or ""
        import re
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not m:
            fail("Groq JSON generation", f"No JSON found in response:\n{raw[:300]}")
        else:
            doc = json.loads(m.group(0))
            assert "title" in doc, "missing 'title'"
            assert isinstance(doc.get("sections"), list), "missing 'sections'"
            assert len(doc["sections"]) > 0, "empty sections"
            ok(
                "Groq JSON generation",
                f"{elapsed:.2f}s · title='{doc['title'][:50]}' · {len(doc['sections'])} sections",
            )
    except json.JSONDecodeError as e:
        fail("Groq JSON generation", f"JSON parse error: {e}\nRaw: {raw[:300]}")
    except Exception as e:
        fail("Groq JSON generation", str(e))


# ════════════════════════════════════════════════════════════════════════════
# 2. FORMATTING RULES EXTRACTION
# ════════════════════════════════════════════════════════════════════════════
section("2. Formatting Rules Extraction")

try:
    from app.services.rules import extract_rules

    cases = [
        (
            "Times New Roman\nHeading size 16 bold\n1.5 spacing\n1 inch margins",
            {"font_name": "Times New Roman", "heading_size_pt": 16, "line_spacing": 1.5, "margin_in": 1.0},
        ),
        (
            "Arial font\n2 inch margins\ndouble spacing",
            {"font_name": "Arial", "margin_in": 2.0},
        ),
        ("", {}),
    ]

    for text, expected in cases:
        rules = extract_rules(text)
        missing = [k for k, v in expected.items() if str(rules.get(k)) != str(v)]
        if missing:
            fail(
                f"extract_rules({text[:30]!r}…)",
                f"Missing or wrong keys: {missing}\nGot: {rules}",
            )
        else:
            ok(f"extract_rules({text[:30]!r}…)", f"→ {rules}")

except Exception as e:
    fail("extract_rules import/run", str(e))


# ════════════════════════════════════════════════════════════════════════════
# 3. STYLE PRESETS
# ════════════════════════════════════════════════════════════════════════════
section("3. Style Presets")

try:
    from app.services.presets import get_preset, _PRESETS

    for name in _PRESETS:
        p = get_preset(name)
        assert p.font_name, f"preset '{name}' missing font_name"
        assert p.heading1_pt > 0, f"preset '{name}' heading1_pt must be > 0"
        ok(f"preset '{name}'", f"font={p.font_name} h1={p.heading1_pt}pt margin={p.margin_in}in")

except Exception as e:
    fail("presets", str(e))


# ════════════════════════════════════════════════════════════════════════════
# 4. AI SERVICE (FALLBACK — no API key needed)
# ════════════════════════════════════════════════════════════════════════════
section("4. AI Service — Fallback Generator")

try:
    import importlib
    # Temporarily unset key to force fallback path
    saved_key = os.environ.pop("GROQ_API_KEY", None)

    from app.services import ai as ai_module
    result = ai_module.generate_structured_document(
        prompt="Write a report on climate change with sections on causes, effects, and solutions.",
        formatting_rules={"font_name": "Arial", "line_spacing": 1.5},
        style_preset="academic",
        tone="formal",
    )

    assert "title" in result and result["title"], "missing title"
    assert isinstance(result.get("outline"), list), "outline must be a list"
    assert isinstance(result.get("sections"), list) and len(result["sections"]) > 0, "no sections"
    for s in result["sections"]:
        assert "heading" in s and "content" in s, f"section missing fields: {s}"

    ok(
        "fallback generate_structured_document",
        f"title='{result['title'][:50]}' · {len(result['sections'])} sections",
    )

    if saved_key:
        os.environ["GROQ_API_KEY"] = saved_key

except Exception as e:
    if saved_key:
        os.environ["GROQ_API_KEY"] = saved_key
    fail("fallback generate_structured_document", str(e))


# ════════════════════════════════════════════════════════════════════════════
# 5. AI SERVICE (GROQ path)
# ════════════════════════════════════════════════════════════════════════════
section("5. AI Service — Groq Path")

if not api_key or api_key == "your_groq_api_key_here":
    skip("generate_structured_document via Groq", "GROQ_API_KEY not set")
else:
    try:
        from app.services import ai as ai_module
        t0 = time.time()
        result = ai_module.generate_structured_document(
            prompt="Create a business report on electric vehicles covering market trends, adoption rates, and future outlook.",
            formatting_rules={"font_name": "Calibri", "line_spacing": 1.5, "margin_in": 1.0},
            style_preset="business",
            tone="formal",
        )
        elapsed = time.time() - t0

        assert "title" in result and result["title"], "missing title"
        assert isinstance(result.get("sections"), list) and len(result["sections"]) > 0, "no sections"

        ok(
            "generate_structured_document via Groq",
            f"{elapsed:.2f}s · title='{result['title'][:50]}' · {len(result['sections'])} sections",
        )
    except Exception as e:
        fail("generate_structured_document via Groq", str(e))


# ════════════════════════════════════════════════════════════════════════════
# 6. DOCX GENERATION
# ════════════════════════════════════════════════════════════════════════════
section("6. DOCX Generation")

try:
    from app.schemas import DocumentSection
    from app.services.docx_engine import build_docx

    sections_data = [
        DocumentSection(id="s1", heading="Introduction", content="This report examines the impact of AI on productivity.\nStudies show a 40% increase in output."),
        DocumentSection(id="s2", heading="Key Findings", content="AI tools reduce repetitive tasks.\nTeams using AI report higher satisfaction."),
        DocumentSection(id="s3", heading="Conclusion", content="AI adoption is accelerating. Organizations that invest now will lead."),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test_report.docx"
        result_path = build_docx(
            out_path=out,
            title="AI Productivity Report",
            outline=["Introduction", "Key Findings", "Conclusion"],
            sections=sections_data,
            style_preset="business",
            extracted_rules={"font_name": "Calibri", "line_spacing": 1.5, "margin_in": 1.0, "heading_size_pt": 14},
            include_title_page=True,
            include_toc=True,
        )
        assert result_path.exists(), "DOCX file not created"
        size_kb = result_path.stat().st_size / 1024
        assert size_kb > 0.5, f"DOCX suspiciously small: {size_kb:.1f} KB"
        ok("build_docx — business preset", f"{size_kb:.1f} KB · {result_path.name}")

    # Academic preset
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "academic.docx"
        result_path = build_docx(
            out_path=out,
            title="Climate Change Research Paper",
            outline=["Abstract", "Introduction", "Methodology", "Results", "Discussion"],
            sections=[
                DocumentSection(id=f"s{i}", heading=h, content=f"Content for {h}. " * 10)
                for i, h in enumerate(["Abstract", "Introduction", "Methodology", "Results", "Discussion"])
            ],
            style_preset="academic",
            extracted_rules={"font_name": "Times New Roman", "line_spacing": 1.5, "heading_size_pt": 16},
            include_title_page=True,
            include_toc=True,
        )
        assert result_path.exists()
        size_kb = result_path.stat().st_size / 1024
        ok("build_docx — academic preset", f"{size_kb:.1f} KB")

    # Resume preset
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "resume.docx"
        result_path = build_docx(
            out_path=out,
            title="John Doe — Software Engineer",
            outline=["Profile", "Experience", "Education", "Skills"],
            sections=[
                DocumentSection(id=f"s{i}", heading=h, content=f"Details for {h}.")
                for i, h in enumerate(["Profile", "Experience", "Education", "Skills"])
            ],
            style_preset="resume",
            extracted_rules={},
            include_title_page=False,
            include_toc=False,
        )
        assert result_path.exists()
        size_kb = result_path.stat().st_size / 1024
        ok("build_docx — resume preset (no title page, no TOC)", f"{size_kb:.1f} KB")

except Exception as e:
    import traceback
    fail("DOCX generation", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# 7. PDF GENERATION
# ════════════════════════════════════════════════════════════════════════════
section("7. PDF Generation")

try:
    from app.schemas import DocumentSection
    from app.services.pdf_engine import build_pdf

    presets_to_test = [
        ("business", {"font_name": "Calibri", "line_spacing": 1.5, "margin_in": 1.0}),
        ("academic",  {"font_name": "Times New Roman", "line_spacing": 2.0, "margin_in": 1.25}),
        ("resume",    {}),
    ]

    for preset_name, rules in presets_to_test:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / f"{preset_name}.pdf"
            result_path = build_pdf(
                out_path=out,
                title=f"Test {preset_name.title()} Document",
                outline=["Section A", "Section B", "Conclusion"],
                sections=[
                    DocumentSection(id=f"s{i}", heading=h, content=f"Content for {h}. " * 15)
                    for i, h in enumerate(["Section A", "Section B", "Conclusion"])
                ],
                style_preset=preset_name,
                extracted_rules=rules,
                include_title_page=True,
                include_toc=True,
            )
            assert result_path.exists(), "PDF not created"
            size_kb = result_path.stat().st_size / 1024
            assert size_kb > 1, f"PDF too small: {size_kb:.1f} KB"
            ok(f"build_pdf — {preset_name} preset", f"{size_kb:.1f} KB")

except Exception as e:
    import traceback
    fail("PDF generation", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# 8. CHART GENERATION
# ════════════════════════════════════════════════════════════════════════════
section("8. Chart Generation")

try:
    from app.schemas import ChartSpec
    from app.services.charts import render_chart_png

    chart_cases = [
        ("bar",  ChartSpec(kind="bar",  title="Revenue by Quarter", labels=["Q1","Q2","Q3","Q4"], values=[120,145,190,210])),
        ("line", ChartSpec(kind="line", title="User Growth",        labels=["Jan","Feb","Mar","Apr"], values=[500,750,1100,1600])),
        ("pie",  ChartSpec(kind="pie",  title="Market Share",       labels=["A","B","C","D"], values=[35,25,25,15])),
    ]

    for kind, spec in chart_cases:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / f"{kind}_chart.png"
            render_chart_png(spec, out)
            assert out.exists(), f"{kind} chart PNG not created"
            size_kb = out.stat().st_size / 1024
            assert size_kb > 0.1, f"{kind} chart too small: {size_kb:.1f} KB"
            ok(f"render_chart_png — {kind}", f"{size_kb:.1f} KB")

except Exception as e:
    import traceback
    fail("chart generation", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# 9. FULL PIPELINE (end-to-end via doc_pipeline + export_engine)
# ════════════════════════════════════════════════════════════════════════════
section("9. Full Pipeline — End-to-End")

try:
    import tempfile as _tmp
    from unittest.mock import patch

    # Point data dir at a temp folder for this test
    tmp_data = Path(tempfile.mkdtemp())
    (tmp_data / "documents").mkdir()
    (tmp_data / "templates").mkdir()
    (tmp_data / "charts").mkdir()

    from app.services import storage as storage_module

    class _TmpPaths:
        documents = tmp_data / "documents"
        templates = tmp_data / "templates"
        charts    = tmp_data / "charts"

    with patch.object(storage_module, "get_paths", return_value=_TmpPaths()):
        from app.schemas import GenerateRequest, ChartSpec
        from app.services.doc_pipeline import create_document
        from app.services.export_engine import export_docx, export_pdf

        req = GenerateRequest(
            prompt="Write a research report on renewable energy sources including solar, wind, and hydro.",
            formatting_instructions="Times New Roman\n1.5 spacing\n1 inch margins\nHeading size 14 bold",
            style_preset="research",
            tone="formal",
            include_title_page=True,
            include_toc=True,
            include_charts=True,
            charts=[ChartSpec(kind="bar", title="Energy Output", labels=["Solar","Wind","Hydro"], values=[45,35,20])],
        )

        t0 = time.time()
        doc = create_document(req)
        elapsed = time.time() - t0

        assert doc.get("document_id"), "no document_id"
        assert doc.get("title"), "no title"
        assert doc.get("sections"), "no sections"
        assert doc.get("pipeline"), "no pipeline"

        doc_id = doc["document_id"]
        ok(
            "create_document",
            f"{elapsed:.2f}s · id={doc_id} · '{doc['title'][:40]}' · {len(doc['sections'])} sections",
        )

        # Export DOCX
        with patch.object(storage_module, "get_paths", return_value=_TmpPaths()):
            docx_path = export_docx(doc_id)
            assert docx_path.exists()
            size_kb = docx_path.stat().st_size / 1024
            ok("export_docx", f"{size_kb:.1f} KB → {docx_path.name}")

        # Export PDF
        with patch.object(storage_module, "get_paths", return_value=_TmpPaths()):
            pdf_path = export_pdf(doc_id)
            assert pdf_path.exists()
            size_kb = pdf_path.stat().st_size / 1024
            ok("export_pdf", f"{size_kb:.1f} KB → {pdf_path.name}")

except Exception as e:
    import traceback
    fail("full pipeline", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# 10. MULTI-PROVIDER ROUTER
# ════════════════════════════════════════════════════════════════════════════
section("10. Multi-Provider Router")

try:
    from app.services.router import (
        ProviderRouter,
        get_router,
        AllProvidersFailed,
        RateLimitExceeded,
        ProviderTimeout,
        GROQ, GEMINI, OPENROUTER, HUGGINGFACE,
        DEFAULT_ORDER,
    )

    _PLACEHOLDER = ("your_", "placeholder", "")

    def _is_real_key(key: str) -> bool:
        """Return True only if the key looks like a genuine credential."""
        if not key:
            return False
        return not any(key.startswith(p) for p in _PLACEHOLDER)

    # ── 10a. status() snapshot ────────────────────────────────────────────────
    router = get_router()
    router.reset_cooldowns()
    status = router.status()

    assert set(status.keys()) == {GROQ, GEMINI, OPENROUTER, HUGGINGFACE}, \
        f"status keys wrong: {set(status.keys())}"

    real_keys   = [p for p in DEFAULT_ORDER if _is_real_key(router._key(p))]
    placeholder = [p for p in DEFAULT_ORDER if router._key(p) and not _is_real_key(router._key(p))]
    no_key      = [p for p in DEFAULT_ORDER if not router._key(p)]

    ok(
        "router.status() — all 4 providers present",
        f"live={real_keys} | placeholder={placeholder} | no_key={no_key}",
    )

    # ── 10b. basic chat via the best available provider ───────────────────────
    if not real_keys:
        skip("router.chat() — live call", "no real provider keys set")
    else:
        t0 = time.time()
        text, provider_used, elapsed = router.chat(
            [{"role": "user", "content": "Reply with exactly: pong"}],
            max_tokens=10,
        )
        ok(
            f"router.chat() — used {provider_used}",
            f"{elapsed:.2f}s · reply='{text.strip()[:30]}'",
        )

    # ── 10c. fallback: mock Groq to raise RateLimitExceeded ───────────────────
    from unittest.mock import patch

    fresh = ProviderRouter()
    fresh.reset_cooldowns()

    def _mock_groq_rate_limit(messages, max_tokens):
        raise RateLimitExceeded(GROQ)

    with patch.object(fresh, "_call_groq", side_effect=_mock_groq_rate_limit):
        secondary_live = [p for p in DEFAULT_ORDER if p != GROQ and _is_real_key(fresh._key(p))]

        if not secondary_live:
            # No real secondary keys — router should raise AllProvidersFailed
            try:
                fresh.chat([{"role": "user", "content": "pong"}], max_tokens=5)
                fail("fallback: expected AllProvidersFailed but got result", "")
            except AllProvidersFailed:
                ok(
                    "fallback: Groq rate-limited -> AllProvidersFailed (no real secondary keys)",
                    "correct behaviour",
                )
        else:
            t0 = time.time()
            text, provider_used, elapsed = fresh.chat(
                [{"role": "user", "content": "Reply with exactly: pong"}],
                max_tokens=10,
            )
            assert provider_used != GROQ, f"should have skipped Groq, got {provider_used}"
            ok(
                f"fallback: Groq rate-limited -> fell back to {provider_used}",
                f"{elapsed:.2f}s",
            )

    # Verify Groq entered cooldown regardless of outcome above
    in_cd, remaining = fresh._in_cooldown(GROQ)
    assert in_cd, "Groq should be in cooldown after RateLimitExceeded"
    ok("cooldown set after RateLimitExceeded", f"Groq cooldown {remaining}s remaining")

    # ── 10d. fallback: mock Groq to timeout ───────────────────────────────────
    fresh2 = ProviderRouter()

    def _mock_groq_timeout(messages, max_tokens):
        raise ProviderTimeout(GROQ)

    with patch.object(fresh2, "_call_groq", side_effect=_mock_groq_timeout):
        secondary_live = [p for p in DEFAULT_ORDER if p != GROQ and _is_real_key(fresh2._key(p))]

        if not secondary_live:
            try:
                fresh2.chat([{"role": "user", "content": "pong"}], max_tokens=5)
                fail("fallback timeout: expected AllProvidersFailed", "")
            except AllProvidersFailed:
                ok(
                    "fallback: Groq timeout -> AllProvidersFailed (no real secondary keys)",
                    "correct behaviour",
                )
        else:
            _, provider_used, _ = fresh2.chat(
                [{"role": "user", "content": "Reply with exactly: pong"}],
                max_tokens=10,
            )
            assert provider_used != GROQ
            ok(f"fallback: Groq timeout -> fell back to {provider_used}")

    in_cd, remaining = fresh2._in_cooldown(GROQ)
    assert in_cd, "Groq should be in cooldown after ProviderTimeout"
    ok("cooldown set after ProviderTimeout", f"Groq cooldown {remaining}s remaining")

    # ── 10e. AllProvidersFailed when ALL providers have no keys ───────────────
    keyless = ProviderRouter()
    with patch.object(keyless, "_key", return_value=""):
        try:
            keyless.chat([{"role": "user", "content": "test"}], max_tokens=5)
            fail("AllProvidersFailed not raised", "expected exception but got result")
        except AllProvidersFailed as e:
            ok("AllProvidersFailed raised when no keys configured", str(e)[:60])

    # ── 10f. reset_cooldowns() clears state ───────────────────────────────────
    r = ProviderRouter()
    r._cool(GROQ,   60)
    r._cool(GEMINI, 60)
    r.reset_cooldowns()
    assert not r._in_cooldown(GROQ)[0],   "Groq should not be in cooldown after reset"
    assert not r._in_cooldown(GEMINI)[0], "Gemini should not be in cooldown after reset"
    ok("reset_cooldowns() clears all cooldowns")

except Exception as e:
    import traceback
    fail("router tests", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# 11. PROVIDER CONNECTIVITY (individual key checks)
# ════════════════════════════════════════════════════════════════════════════
section("11. Individual Provider Connectivity")

try:
    from app.services.router import ProviderRouter, GROQ, GEMINI, OPENROUTER, HUGGINGFACE

    probe_router = ProviderRouter()
    probe_msg = [{"role": "user", "content": "Reply with exactly: pong"}]

    def _is_real(k: str) -> bool:
        return bool(k) and not k.startswith("your_")

    for provider in [GROQ, GEMINI, OPENROUTER, HUGGINGFACE]:
        key = probe_router._key(provider)
        if not _is_real(key):
            skip(f"{provider} ping", "placeholder or missing key in .env")
            continue
        try:
            caller = {
                GROQ:        probe_router._call_groq,
                GEMINI:      probe_router._call_gemini,
                OPENROUTER:  probe_router._call_openrouter,
                HUGGINGFACE: probe_router._call_huggingface,
            }[provider]
            t0 = time.time()
            reply = caller(probe_msg, max_tokens=15)
            elapsed = time.time() - t0
            ok(f"{provider} ping", f"{elapsed:.2f}s · '{reply.strip()[:40]}'")
        except Exception as exc:
            fail(f"{provider} ping", str(exc)[:200])

except Exception as e:
    import traceback
    fail("individual provider connectivity", traceback.format_exc())


# ════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════════
total = passed + failed + skipped
print(f"\n{BOLD}{'=' * 55}{RESET}")
print(
    f"{BOLD}Results: "
    f"{GREEN}{passed} passed{RESET}  "
    f"{RED}{failed} failed{RESET}  "
    f"{YELLOW}{skipped} skipped{RESET}  "
    f"({total} total)"
)
print(f"{BOLD}{'=' * 55}{RESET}\n")

if failed:
    sys.exit(1)

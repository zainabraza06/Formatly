# Formatly

Formatly is an AI document workspace. You paste notes (and any extra material), it **writes a fully styled paper or report**, then you **open that document in Document OS** and keep editing it by hand or in plain English. Every AI edit is a validated JSON action, every action is versioned, and you can export Word or PDF.

This README is the full project guide: what it is, how the pieces fit, how to run it, how each screen works, the HTTP and WebSocket APIs, the action language, data on disk, tests, and troubleshooting.

**Local URLs**

- UI: http://localhost:5173
- API (OpenAPI): http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- ReDoc: http://127.0.0.1:8000/redoc

---

## Table of contents

1. [What you can do](#what-you-can-do)
2. [How the product is split](#how-the-product-is-split)
3. [End-to-end flows](#end-to-end-flows)
4. [Tech stack](#tech-stack)
5. [Repository map](#repository-map)
6. [Prerequisites](#prerequisites)
7. [Install and run](#install-and-run)
8. [Environment variables](#environment-variables)
9. [Accounts and auth](#accounts-and-auth)
10. [Compose (paper generator)](#compose-paper-generator)
11. [Document OS](#document-os)
12. [Frontend screens](#frontend-screens)
13. [HTTP API](#http-api)
14. [WebSocket protocol](#websocket-protocol)
15. [Action language](#action-language)
16. [PaperSpec (generation contract)](#paperspec-generation-contract)
17. [Stylesheets](#stylesheets)
18. [LLM router](#llm-router)
19. [Storage on disk](#storage-on-disk)
20. [LibreOffice (exact layout)](#libreoffice-exact-layout)
21. [Tests](#tests)
22. [Scripts](#scripts)
23. [Troubleshooting](#troubleshooting)
24. [Security notes](#security-notes)
25. [License](#license)

---

## What you can do

**Write a document from notes**

- Paste source material: notes, a brief, excerpts, data tables as text.
- Attach extra labelled blobs (survey answers, a transcript, source code, citations).
- Choose a stylesheet: IEEE 2-column, IEEE 1-column, formal assignment, or a custom sheet you saved.
- Choose a document kind as free text (`paper`, `report`, `assignment`, `memo`, `literature review`, `thesis chapter`, ...).
- Choose depth: `brief` (short sections) or `standard` (fuller sections).
- Optionally refine a vague extra instruction ("make it look like a lab report") into something the writer can follow.
- Generate a `PaperSpec` (structured JSON). Stop cancels the server-side run (HTTP 499), not a 500.
- Preview as HTML, or as a PDF of the real `.docx` when LibreOffice is installed.
- Download DOCX, or open the spec in the editor **without** flattening it through Word first.

**Edit the document as a graph (Document OS)**

- Import a `.docx` or a composed spec.
- See pages measured in the editor (not only Word's saved break markers).
- Type commands: "center all figures", "make headings bold 14pt", "rewrite the abstract in plainer English".
- Watch selection and formatting animate as events stream over WebSocket.
- Undo, redo, rewind to a version, restore a version as a new commit, compare two versions.
- Switch **Edit** (HTML layout you can change) vs **Exact** (LibreOffice PDF of the *current* graph, including edits).
- Export.

**Account**

- Sign up / log in. Token in `localStorage` (`docos.token`), sent as `Authorization: Bearer`.
- Change display name. Change password (must prove the current password).
- Papers and DocOS documents are **owner-scoped**. Other users cannot list or open them.

Without `MISTRAL_API_KEY`, generation fails and the editor falls back to **keyword heuristics** for common commands so a local demo of the UI still works.

---

## How the product is split

There are two products in one repo. They share auth, the Mistral router, and the data directory.

```
  Compose                         Document OS
  -------                         -----------
  notes + style + depth           .docx or PaperSpec
           |                              |
           v                              v
      PaperSpec JSON               DocumentGraph
           |                              |
           +---- import-spec -------------+
           |                              |
           v                              v
      render .docx                 NL -> Action[] -> mutate graph
           |                              |
           v                              v
      download / PDF               versions + live events + export
```

**Compose** lives in `backend/app/paper/`. The model emits *semantic* blocks (heading, paragraph, table, equation, listing, figure). A stylesheet resolver then stamps explicit fonts, sizes, numbering, and captions. The renderer is a deterministic executor: it does not invent layout.

**Document OS** lives in `backend/app/docos/`. Four engines:

| Engine | Package | Job |
|--------|---------|-----|
| Document | `docos/graph`, `docos/parser` | Typed tree of nodes; DOCX parse; optional LibreOffice pagination |
| Command | `docos/command` | Natural language -> control op or validated `ActionBatch`; rewrite is a second LLM pass over real text |
| Execution | `docos/execution` | Sole mutator. Clone, apply, stream events. On failure, discard the clone |
| Version | `docos/versioning` | SQLite history. Snapshot every 10 versions; replay actions between checkpoints |

**Rule:** the model never writes the document. It only emits JSON. Invalid or dangerous batches are rejected; the graph is untouched.

Deeper notes: `backend/app/docos/ARCHITECTURE.md`.

An older section-based generator still exists on `app/main.py` (`POST /generate`, drafts, charts, excel export). The product UI uses **Compose + DocOS**. `/app/new` redirects to compose; `/app/assistant` redirects to the editor.

---

## End-to-end flows

### A. Compose then edit

1. Sign up at `/login`.
2. `/app/compose`: paste notes, pick IEEE or Assignment, depth Standard.
3. Optional: Refine instructions. Review `improved`, `changes`, `questions`. Send feedback and refine again if needed.
4. Generate. The UI polls nothing; one long `POST /paper/generate` (abortable).
5. HTML preview, or exact PDF via `POST /paper/preview`.
6. "Open in editor" -> `POST /docos/import-spec` with the spec. Listings, equations, and figures stay typed nodes instead of becoming loose Word text.
7. In `/app/editor?doc=<id>`, prompt the AI. Events animate. Versions appear in the timeline.
8. Download from Generated files: `GET /paper/{id}/export/docx` or `/export/pdf`.

### B. Import an existing Word file

1. `/app/editor` or `/app/documents`: upload `.docx`.
2. Parser builds a graph. If LibreOffice is present, pages are assigned from a PDF conversion; otherwise saved breaks + editor measurement.
3. Same command / version / exact-view path as above.

### C. Command that rewrites prose

1. User: "replace the LaTeX with readable mathematics".
2. Planner sees node *counts and headings*, not the full prose (prompt stays small). It emits one `rewrite` action with a target/scope.
3. `docos/command/rewriter.py` walks text nodes (body, heading, caption, reference, footnote -- not table cells) in ~5000-character passes, sends each pass to Mistral with the actual text, applies returned `{id, text}` edits.
4. Execution commits a version.

That split exists because a single prompt holding a whole paper truncates, and the middle of the document would go unedited.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| UI | React 19, TypeScript, Vite 8, Tailwind 3, Framer Motion, React Router 7 |
| API | FastAPI, Uvicorn, Pydantic v2, python-multipart |
| Word | python-docx |
| PDF (simple) | fpdf2 |
| Exact PDF | LibreOffice (`soffice`) converting DOCX -> PDF |
| Charts | matplotlib, Pillow |
| Listings | Pygments; optional "codeshot" window images |
| Spreadsheet (legacy export) | openpyxl |
| HTTP client (LLM) | httpx |
| Auth | PBKDF2-SHA256 (120000 iterations), HS256 JWT-shaped tokens, 7-day TTL, stdlib only |
| Live edits | WebSockets |
| Data | Files + SQLite under `backend/.data/` (gitignored) |
| Tests | pytest |

Python 3.11+ (3.12 recommended). Node 20+.

---

## Repository map

```
Formatter/
  README.md
  .gitignore
  backend/
    requirements.txt
    .env.example
    app/
      main.py                 FastAPI app, CORS, health, legacy generate/export
      schemas.py              Legacy GenerateRequest / ChartSpec
      services/
        router.py             Mistral client, cooldowns, timeouts
        ai.py                 Legacy rewrite helper
        storage.py            Data dir, ids, JSON helpers
        charts.py             PNG charts
        chart_analyzer.py
        doc_pipeline.py       Legacy generator
        docx_engine.py / pdf_engine.py / excel_engine.py / export_engine.py
      paper/
        api.py                /paper routes
        generator.py          Single-pass generate
        agentic.py            Plan + per-section write (long docs)
        schema.py             PaperSpec blocks
        stylesheet.py         Apply StyleSheet onto a spec
        renderer.py           Spec -> .docx
        to_graph.py           Spec -> DocumentGraph
        prompt.py             System/user prompts, depths
        refine.py             Instruction refiner
        equations.py figures.py codeshot.py references.py jsonx.py
        styles/               ieee, ieee_1col, assignment, custom store
        cli.py                Optional CLI entry
      docos/
        api.py                /docos REST + WS
        service.py            Wires four engines
        export.py             Graph -> .docx bytes
        ARCHITECTURE.md
        auth/                 /auth, users, tokens
        graph/                Node, DocumentGraph, Style
        parser/               DOCX parse, paginator (LibreOffice)
        actions/              Action schema + validator
        command/              NL parser, prompts, rewriter
        execution/            Mutator + events
        versioning/           SQLite store, snapshot/replay, diff
        events/               Connection hub
    tests/                    pytest modules (see Tests)
  frontend/
    package.json
    .env.example
    src/
      main.tsx App.tsx
      context/AuthContext.tsx
      layout/DashboardLayout.tsx
      pages/                  Landing, Login, dashboard pages
      components/docos/       GraphCanvas, NodeView, AIPanel, ExactView, VersionTimeline
      components/paper/       DocumentPreview, InstructionRefiner, GenerationStatus
      hooks/useDocOS.ts       WS, event pacing, local graph patches
      lib/                    api.ts paperApi.ts docosApi.ts auth.ts theme.ts
      types/
```

---

## Prerequisites

- Python 3.11+ and pip
- Node.js 20+ and npm
- Mistral API key for generation and LLM commands: https://console.mistral.ai/api-keys
- LibreOffice (optional) for exact preview, exact editor view, PDF export of papers, and true page breaks

Windows: PowerShell examples below. Linux/macOS: use `python3`, `source .venv/bin/activate`, `cp` instead of `Copy-Item`.

---

## Install and run

### Backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Put your key in `backend/.env`:

```
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest
```

Start from the `backend/` directory (so `app` imports):

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`--reload` watches Python files. CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`.

### Frontend

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Vite: http://localhost:5173. The client calls `import.meta.env.VITE_API_URL` or defaults to `http://127.0.0.1:8000`.

If the API is on another port:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:8010"
npm run dev
```

Or set `VITE_API_URL` in `frontend/.env` (Vite reads it at **dev-server start**; restart after changing).

### Production-ish frontend build

```powershell
Set-Location frontend
npm run build
npm run preview
```

Point `VITE_API_URL` at the real API **before** `npm run build` (it is baked in).

---

## Environment variables

Copy from `backend/.env.example` and `frontend/.env.example`. Real `.env` files are gitignored.

### Backend

| Name | Default | Meaning |
|------|---------|---------|
| `MISTRAL_API_KEY` | empty | Required for LLM. Empty: generation errors; editor uses heuristics |
| `MISTRAL_MODEL` | `mistral-large-latest` | Chat model id |
| `LLM_TIMEOUT` | unset | Seconds. Unset: `30 + max_tokens / 40` (measured ~60 tok/s; floor is conservative) |
| `DOCOS_SECRET` | generated file | Signs auth tokens. Unset: random key written to `<data>/secret.key` so restarts keep tokens |
| `DOCPILOT_DATA_DIR` | `backend/.data` | Documents, charts, SQLite, users, secret |
| `LIBREOFFICE_PATH` | auto-detect | Full path to `soffice` / `soffice.exe` |

`.env.example` also mentions `FORMATLY_DATA_DIR`; the code reads **`DOCPILOT_DATA_DIR`**.

### Frontend

| Name | Default | Meaning |
|------|---------|---------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | API origin (no trailing slash) |

---

## Accounts and auth

Routes under `/auth`. Passwords min length 6. Email is identity (cannot change). Display name can.

| Method | Path | Auth | Body / notes |
|--------|------|------|----------------|
| POST | `/auth/signup` | no | `{ "email", "password", "name"? }` -> `{ token, user }`. 409 if email exists. 422 invalid email |
| POST | `/auth/login` | no | `{ "email", "password" }` -> `{ token, user }`. 401 bad credentials |
| GET | `/auth/me` | Bearer | Public user: `id`, `email`, `name`, `created_at` |
| PATCH | `/auth/me` | Bearer | `{ "name" }` (1-120 chars) |
| POST | `/auth/password` | Bearer | `{ "current_password", "new_password" }`. 400 if current wrong or new equals old |

Tokens: HS256, claim `sub` = user id, TTL 7 days. WebSockets cannot send `Authorization` from the browser; pass `?token=`.

Frontend: `frontend/src/lib/auth.ts`, `AuthContext`, `RequireAuth`. Unauthenticated `/app/*` redirects to login.

---

## Compose (paper generator)

### What the model is asked to produce

A `PaperSpec`: `meta` + `blocks` + `references` + `visualization_plan`. Blocks are semantic. After generation, `resolve()` fills fonts, indents, heading numbers, caption prefixes from the stylesheet. `resolved: true` means formatting is explicit.

Unknown style names (e.g. "Chicago") are **not** silently mapped to IEEE for the writer's *conventions*: the name is passed in the prompt; a default sheet still supplies typography so a file can be rendered.

### Single pass vs multi-pass

- `brief` / `standard`: one chat call (up to 8000 tokens). If JSON is truncated, a retry asks for complete JSON only.
- Depths that cannot fit (`detailed` in the generator, even if the UI currently offers brief/standard): **agentic** path in `paper/agentic.py`:
  1. Plan call (~2000 tokens): meta, outline, references, visualisation plan.
  2. One write call per section (~3000 tokens).
  3. Assemble one spec. A failed section degrades that section, not the whole document.

### Request fields (`POST /paper/generate`, `/paper/compose`, refine)

```json
{
  "raw_text": "required source notes...",
  "style": "ieee",
  "doc_kind": "paper",
  "depth": "standard",
  "attachments": [{ "label": "Appendix data", "content": "..." }],
  "reference_example": "optional excerpt of a paper to imitate",
  "instructions": "optional extra constraints",
  "title_hint": "optional",
  "authors": [{ "name": "A. Author", "affiliation": "Univ", "email": "" }]
}
```

`depth`: `brief` | `standard` (UI). Generator also understands `detailed` for multi-pass.

### Refine

`POST /paper/instructions/refine` does **not** generate a paper and does not save. Returns `{ provider, improved, changes[], questions[] }`. Pass `previous` + `feedback` on retry so it corrects rather than rolling the dice.

### Cancel

The API runs generation in a worker thread and polls whether the HTTP client is still connected (~0.5s). If you abort in the UI, work raises `GenerationCancelled` and the API returns **499**.

### Built-in styles (ids)

| id | Name | Columns | Headings | Tables |
|----|------|---------|----------|--------|
| `ieee` | IEEE Conference (2-column) | 2 | roman_alpha | horizontal |
| `ieee_1col` | IEEE Conference (1-column) | 1 | roman_alpha | horizontal |
| `assignment` | Formal Assignment | 1 | decimal | grid |

Aliases (examples): `ieee conference`, `homework`, `lab report`, `report` -> assignment, empty/`default` -> ieee.

Custom styles: `POST /paper/styles` with a full `StyleSheet` JSON. Lookup order: built-in **id** wins; then your custom by id or name; then built-in **alias**; then default ieee.

---

## Document OS

### Graph model

Root is always `type: document`. Children are typed nodes:

`paragraph`, `heading`, `subheading`, `body`, `image`, `figure`, `caption`, `table`, `table_row`, `table_cell`, `horizontal_rule`, `page_break`, `header`, `footer`, `reference`, `footnote`.

Each node: `id` (`n_` + hex), `content`, `style` (font_family, font_size, bold, italic, underline, color, highlight, alignment), `metadata`, `children`.

High-level action **targets** map to types, e.g. `figure` -> figure + image, `body` -> body + paragraph.

### Command pipeline

1. **Control rules** (no LLM): exact `undo` / `redo`; `rewind to version N`; `restore to version N`; `compare versions A and B`.
2. Else **LLM** with a small graph summary (counts, headings). Must return strict JSON `ActionBatch`. Validated.
3. Else **heuristics**: highlight, delete, justify, center/centre, font size, bold, select, by keywords and a guessed target.
4. If the batch contains `rewrite`, the rewriter runs on scoped text nodes in passes (`_PASS_CHARS = 5000`, `_MAX_TOKENS = 4000`).
5. Execution on a **clone**. Events: `batch_started`, `selection_*`, `format_*`, `delete_*`, `insert_*`, `move_*`, `replace_*`, `batch_finished` or `batch_failed`.
6. Version commit (parent = current). Redo pointer cleared. Every 10th seq stores a full snapshot.

### Version ops

- **undo**: current pointer -> parent; previous current saved as redo.
- **redo**: current -> redo pointer.
- **rewind**: pointer to any historical version (non-destructive).
- **restore**: new version whose graph equals an old one (history kept).
- **branch**: commit with `parent_id` set to an old version (engine supports it; UI is linear timeline today).
- **diff**: node-level `GraphDiff` between two seqs, carrying the text as well as the counts.

A `GraphDiff` answers "what changed with what". `added` and `removed` entries carry
the node's `content` (with `truncated: true` when it ran past 2000 characters).
A `changed` entry carries `content.before`, `content.after` and `content.segments` —
word-level runs tagged `equal` / `insert` / `delete` from `difflib`, so the timeline
can strike out the words that left and highlight the ones that arrived — plus
`style.fields`, one `{field, before, after}` per property that moved. A `summary`
block holds the counts (`added`, `removed`, `changed`, `text_changed`,
`style_changed`, `words_added`, `words_removed`).

Materialise: walk to nearest checkpoint snapshot, replay action batches forward.

### Editor UI behaviour

`useDocOS` opens `ws://.../docos/ws/{id}?token=`. Incoming events are **paced** (~220ms per item, ~70ms per step) so the canvas can highlight nodes one by one. Manual edits (style patch, delete, text) go through graph helpers on the client; commands go to the server.

Views: **Edit** (`GraphCanvas` + measured pages) and **Exact** (`ExactView` fetches `/docos/{id}/exact.pdf`).

---

## Frontend screens

| Route | File | What it is |
|-------|------|------------|
| `/` | `LandingPage.tsx` | Marketing, features, pipeline, theme toggle, link to login |
| `/login` | `Login.tsx` | Signup and login |
| `/app` | `DashboardHome.tsx` | Shortcuts, recent papers, how-it-works |
| `/app/compose` | `ComposePaper.tsx` | Full composer: style, kind, depth, attachments, refine, generate, preview, handoff |
| `/app/documents` | `MyDocuments.tsx` | DocOS documents you own |
| `/app/editor` | `DocumentEditor.tsx` | Graph editor, AI panel, versions, exact view, import |
| `/app/files` | `GeneratedFiles.tsx` | Recent composed papers, export |
| `/app/settings` | `Settings.tsx` | Profile, password, `/health` including `exact_preview` |
| `/app/new` | redirect | -> compose |
| `/app/assistant` | redirect | -> editor |

Layout: `DashboardLayout` (nav, theme). Auth: `RequireAuth`.

Key components: `AIPanel` (live task, reasoning, provider, history), `VersionTimeline`, `GraphCanvas` / `NodeView`, `measurePages.ts` (paginate by measuring, not only Word markers), `DocumentPreview`, `InstructionRefiner`, `GenerationStatus`, `ThemeToggle`.

---

## HTTP API

Interactive: http://127.0.0.1:8000/docs

Unless noted, JSON in/out. Errors: `{ "detail": "..." }` (FastAPI). Owner mismatch: 403. Missing doc: 404.

### Meta

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/health` | no | `{ "status": "ok", "version": "1.0.0", "exact_preview": true/false }` |
| GET | `/providers/status` | no | Router status (configured?, cooldown remaining). No API keys |

### Paper (Bearer)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/paper/styles` | Built-in + your custom summaries |
| GET | `/paper/styles/{style_id}` | Full stylesheet |
| POST | `/paper/styles` | Create custom. 422 invalid |
| DELETE | `/paper/styles/{style_id}` | Custom only. 404 if missing |
| POST | `/paper/instructions/refine` | See Compose |
| POST | `/paper/generate` | `{ provider, spec, document_id }`. Saves `{owner_id, spec, created_at}` as `{id}.spec.json`. 502 `PaperGenerationError`. 499 cancelled |
| POST | `/paper/render` | Body = spec object. Returns `.docx`. Empty/no blocks: 422 |
| POST | `/paper/preview` | Spec -> PDF. 503 if no LibreOffice |
| POST | `/paper/compose` | Generate + render, file download |
| GET | `/paper/recent` | Your last 20 specs (title, style, created_at, document_id) |
| GET | `/paper/{document_id}/export/docx` | Re-render owned spec |
| GET | `/paper/{document_id}/export/pdf` | Needs LibreOffice |

### DocOS (Bearer; WS uses query token)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/docos` | `{ document_id, title, created_at, current_version, versions }[]` |
| POST | `/docos/import` | multipart `file`. Parse failure 400 |
| POST | `/docos/import-spec` | `{ spec, title? }`. No blocks: 422 |
| GET | `/docos/{id}` | Current graph + metadata |
| GET | `/docos/{id}/exact.pdf` | Current graph -> docx -> LibreOffice PDF. 503 if unavailable |
| GET | `/docos/{id}/history` | Version list |
| GET | `/docos/{id}/diff?a=&b=` | Seq integers |
| POST | `/docos/{id}/command` | `{ "command": "..." }` -> result + collected events. Also broadcasts to WS watchers |
| WS | `/docos/ws/{id}?token=` | See WebSocket. Close 4401 if token bad |

### Legacy (`main.py`, mostly unauthenticated)

| Method | Path | Notes |
|--------|------|--------|
| POST | `/generate` | Old section pipeline |
| GET | `/documents/recent` | Last 10 drafts (not owner-scoped like `/paper/recent`) |
| GET/PUT | `/documents/{id}/draft` | |
| POST | `/documents/{id}/sections/{sid}/rewrite` | Tone rewrite |
| POST | `/documents/{id}/analyze-charts` | |
| POST | `/documents/{id}/charts/{index}/render` | |
| GET | `/documents/{id}/charts/{index}/image` | PNG |
| GET | `/documents/{id}/export/docx\|pdf\|excel` | |

Prefer `/paper` and `/docos` for new work.

### Example: login then generate

```powershell
$login = Invoke-RestMethod -Method POST http://127.0.0.1:8000/auth/login `
  -ContentType application/json `
  -Body '{"email":"you@example.com","password":"secret1"}'
$token = $login.token
$headers = @{ Authorization = "Bearer $token" }

Invoke-RestMethod -Method POST http://127.0.0.1:8000/paper/generate `
  -Headers $headers -ContentType application/json `
  -Body '{"raw_text":"Notes on TCP congestion control.","style":"ieee","doc_kind":"paper","depth":"brief"}'
```

---

## WebSocket protocol

URL: `ws://127.0.0.1:8000/docos/ws/{document_id}?token={jwt}`

**Client -> server** (JSON):

```json
{ "command": "center all figures" }
```

Empty command -> `{ "event": "error", "payload": { "detail": "empty command" } }`.

**Server -> client**: execution `Event.to_message()` plus command-layer messages such as `command_parsed` (actions, reasoning, provider, source). Payloads include node ids and short text previews for animation.

Multiple tabs on the same `document_id` share the hub: REST commands also `broadcast` to watchers.

---

## Action language

The model (or heuristics) must emit:

```json
{
  "reasoning": "short summary for the AI panel",
  "actions": [
    {
      "type": "align",
      "target": "figure",
      "node_ids": [],
      "style": null,
      "params": { "alignment": "center" }
    }
  ]
}
```

**Types:** `select`, `format`, `delete`, `insert`, `replace`, `highlight`, `justify`, `align`, `resize`, `move`, `copy`, `paste`, `merge`, `split`, `normalize`, `rewrite`.

**Targets:** `heading`, `subheading`, `paragraph`, `body`, `table`, `table_cell`, `figure`, `image`, `caption`, `reference`, `horizontal_rule`, `page_break`, `header`, `footer`, `footnote`.

Scoped ops need `target` or `node_ids`. Validation extras:

- `align`: `params.alignment` in left | center | right | justify
- `resize`: `font_size` in params or style
- `replace`: `params.find` and `params.with`
- `format` / `highlight`: a style (or highlight color)
- `delete` of every `paragraph`/`body` without `node_ids` requires `params.confirm: true`

Failed validation: batch not executed.

**Heuristic keywords (offline fallback):** select/find/show/list, highlight, remove/delete, justify, center/centre, font size/resize/size, bold; otherwise select headings.

**Control phrases:** `undo`, `redo`, `rewind to version 3`, `restore to version 3`, `compare versions 2 and 5`.

---

## PaperSpec (generation contract)

Top level: `meta`, `blocks[]`, `references[]` (strings), `visualization_plan[]`, `resolved`.

**meta:** title, authors[], abstract, keywords[], `title_page`, `title_page_lines[]`, `page_header`, `style`, `page` (width/height/margins inches, columns, column_spacing).

**block types** (`type` discriminator):

| type | Fields of interest |
|------|--------------------|
| `heading` | `level` 1-3, `text` |
| `paragraph` | `text` |
| `list` | `ordered`, `items[]` |
| `equation` | TeX `text`, `numbered`, `render` auto\|text\|image |
| `table` | caption, columns, rows, span column\|page |
| `figure` | caption, `chart` (bar/line/pie/scatter/grouped_bar), or `image_path`, span |
| `code` | language, text, caption, filename, render text\|image, window editor\|terminal, theme |
| `page_break` | cover sheet / new page |

Charts coerce loose labels ("pie chart", "line graph") to enum kinds. Charts with no values are skipped so you do not get empty axes.

Renderer: `paper/renderer.py`. Spec to editor: `paper/to_graph.py` (keeps listings/equations/figures as graph types).

---

## Stylesheets

`StyleSheet` is data: per-element `Style` (font, size_pt, bold, italic, small_caps, alignment, indents, spacing) plus conventions:

- `heading_scheme`: roman_alpha | decimal | none
- table/figure/code caption prefix, position, numbering
- `table_borders`: horizontal | grid | none
- `references_title`, `abstract_lead`, `keywords_lead`, `number_references`

IEEE and assignment modules live under `backend/app/paper/styles/`. User sheets are stored per owner (same resolver API). `GET /paper/styles/{id}` is a starting point for a custom sheet.

---

## LLM router

`backend/app/services/router.py`. One provider today: **Mistral**. Shape kept (order list, cooldowns, `status()`) for a possible second provider.

Cooldowns: rate limit 60s, timeout 30s, other error 10s. `GenerationCancelled` is not a provider failure.

Command engine asks for strict JSON (~900 tokens). Paper generate uses a large budget. Rewriter uses 4000 tokens per page-sized pass.

`GET /providers/status` shows whether a key is configured and cooldown state.

---

## Storage on disk

Default root: `backend/.data/` (`DOCPILOT_DATA_DIR`). Gitignored.

Typical layout:

```
backend/.data/
  secret.key              auto DOCOS_SECRET if env unset
  documents/
    {id}.spec.json        composed papers (includes owner_id)
    {id}.docx             rendered files
  charts/                 PNG charts (legacy + paper figures)
  templates/              created by storage helper
  (SQLite)                DocOS documents, versions, users, custom styles
```

Version 0 of a DocOS doc is always a checkpoint (the import). Seq 10, 20, ... snapshot again.

---

## LibreOffice (exact layout)

HTML/CSS in the editor is an approximation. Word's line breaking and pagination need a real layout engine.

When `soffice` is found (`PATH`, `LIBREOFFICE_PATH`, or common install paths on Windows/macOS/Linux):

- `/health` -> `"exact_preview": true`
- Compose: `POST /paper/preview` PDF
- Editor: `GET /docos/{id}/exact.pdf` from the **current** graph (edits included), not the original upload
- Import: `repaginate()` maps nodes to PDF pages by text
- Paper PDF export

If missing: 503 on those routes; UI falls back to HTML preview / marker+measurement pagination.

Windows default:

`C:\Program Files\LibreOffice\program\soffice.exe`

Conversion timeout: 240s (large docs).

---

## Tests

From `backend/` with the venv active:

```powershell
pytest
pytest tests/test_docos.py -q
pytest -k ownership
```

Needs `pytest` (in `requirements.txt`). Some tests hit Mistral only if `MISTRAL_API_KEY` is set (`test_all.py`).

| File | Covers |
|------|--------|
| `test_account.py` | signup, login, profile, password |
| `test_paper.py` | spec, generate/render paths |
| `test_paper_api_validation.py` | empty spec, 422s |
| `test_paper_ownership.py` | recent list and export scoped to owner |
| `test_refine.py` | instruction refiner |
| `test_agentic.py` | plan/section assembly |
| `test_generator_recovery.py` | truncated JSON retry |
| `test_cancellation.py` | client disconnect / cancel |
| `test_compose_handoff.py` | spec -> DocOS |
| `test_spec_to_graph.py` | typed nodes from spec |
| `test_custom_styles.py` | user stylesheets |
| `test_assignment_and_listings.py` | assignment style, code blocks |
| `test_equations_and_code.py` / `test_codeshot_and_equations.py` | math and listings |
| `test_layout_instructions.py` | title page, headers, breaks |
| `test_jsonx.py` | extract JSON from model prose |
| `test_docos.py` | graph, actions, versions |
| `test_docx_import.py` / `test_docx_fidelity.py` | parser |
| `test_docos_export.py` | graph -> docx |

---

## Scripts

**Frontend** (`frontend/package.json`)

- `npm run dev` -- Vite HMR
- `npm run build` -- `tsc -b && vite build`
- `npm run lint` -- ESLint
- `npm run preview` -- serve `dist`

**Backend**

- `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- `pytest`
- `python -m app.paper.cli` -- optional paper CLI (see `paper/cli.py`)

---

## Troubleshooting

**UI loads, API calls fail (CORS / network)**  
Confirm the API is on 8000 and `VITE_API_URL` matches. CORS is only 5173. A production UI on another origin will be blocked until CORS is widened in `main.py`.

**401 on every /paper or /docos call**  
Token missing or expired (7 days). Log in again. WS must include `?token=`.

**409 on signup**  
Email already registered.

**Generation 502**  
No key, Mistral error, or unparseable JSON after retry. Check `GET /providers/status` and backend logs.

**Generation hangs then dies**  
Timeout scales with token budget. Override with `LLM_TIMEOUT` only if you know you need a hard cap; too small aborts a still-writing document.

**Preview / exact view 503**  
Install LibreOffice or set `LIBREOFFICE_PATH`. Confirm `/health` `exact_preview`.

**Imported Word looks short or wrong fonts**  
Editor paginates by measuring; import can use LibreOffice pages. Exact view shows layout-engine truth. Spec handoff preserves types better than DOCX round-trip.

**"Done" but text did not change**  
Use a `rewrite` instruction so the rewriter sees the prose. Format/select commands do not rewrite sentences.

**Delete all body refused**  
Validator requires `confirm: true` or explicit `node_ids`.

**Tokens invalid after deleting `.data`**  
`secret.key` was regenerated. Set `DOCOS_SECRET` in `.env` for a stable secret.

**Port 8000 in use**  
Start uvicorn on 8010 and set `VITE_API_URL`.

**pytest import errors**  
Run from `backend/` with venv activated.

---

## Security notes

- Do not commit `.env` or `backend/.data/`.
- Set `DOCOS_SECRET` in any shared/deployed environment.
- `/paper/recent` and DocOS list/get are owner-scoped. The legacy `/documents/recent` is not; do not expose it as a multi-user API.
- CORS is localhost-only in this repo.
- Password change requires the current password (stolen session should not lock the owner out by itself).
- Action batches are validated; bulk delete of body needs confirm.
- LLM output is untrusted JSON until `validate_batch` / `PaperSpec.model_validate`.

---

## License

Private project unless a `LICENSE` file is added to the repository.

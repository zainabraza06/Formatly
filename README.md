# Formatly

Formatly is an AI document workspace with two halves that meet in the middle.

**Compose** turns notes into a fully styled paper or report. **Document OS** opens a
document — one Formatly wrote, or a `.docx` you already had — and lets you keep
editing it in plain English: *"put the contributions in bullets"*, *"only the top
and bottom borders, bold"*, *"increase the headings by 2"*.

The rule that shapes everything below: **the model never writes the document.** It
emits JSON describing what to do. A validator checks it, a deterministic engine
applies it, and every change is versioned and reversible.

**Local URLs** — UI <http://localhost:5173> · API docs <http://127.0.0.1:8000/docs> ·
health <http://127.0.0.1:8000/health>

---

## Contents

1. [Quick start](#quick-start)
2. [The two products](#the-two-products)
3. [Document OS: the four engines](#document-os-the-four-engines)
4. [The document model](#the-document-model)
5. [Import: a .docx becomes a graph](#import-a-docx-becomes-a-graph)
6. [Understanding a command](#understanding-a-command)
7. [The action language](#the-action-language)
8. [Execution](#execution)
9. [Versions](#versions)
10. [Live events](#live-events)
11. [Rendering and pagination](#rendering-and-pagination)
12. [Export](#export)
13. [Mathematics, both ways](#mathematics-both-ways)
14. [Compose](#compose)
15. [Accounts and ownership](#accounts-and-ownership)
16. [HTTP and WebSocket API](#http-and-websocket-api)
17. [Configuration](#configuration)
18. [Data on disk](#data-on-disk)
19. [Testing](#testing)
20. [Troubleshooting](#troubleshooting)
21. [Design invariants](#design-invariants)

---

## Quick start

Prerequisites: **Python 3.14** (3.11+ works), **Node 20+**, and optionally
**LibreOffice** for exact-layout PDF.

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # POSIX: .venv/bin/pip
cp .env.example .env        # add MISTRAL_API_KEY
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend, in another shell
cd frontend
npm install
npm run dev
```

Without an API key the app still runs: the editor falls back to its rule-based
command reader, which handles most ordinary instructions on its own (see
[Understanding a command](#understanding-a-command)).

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q     # 641 tests
```

---

## The two products

```mermaid
flowchart LR
    subgraph Compose["Compose  ·  backend/app/paper"]
        N[notes, attachments,<br/>stylesheet, depth] --> G[generator<br/>LLM writes semantic blocks]
        G --> S[PaperSpec JSON]
        S --> SS[stylesheet resolver<br/>stamps fonts, sizes, numbering]
        SS --> R[renderer<br/>deterministic .docx]
    end

    subgraph DocOS["Document OS  ·  backend/app/docos"]
        D[.docx upload] --> P[parser]
        P --> GR[(DocumentGraph)]
        GR --> C[command engine]
        C --> E[execution engine]
        E --> GR
        GR --> V[(versions)]
        GR --> X[export]
    end

    S -- "import-spec<br/>(no .docx round trip)" --> GR
    R --> D

    Compose -.shares.- SVC[auth · LLM router · data dir]
    DocOS -.shares.- SVC
```

A composed document can enter Document OS **without** going through a `.docx`
first. Going through a file would flatten what the spec knows — a listing into
loose paragraphs, an equation into whatever characters it typeset to — because
DOCX has no word for either.

---

## Document OS: the four engines

```mermaid
flowchart TB
    U([instruction in plain English]) --> CE

    subgraph CE["Command engine · docos/command"]
        direction TB
        CTRL{control op?<br/>undo / redo / rewind} -->|yes| CTL[version op]
        CTRL -->|no| PLAN[plan the instruction]
        PLAN --> BATCH[ActionBatch JSON]
    end

    BATCH --> VAL{validator<br/>docos/actions}
    VAL -->|invalid| REJ[rejected · graph untouched]
    VAL -->|valid| SVC

    subgraph SVC["Service · docos/service.py"]
        direction TB
        IDS[drop invented node ids] --> SPANS[resolve described spans]
        SPANS --> SEC[pin to a named section]
        SEC --> RW[resolve rewrites against real text]
    end

    SVC --> EX

    subgraph EX["Execution engine · docos/execution"]
        direction TB
        CLONE[clone the graph] --> APPLY[apply each action<br/>streaming events]
        APPLY -->|any failure| ROLL[discard the clone]
        APPLY -->|all fine| OK[the new graph]
    end

    OK --> VE[Version engine<br/>commit + stream]
    ROLL --> REJ
    CTL --> VE
    VE --> WS([WebSocket events → editor])
```

| Engine | Package | Job |
|---|---|---|
| **Document** | `docos/graph`, `docos/parser` | Typed node tree; DOCX → graph; optional LibreOffice pagination |
| **Command** | `docos/command` | Instruction → control op or validated `ActionBatch` |
| **Execution** | `docos/execution` | **Sole mutator.** Clone, apply, stream, roll back on failure |
| **Version** | `docos/versioning` | SQLite history; snapshot every 10, replay actions between |

Deeper notes live in `backend/app/docos/ARCHITECTURE.md`.

---

## The document model

A document is a tree of typed nodes. Nothing about layout is inferred — every
value is one the file stated, converted to the units the model uses: **inches**
for widths, **points** for type and rules, **hex** for colour.

```mermaid
classDiagram
    class DocumentGraph {
        +Node root
        +str title
        +nodes() Iterator
        +resolve_target(str) Node[]
        +insert_after(id, node)
        +clone() DocumentGraph
    }
    class Node {
        +str id
        +NodeType type
        +str content
        +Style style
        +Run[] runs
        +dict metadata
        +Node[] children
        +apply_style(patch)
        +style_span(find, patch)
        +inline_runs() Run[]
    }
    class Run {
        +str text
        +Style style
    }
    class Style {
        +font_family, font_size
        +bold, italic, underline
        +color, highlight
        +alignment
        +vertical_align
    }
    DocumentGraph "1" --> "1" Node : root
    Node "1" --> "*" Node : children
    Node "1" --> "*" Run : runs
    Node --> Style
    Run --> Style
```

**17 node types** — `document`, `paragraph`, `heading`, `subheading`, `body`,
`image`, `figure`, `caption`, `table`, `table_row`, `table_cell`,
`horizontal_rule`, `page_break`, `header`, `footer`, `reference`, `footnote`.

**Runs** are why a paragraph can be half bold. `style` is the paragraph's own
formatting; `runs` describe it piece by piece. Runs that no longer spell out
`content` are ignored rather than trusted, so a rewrite cannot leave stale
formatting attached to words that are gone.

**`metadata`** carries everything Word states that is not a style:

| Key | Means |
|---|---|
| `list` | `{kind: bullet\|number, level}` — a bullet is a property of the paragraph, not characters typed into it |
| `borders` | a table's six edges in points, plus `header` for the rule under the heading row |
| `columns_in`, `width_in`, `align`, `cell_pad_in` | a table's geometry |
| `shade`, `valign`, `span`, `vmerge` | one cell's shading, placement and merging |
| `line_spacing`, `space_before_pt`, `space_after_pt`, `indent_*_pt` | paragraph spacing |
| `equations` | the original OMML for an equation nobody has edited |
| `header_row` | the row a table treats as its heading |

---

## Import: a .docx becomes a graph

```mermaid
flowchart TB
    F[.docx bytes] --> B[walk the body in document order]
    B --> PARA{what is this block?}

    PARA -->|w:tbl| T[table<br/>columns, borders, cell padding,<br/>shading, merges, header row]
    PARA -->|picture| IMG[figure + image<br/>bytes inlined as data URI]
    PARA -->|border or VML rule| HR[horizontal rule]
    PARA -->|only a break| PB[page break]
    PARA -->|words| CL[classify]

    CL --> STY[style name:<br/>Heading, List Bullet, List Number]
    CL --> SHP["shape: numbering, length, weight<br/>(a title is often a bold paragraph,<br/>not a Word Heading)"]
    CL --> CAP["caption by what it says:<br/>Figure 2., TABLE III., Fig. 1:"]
    CL --> OM[OMML equations → LaTeX<br/>original XML kept alongside]

    T --> GR[(DocumentGraph)]
    IMG --> GR
    HR --> GR
    PB --> GR
    STY --> GR
    SHP --> GR
    CAP --> GR
    OM --> GR

    GR --> PG{"≤ 150 nodes<br/>and LibreOffice present?"}
    PG -->|yes| EXACT[exact page count via PDF]
    PG -->|no| MARK["Word's own break markers<br/>(the editor re-measures anyway)"]
```

Two things the parser learned the hard way, both because a document says them in
more than one place:

- **Lists** live in a `List Bullet`/`List Number` *style* or an inline `w:numPr`.
  `List Paragraph` alone is not a list — Word gives that style to any indented
  block, and reading it as one put a bullet on the sentence introducing the list.
- **Table borders** are usually stated by the table's *style*, not on the table.
  Reading only the table's own XML reported no edges at all, and the editor then
  drew a full grid whatever the style said.

---

## Understanding a command

An instruction gets three chances, in falling order of context and rising order
of certainty that an answer comes back at all.

```mermaid
flowchart TB
    I([instruction]) --> CTRL{"matches a control phrase?<br/>undo · redo · rewind to version N"}
    CTRL -->|yes| OP[control op · no model involved]

    CTRL -->|no| FULL["**1 · full plan**<br/>instruction + the document's brief<br/>≈ 7,000 chars · 40s budget"]
    FULL -->|JSON| VALID{valid batch?}
    FULL -->|"timeout, outage,<br/>rate limit, prose"| BRIEF

    VALID -->|yes| DONE([ActionBatch])
    VALID -->|no| BRIEF

    BRIEF["**2 · brief plan**<br/>instruction alone<br/>≈ 195 chars · a 37× smaller ask"]
    BRIEF -->|JSON| VALID2{valid batch?}
    VALID2 -->|yes| DONE
    VALID2 -->|no| RULES

    RULES["**3 · rules**<br/>deterministic, offline, instant"]
    RULES --> DONE
```

**Why three.** The planner reads rewording perfectly — *"squash the gap between
paragraphs"*, *"put a line under the header row of each table"* — and answers in
about a second and a half. What used to be brittle was the path taken when it
answered at all: the rules match *words*, so a synonym was a different request to
them. The brief plan exists because what times out is not the instruction but the
document's brief travelling with it.

The panel always says which of the three answered, and why the others did not.

**The rules on their own** handle: weight and slope, colour, highlight, all four
alignments, size as a number / a step (`by 2`) / a direction (`larger`), bullets
and numbering, letter case, line spacing and paragraph gaps, typeface, table
borders (including *"keep the top and bottom, removing the left and right"*),
phrases named outright, and deletion of a class of thing. Anything they cannot
place goes to the rewriter rather than being dismissed.

### Placing an instruction in the document

```mermaid
flowchart LR
    A[action with no node ids] --> N{"does it already<br/>name what it is about?"}
    N -->|"yes: 'the table', a border"| K[leave it alone]
    N -->|no| L[locate_section<br/>match against headings and<br/>what each section is about]
    L -->|found| PIN[pin to those node ids]
    L -->|nothing| T[fall back to the target class]
    PIN --> H{"only headings<br/>in scope?"}
    H -->|yes| EXP["expand to the section beneath —<br/>the planner names a section<br/>by its heading's id"]
    H -->|no| GO([execute])
    EXP --> GO
    K --> GO
    T --> GO
```

---

## The action language

Every instruction becomes an `ActionBatch`: a short reasoning string and a list of
actions. **21 action types:**

```
align  border  case  copy  delete  format  highlight  insert  justify  list
merge  move  normalize  paste  render_maths  replace  resize  rewrite  select
spacing  split
```

```jsonc
{
  "reasoning": "…",
  "actions": [{
    "type": "format",
    "target": "heading",          // a class of thing, or…
    "node_ids": ["n_a1b2c3"],     // …exactly these nodes
    "style":  { "bold": true },
    "params": { "find": "MobiAct" }
  }]
}
```

**18 targets** — `body`, `caption`, `document`, `figure`, `footer`, `footnote`,
`header`, `heading`, `horizontal_rule`, `image`, `page_break`, `paragraph`,
`reference`, `subheading`, `table`, `table_cell`, `table_header`, `title`.

Three of those are roles rather than node types: `table_header` (the cells of a
header row), `title` (the first thing the document says, heading or not), and
`document` (everywhere words are — for a phrase that could be anywhere).

**Notable params**

| Action | Params | Note |
|---|---|---|
| `format` | `find` / `describe` / `spans` | a quoted phrase is searched for; a *described* one is resolved by a model and each span checked against the real text before use |
| `resize` | `font_size` \| `delta` \| `scale` | `12 pt`, `by 2`, and `larger` are three different requests; a "size" under 5 pt is read as a misplaced step |
| `list` | `kind: bullet\|number\|none`, `level` | splits an enumerating paragraph into its items |
| `border` | `sides` (list or side→width map), `width` | naming sides means those **and no others** |
| `case` | `kind: upper\|lower\|title\|sentence` | mechanical, so no model is asked |
| `spacing` | `line`, `before_pt`, `after_pt` | |

**Validation** rejects unknown targets, missing scope, malformed params, and
refuses to delete every paragraph in a document without explicit confirmation.
An invalid batch never reaches the graph.

---

## Execution

```mermaid
sequenceDiagram
    participant S as Service
    participant E as ExecutionEngine
    participant W as working clone
    participant O as original graph

    S->>E: execute(graph, batch)
    E->>O: clone()
    O-->>W: a copy
    loop each action
        E->>W: apply
        E-->>S: events (started, progress, finished)
    end
    alt an action fails
        E->>W: discard
        E-->>S: BATCH_FAILED + the untouched original
    else all applied
        E-->>S: the new graph
        S->>S: what actually changed?
        S->>S: commit a version
    end
```

The executor is the only code that mutates a graph. It works on a clone, so a
failure halfway through leaves nothing half-done. Two details that took several
bugs to get right:

- **What changed** compares content, style, *runs* and *metadata*. Comparing only
  text and style called a bolded word, a bullet and a table border "nothing".
- **A table has no words of its own.** Text formatting aimed at a table expands to
  its cells; alignment does not, because a table is aligned as a block.

---

## Versions

```mermaid
flowchart LR
    V0["v0 · snapshot<br/>(import)"] --> V1[v1 · actions]
    V1 --> V2[v2 · actions]
    V2 --> D1["…"]
    D1 --> V10["v10 · snapshot"]
    V10 --> V11[v11 · actions]
    V11 --> V12[v12 · actions]

    subgraph MAT["materialising v12"]
        direction LR
        S[nearest snapshot: v10] --> RP[replay v11, v12]
        RP --> G[(the graph)]
    end
```

Every version stores its **action batch**; every tenth stores a **full snapshot**.
A version is materialised by taking the nearest snapshot and replaying forward,
which is why a rewrite records its *resolved text* rather than its instruction —
asking a model again would give different words every time.

| Operation | Effect |
|---|---|
| **undo** / **redo** | move along the chain |
| **rewind** | move the head to an earlier version |
| **restore** | make an earlier version the *newest* one, keeping the history between |
| **compare** | word-level diff of two versions, with before/after text per node |

`restore` takes a snapshot of its own: its batch is empty, so replaying it would
otherwise reproduce the parent instead of the version asked for.

---

## Live events

```mermaid
sequenceDiagram
    participant UI as Editor
    participant WS as /docos/ws/{id}
    participant SV as Service
    participant EX as Execution

    UI->>WS: connect (token in query)
    UI->>WS: {"command": "make the headings bold"}
    WS->>SV: run_command
    SV-->>UI: command_parsed (which planner, the plan)
    SV-->>UI: section_located (when a section was named)
    SV-->>UI: spans_resolved (when words were described)
    SV->>EX: execute
    EX-->>UI: format_started {target, total}
    loop each node
        EX-->>UI: format_progress {id, index}
    end
    EX-->>UI: format_finished {count}
    SV-->>UI: version_committed {seq, summary}
    Note over UI: the page animates node by node,<br/>then shows what was done
```

The line under **Done** is built from the actions that ran and the nodes that
actually changed — *"Bolded "GBP 2.41" and "GBP 2.66" in Executive Summary"*,
*"Bulleted 4 paragraphs"*, *"Drew heavy top and bottom borders on 10 tables, and
no others"*. It used to show the planner's own reasoning, which is a note the
planner writes to itself about node ids, and which read the same whether anything
had happened or not.

---

## Rendering and pagination

The editor draws the document itself rather than embedding a viewer, so every
node stays addressable and every change animates in place.

```mermaid
flowchart TB
    G[(graph)] --> PROOF["measuring pass<br/>every node laid out once,<br/>off-screen, at the real text width"]
    PROOF --> M[measured heights]
    M --> FILL["fill each page until the next node<br/>would cross the bottom margin"]
    FILL --> SPLIT["a paragraph that does not fit<br/>is split at the last line that does"]
    SPLIT --> PAGES[pages]
    PAGES --> SHEET["white sheet at the document's<br/>real size, scaled to fit the frame"]
```

Word's saved break markers are only the starting point: they describe the layout
of the machine that last saved the file. What the page shows is measured.

Fidelity details that each cost a visible bug: type is drawn in **points**, not
pixels; Word's line-spacing multiple is a multiple of the font's *own* line
height, not of its size; a table uses the document's cell padding (0.075″ at the
sides, none above) rather than the editor's; and a cell is set in the document's
type, not a fixed 10pt.

**Exact view** is a different answer to the same question: LibreOffice renders the
*current* graph to PDF, so it shows real Word pagination including your edits.

---

## Export

```mermaid
flowchart TB
    G[(current graph)] --> W[write nodes in order]
    W --> P{node kind}
    P -->|paragraph| PR["style, spacing, list style,<br/>one Word run per formatted piece"]
    P -->|table| TB["columns, borders, cell padding,<br/>shading, merges"]
    P -->|image| IM[picture, clamped to the text width]
    P -->|rule / break| RB[border paragraph / page break]

    PR --> EQ{equations?}
    EQ -->|"stored OMML, untouched"| ORIG[write Word's original XML back]
    EQ -->|"typed LaTeX + maths drawn"| CONV[LaTeX → OMML]
    EQ -->|"maths off"| TXT["write the characters as typed"]

    ORIG --> DOC[.docx]
    CONV --> DOC
    TXT --> DOC
    TB --> DOC
    IM --> DOC
    RB --> DOC

    DOC --> PDF["PDF via LibreOffice<br/>(same file, laid out)"]
```

### The schema is an order, not just a set

Word validates the **sequence** of elements inside a property container. All three
of these are well-formed XML and a file Word refuses to open, saying only *"we
found a problem with its contents"*:

| Wrong | Right |
|---|---|
| `w:tblBorders` after `w:tblLayout` | before it |
| `w:tcBorders` after `w:vAlign` | before it |
| edges written top, bottom, left, right | top, **left**, bottom, right, insideH, insideV |

A fourth: OMML has no bare group — `m:e` is part of a structure, never a thing on
its own, and one sitting straight inside an `m:oMath` invalidates the document.

None of this is caught by round-tripping through our own parser, and LibreOffice
opens all four broken variants happily. `tests/test_docx_is_valid.py` asserts the
order over a document that uses every part of the exporter at once.

---

## Mathematics, both ways

```mermaid
flowchart LR
    subgraph In["reading"]
        OM[Word OMML] --> LX["LaTeX between dollars<br/>+ the original XML kept"]
    end
    subgraph Screen["on the page"]
        LX --> K{"∑ Maths on?"}
        K -->|yes| KT[KaTeX draws it]
        K -->|no| CH[the characters as typed]
    end
    subgraph Out["writing"]
        LX --> U{edited?}
        U -->|no| BACK[the original XML, untouched]
        U -->|"yes, maths drawn"| NEW[LaTeX → OMML]
        U -->|"maths off"| ASIS[the characters as typed]
    end
```

Reading and writing are separate converters (`parser/omml.py`,
`parser/omml_write.py`). The writer covers what a paper uses — fractions, powers
and indices, roots, sums and integrals with limits, bracketed groups, Greek,
operators, upright function names. A command it does not know is written out as
typed rather than guessed at, so an exotic formula degrades to how it looked
before instead of coming out wrong.

Converting equations to *prose* was tried and removed: it is lossy, irreversible,
costs a model call per page, and cannot be undone by looking at the result.
Drawing them is a display change that alters no words.

---

## Compose

```mermaid
flowchart TB
    N[notes + attachments] --> RF{refine an<br/>extra instruction?}
    RF -->|yes| RI[LLM turns 'like a lab report'<br/>into something a writer can follow]
    RF -->|no| PL
    RI --> PL[plan the sections]
    PL --> WR{depth}
    WR -->|brief| ONE[one pass]
    WR -->|standard| MANY[section by section,<br/>each retried on failure]
    ONE --> SPEC[PaperSpec JSON<br/>semantic blocks only]
    MANY --> SPEC
    SPEC --> ST["stylesheet resolver<br/>IEEE 1-col / 2-col / assignment / custom"]
    ST --> RD[renderer → .docx]
    SPEC --> IG["import-spec → DocumentGraph<br/>(keeps listings and equations)"]
```

The model emits **semantic** blocks — heading, paragraph, table, equation,
listing, figure — and never layout. The stylesheet stamps fonts, sizes, numbering
and captions afterwards, so the same spec can be set as an IEEE paper or a formal
assignment without asking the model again.

---

## Accounts and ownership

- Sign up / log in; the token lives in `localStorage` as `docos.token` and is sent
  as `Authorization: Bearer …`. The WebSocket takes it as a query parameter.
- Papers and documents are **owner-scoped**. A stranger's id is `403`, an unknown
  id is `404`; neither reports success.
- Deleting is checked the same way, including *Delete all*, which lists only the
  caller's own documents and deletes them by id.

---

## HTTP and WebSocket API

All DocOS and paper routes take a Bearer token.

### Documents

| Method | Path | Does |
|---|---|---|
| `GET` | `/docos` | list your documents |
| `POST` | `/docos/import` | upload a `.docx` |
| `POST` | `/docos/import-spec` | import a composed spec directly |
| `GET` | `/docos/{id}` | the current graph |
| `DELETE` | `/docos/{id}` | delete one, with its history |
| `DELETE` | `/docos` | delete **all** of yours |
| `GET` | `/docos/{id}/download.docx?maths=1` | export; `maths=1` writes typed LaTeX as equations |
| `GET` | `/docos/{id}/download.pdf?maths=1` | the same file, laid out by LibreOffice |
| `GET` | `/docos/{id}/exact.pdf` | exact view of the current graph |
| `GET` | `/docos/{id}/brief` | what the document is: kind, sections, inventory |
| `POST` | `/docos/{id}/read` | read it through, section by section |
| `GET` | `/docos/{id}/history` | versions |
| `GET` | `/docos/{id}/diff?a=3&b=7` | word-level diff |
| `POST` | `/docos/{id}/command` | run an instruction (non-streaming) |
| `WS` | `/docos/ws/{id}?token=…` | run instructions and receive events |

### Auth

`POST /auth/signup` · `POST /auth/login` · `GET /auth/me` · `POST /auth/password`

### WebSocket messages

```jsonc
// → server
{ "command": "make the headings bold" }

// ← server, in order
{ "event": "command_parsed",    "payload": { "source": "llm", "actions": [...] } }
{ "event": "format_started",    "payload": { "target": "heading", "total": 7 } }
{ "event": "format_progress",   "payload": { "id": "n_…", "index": 0 } }
{ "event": "format_finished",   "payload": { "count": 7 } }
{ "event": "version_committed", "payload": { "seq": 12, "summary": "Bolded 7 headings." } }
```

---

## Configuration

`backend/.env`:

| Variable | Meaning |
|---|---|
| `MISTRAL_API_KEY` | the planner and rewriter; without it the rules answer everything |
| `MISTRAL_MODEL` | default `mistral-medium-latest` |
| `MISTRAL_LIGHT_MODEL` | comma-separated ladder of smaller models to try when the main one is busy; empty turns it off |
| `DOCPILOT_DATA_DIR` | where documents and the database live |

The router keeps a per-provider cooldown, retries on 429/5xx, walks down the
model ladder on 403/404 (a plan the account cannot run), and gives up rather than
hanging. Every failure reason travels back to the panel.

**Frontend** — `VITE_API_URL` (defaults to `http://127.0.0.1:8000`).

---

## Data on disk

```
backend/.data/
├── docos.db          documents, versions, users, saved styles (SQLite)
├── documents/        generated .docx and PDF
├── templates/        saved stylesheets
├── charts/           generated figures
└── secret.key        token signing key
```

The test suite runs against a temporary directory of its own, so it can never
leave documents in yours.

---

## Testing

**641 tests.** Two of them are sweeps rather than examples, because every bug in
the command area had one of two shapes.

```mermaid
flowchart LR
    subgraph One["the document had it, the model did not"]
        A["test_command_matrix<br/>~45 instructions against one paper,<br/>each checked by what it did"]
    end
    subgraph Two["the model had it, the page did not"]
        B["test_renderer_covers_the_model<br/>every Style field and every visible<br/>metadata key must appear in the renderer"]
    end
    subgraph Three["the file was invalid"]
        C["test_docx_is_valid<br/>schema order over a document using<br/>every part of the exporter"]
    end
```

The matrix runs **offline**, so it tests the rules rather than the model's mood:
a phrasing that stops being understood fails there rather than in front of
someone. The renderer sweep is deliberately coarse — an edit that silently fails
to apply leaves no other trace, which is exactly how table borders once shipped
working in the model and invisible on the page.

Other suites cover the parser, export fidelity, versioning, the router's
fallbacks, spans, lists, table layout, typed emphasis, and the equation
converters in both directions.

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q
cd frontend && npx tsc --noEmit -p tsconfig.app.json && npm run lint
```

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| **Word: "we found a problem with its contents"** | an element written out of schema order — see [Export](#export). LibreOffice will open the same file happily |
| **"The planner could not be used… this plan is a fallback"** | the model timed out or the account cannot use it; the rules answered instead. The panel names the reason |
| **A command reports "the document already looks that way"** | it found its scope and had nothing to do. If that seems wrong, the scope was wrong — check `section_located` in the events |
| **Exact view or PDF fails** | LibreOffice is not installed or not on `PATH` |
| **Equations show as `$…$`** | the ∑ Maths toggle is off; it governs the page *and* the download |
| **Pages differ from Word** | the editor measures its own layout; Exact view is the authority |

---

## Design invariants

These are the rules the code is arranged around. Most were learned by breaking
them.

1. **The model never writes the document.** It emits JSON; a validator checks it;
   a deterministic engine applies it.
2. **One mutator.** Only the execution engine changes a graph, on a clone, with
   rollback.
3. **Everything is reversible.** A version stores resolved actions, not
   instructions, so replay is deterministic.
4. **A change nobody can see is a bug**, even if the model, the file and the
   history all agree it happened.
5. **Say what happened, not what was intended.** The outcome line is built from
   what changed.
6. **Degrade, don't fail.** No API key, no LibreOffice, an unknown LaTeX command,
   a provider outage — each loses one capability, not the app.
7. **Read the document, don't guess at it.** Every layout value is one the file
   stated; where a document says something two ways, read both.

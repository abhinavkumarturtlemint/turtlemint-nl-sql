const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, TableOfContents, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageBreak, PageNumber,
  Header, Footer
} = require("docx");

const CONTENT_WIDTH = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 290 },
    children: [new TextRun({ text, ...opts })],
  });
}
function rich(runs, after = 120) {
  return new Paragraph({ spacing: { after, line: 290 },
    children: runs.map(r => new TextRun(r)) });
}
function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] }); }
function bullet(text, lead) {
  const children = [];
  if (lead) children.push(new TextRun({ text: lead + " ", bold: true }));
  children.push(new TextRun(text));
  return new Paragraph({ numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60, line: 285 }, children });
}
function numbered(text, lead) {
  const children = [];
  if (lead) children.push(new TextRun({ text: lead + " ", bold: true }));
  children.push(new TextRun(text));
  return new Paragraph({ numbering: { reference: "numbers", level: 0 },
    spacing: { after: 60, line: 285 }, children });
}
function headerCell(text, w) {
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: cellMargins,
    shading: { fill: "1F3864", type: ShadingType.CLEAR },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF" })] })],
  });
}
function cell(text, w, opts = {}) {
  const runs = Array.isArray(text) ? text.map(t => new TextRun(t)) : [new TextRun(text)];
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ children: runs })],
  });
}
function mono(text) {
  return new Paragraph({ spacing: { after: 120 },
    children: [new TextRun({ text, font: "Consolas", size: 18 })] });
}

const doc = new Document({
  creator: "Claude",
  title: "Statement of Work — Natural Language SQL Query Processor",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal",
        run: { size: 44, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { after: 120 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 320, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "404040" },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: { page: {
      size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
    } },
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "SOW — NL-SQL Query Processor  |  Page ", size: 18, color: "808080" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "808080" }),
      ],
    })] }) },
    children: [
      // COVER
      new Paragraph({ style: "Title", spacing: { before: 2400, after: 80 },
        children: [new TextRun("Statement of Work")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "Natural Language SQL Query Processor", bold: true, size: 32, color: "2E75B6" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 },
        children: [new TextRun({ text: "An internal AI tool for non-technical users to query Turtlemint data in plain English", italics: true, size: 22, color: "595959" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1800 },
        children: [new TextRun({ text: "Prepared by: Abhinav (PM)", size: 22 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Version: 1.0  |  Date: 20 May 2026", size: 22, color: "595959" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240 },
        children: [new TextRun({ text: "Status: Draft for Review", size: 20, italics: true, color: "808080" })] }),

      new Paragraph({ children: [new PageBreak()] }),

      h1("Contents"),
      new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),

      new Paragraph({ children: [new PageBreak()] }),

      // 1. EXECUTIVE SUMMARY
      h1("1. Executive Summary"),
      p("Business users at Turtlemint regularly need answers from the company’s ClickHouse data warehouse but cannot write SQL themselves. Today they wait on data analysts, slowing down decisions. This project delivers an internal AI tool that lets a business user ask a question in plain English and receive a correct, explainable answer along with the underlying SQL — within seconds."),
      p("The approach mirrors Uber’s production “QueryGPT” system: a Retrieval-Augmented Generation (RAG) backbone combined with a pipeline of specialised AI agents (Intent → Table → Generation) and a safety layer (guardrails, query preview, audit log). The single source of truth for table schemas is OpenMetadata; the tool fetches the live schema at SQL-generation time and never relies on a stored copy."),
      p("The MVP targets one business team (recommended: Operations) and is built over 5 weeks across four phases. The success criterion is not “the tool generates SQL” — it is “a business user can self-serve an answer they can trust.”"),

      // 2. OBJECTIVES & SUCCESS METRICS
      h1("2. Objectives and Success Metrics"),
      h2("2.1 Primary objectives"),
      bullet("non-technical users can ask data questions in English without learning SQL.", "Reduce dependence on analysts —"),
      bullet("median answer time below 1 minute, versus the current ~10+ minutes via analyst queue.", "Speed up answers —"),
      bullet("non-technical users can verify and act on the answer (SQL preview, plain-English explanation, audit trail).", "Build trust —"),
      bullet("read-only execution, no risk of data modification or leakage, every action logged.", "Stay safe —"),

      h2("2.2 Success metrics (measured against a golden evaluation set)"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [3200, 3000, 3160],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Metric", 3200), headerCell("Target (MVP)", 3000), headerCell("Stretch (post-MVP)", 3160) ]}),
          new TableRow({ children: [
            cell("Intent classification accuracy", 3200, { fill: "EAF1F8" }),
            cell("≥ 85%", 3000), cell("≥ 95%", 3160) ]}),
          new TableRow({ children: [
            cell("Correct-table selection (overlap score)", 3200, { fill: "EAF1F8" }),
            cell("≥ 0.80", 3000), cell("≥ 0.95", 3160) ]}),
          new TableRow({ children: [
            cell("Query executes successfully", 3200, { fill: "EAF1F8" }),
            cell("≥ 90%", 3000), cell("≥ 98%", 3160) ]}),
          new TableRow({ children: [
            cell("Result semantically matches golden SQL", 3200, { fill: "EAF1F8" }),
            cell("≥ 0.75 similarity", 3000), cell("≥ 0.90", 3160) ]}),
          new TableRow({ children: [
            cell("Median time per question", 3200, { fill: "EAF1F8" }),
            cell("< 60 seconds", 3000), cell("< 20 seconds", 3160) ]}),
          new TableRow({ children: [
            cell("User-reported time savings", 3200, { fill: "EAF1F8" }),
            cell("≥ 70% say faster than asking an analyst", 3000),
            cell("≥ 90%", 3160) ]}),
          new TableRow({ children: [
            cell("Destructive query incidents", 3200, { fill: "EAF1F8" }),
            cell("0 (hard requirement)", 3000), cell("0", 3160) ]}),
        ],
      }),

      // 3. IN SCOPE / OUT OF SCOPE
      h1("3. Scope"),
      h2("3.1 In scope"),
      bullet("Web-based chat-style interface for asking questions and viewing results."),
      bullet("Natural-language to ClickHouse-SQL generation, restricted to read-only SELECT statements."),
      bullet("Live integration with OpenMetadata for current schema retrieval."),
      bullet("Live integration with the existing clickhouse_query_run endpoint for query execution (subject to safety confirmation)."),
      bullet("Multi-agent pipeline: Prompt Enhancer, Intent Agent, Table Agent (with user confirmation), Column Prune Agent, SQL Generator, Result Formatter."),
      bullet("Curated knowledge base of example question-to-SQL pairs and business definitions."),
      bullet("Guardrail layer (SELECT-only enforcement, row limits, query timeout, preview UI, audit log)."),
      bullet("Golden evaluation set and continuous accuracy measurement."),
      bullet("Initial rollout to one identified business team."),

      h2("3.2 Explicitly out of scope (this phase)"),
      bullet("Writing or modifying data (INSERT, UPDATE, DELETE, DDL)."),
      bullet("Cross-database joins outside ClickHouse."),
      bullet("Charting and dashboarding beyond simple result tables and one auto-chart."),
      bullet("Embedding the tool inside other Turtlemint products."),
      bullet("Fine-tuning a custom model — the project uses Claude via Anthropic API only."),
      bullet("Multi-language support (English-only at launch)."),
      bullet("Mobile-native app."),
      bullet("PII redaction logic beyond what OpenMetadata column-level tags already provide."),

      new Paragraph({ children: [new PageBreak()] }),

      // 4. APPROACH
      h1("4. Approach"),
      h2("4.1 Architectural pattern"),
      p("RAG-based agentic pipeline with a hybrid schema strategy. The vector database stores only a lightweight searchable index (table names plus one-line summaries) plus curated example queries and business definitions. Full schema details are fetched live from OpenMetadata at SQL-generation time, so the SQL is always written against the current source of truth."),

      h2("4.2 Reference architecture: Uber QueryGPT"),
      p("Uber’s publicly documented QueryGPT (handling ~1.2M queries/month, time-per-query cut from 10 to 3 minutes) is the reference design. Key adopted principles: domain workspaces for narrowing search, decomposed agents (each LLM call is given one narrow job), human-in-the-loop confirmation at table selection, and a golden-set evaluation framework. Uber’s lesson — that a single end-to-end LLM call hallucinates at scale, and decomposition fixes it — is treated as proven and is adopted from the start."),

      h2("4.3 System architecture (high level)"),
      mono(
`OpenMetadata (source of truth for schema)
       │
       ├── nightly sync ──►  Vector Index (table names + 1-line summaries)
       │                     Knowledge Base (Q→SQL examples, business defs)
       │
       │ live API call (at SQL generation time)
       ▼
User Question ──► Prompt Enhancer ──► Intent Agent ──► Table Agent (user confirms)
   ──► Column Prune Agent ──► SQL Generator ──► Guardrails ──► clickhouse_query_run
   ──► Result Formatter ──► User Answer  +  Audit Log`),

      h2("4.4 Pipeline stages"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [600, 2000, 6760],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("#", 600), headerCell("Stage", 2000), headerCell("Purpose", 6760) ]}),
          new TableRow({ children: [
            cell("1", 600, { fill: "EAF1F8" }),
            cell("Prompt Enhancer", 2000),
            cell("Cleans messy user input (typos, vagueness) into a clear question before any downstream step runs.", 6760) ]}),
          new TableRow({ children: [
            cell("2", 600, { fill: "EAF1F8" }),
            cell("Intent Agent", 2000),
            cell("Classifies the question into a business domain (Partners / Policies / Claims / Payments / …) using semantic search over the vector index.", 6760) ]}),
          new TableRow({ children: [
            cell("3", 600, { fill: "EAF1F8" }),
            cell("Table Agent", 2000),
            cell("Selects candidate ClickHouse tables within the domain; presents them to the user for confirmation or edit.", 6760) ]}),
          new TableRow({ children: [
            cell("4", 600, { fill: "EAF1F8" }),
            cell("Live schema fetch", 2000),
            cell("Calls OpenMetadata API for the current, complete schema of confirmed tables. No cached schema is used for SQL.", 6760) ]}),
          new TableRow({ children: [
            cell("5", 600, { fill: "EAF1F8" }),
            cell("Column Prune Agent", 2000),
            cell("Removes irrelevant columns from the fetched schema, reducing token usage and improving accuracy.", 6760) ]}),
          new TableRow({ children: [
            cell("6", 600, { fill: "EAF1F8" }),
            cell("SQL Generator", 2000),
            cell("Produces ClickHouse-dialect SQL plus a plain-English explanation. Receives question + pruned schema + relevant examples + business definitions.", 6760) ]}),
          new TableRow({ children: [
            cell("7", 600, { fill: "EAF1F8" }),
            cell("Guardrails", 2000),
            cell("Parses SQL, blocks anything other than SELECT, enforces row LIMIT and timeout. Logs the query.", 6760) ]}),
          new TableRow({ children: [
            cell("8", 600, { fill: "EAF1F8" }),
            cell("Executor", 2000),
            cell("Calls the existing clickhouse_query_run endpoint over HTTP and retrieves rows.", 6760) ]}),
          new TableRow({ children: [
            cell("9", 600, { fill: "EAF1F8" }),
            cell("Result Formatter", 2000),
            cell("Renders results as a table with an optional auto-chart and a plain-English summary.", 6760) ]}),
          new TableRow({ children: [
            cell("10", 600, { fill: "EAF1F8" }),
            cell("Chat correction", 2000),
            cell("If the result is wrong, the user can refine in-place (“no, last month”) and the pipeline re-runs with that context.", 6760) ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 5. TECH STACK
      h1("5. Technology Stack"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 2400, 4760],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Layer", 2200), headerCell("Technology", 2400), headerCell("Notes", 4760) ]}),
          new TableRow({ children: [
            cell("Frontend", 2200, { fill: "EAF1F8" }),
            cell("Streamlit", 2400),
            cell("Chat UI, table view, simple auto-charts. Right tool for a low-traffic internal product. Can be replaced with React later.", 4760) ]}),
          new TableRow({ children: [
            cell("Backend", 2200, { fill: "EAF1F8" }),
            cell("Python 3.11 + FastAPI", 2400),
            cell("Hosts the pipeline. REST endpoints for the frontend. Async I/O for parallel agent calls.", 4760) ]}),
          new TableRow({ children: [
            cell("LLM (all agents)", 2200, { fill: "EAF1F8" }),
            cell("Claude (Anthropic API)", 2400),
            cell("Same model, different prompts per agent. Large context window covers ClickHouse schemas. Per-call cost monitored.", 4760) ]}),
          new TableRow({ children: [
            cell("RAG framework", 2200, { fill: "EAF1F8" }),
            cell("Vanna.ai", 2400),
            cell("Manages the vector index, example pairs, and business definitions. Custom schema-fetcher plugged in for OpenMetadata live calls.", 4760) ]}),
          new TableRow({ children: [
            cell("Vector database", 2200, { fill: "EAF1F8" }),
            cell("Chroma (local) or pgvector", 2400),
            cell("Stores only table-name + 1-line summary embeddings, plus example Q→SQL embeddings.", 4760) ]}),
          new TableRow({ children: [
            cell("Source of truth (schema)", 2200, { fill: "EAF1F8" }),
            cell("OpenMetadata (existing)", 2400),
            cell("Live API call at SQL-generation time. Nightly sync feeds the lightweight vector index.", 4760) ]}),
          new TableRow({ children: [
            cell("SQL safety parsing", 2200, { fill: "EAF1F8" }),
            cell("sqlglot", 2400),
            cell("Parses the generated SQL to confirm it is a single SELECT with no destructive statements.", 4760) ]}),
          new TableRow({ children: [
            cell("Database", 2200, { fill: "EAF1F8" }),
            cell("ClickHouse (existing)", 2400),
            cell("Turtlemint’s production data warehouse. No changes required.", 4760) ]}),
          new TableRow({ children: [
            cell("Execution endpoint", 2200, { fill: "EAF1F8" }),
            cell("clickhouse_query_run (existing) or read-only client", 2400),
            cell("Subject to confirmation that the endpoint is read-only and authenticated; fallback is a direct ClickHouse client with read-only credentials.", 4760) ]}),
          new TableRow({ children: [
            cell("Audit log", 2200, { fill: "EAF1F8" }),
            cell("PostgreSQL or a ClickHouse table", 2400),
            cell("One row per question: user, raw question, generated SQL, latency, success flag, row count, error if any.", 4760) ]}),
          new TableRow({ children: [
            cell("Deployment", 2200, { fill: "EAF1F8" }),
            cell("Docker + internal VM/Kubernetes", 2400),
            cell("Aligned with Turtlemint’s standard internal-tool deployment pattern (to confirm with platform team).", 4760) ]}),
          new TableRow({ children: [
            cell("Secrets management", 2200, { fill: "EAF1F8" }),
            cell("Per Turtlemint standard (Vault / env)", 2400),
            cell("Anthropic API key, OpenMetadata credentials, DB credentials. Never committed to code.", 4760) ]}),
          new TableRow({ children: [
            cell("Monitoring", 2200, { fill: "EAF1F8" }),
            cell("Existing Turtlemint logging/metrics", 2400),
            cell("Per-stage latency, error rates, daily active users, accuracy score from golden-set runs.", 4760) ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 6. PHASED WORK PLAN
      h1("6. Phased Work Plan"),
      p("The project runs over 5 weeks across four phases. Each phase ends with a demo and explicit acceptance criteria. No phase begins before its predecessor passes acceptance."),

      h2("6.1 Phase 0 — Pre-build (Days 1–3)"),
      h3("Goals"),
      bullet("Confirm prerequisites with Turtlemint teams (engineering, data, platform)."),
      bullet("Source initial training material from business users."),
      h3("Tasks"),
      numbered("Get confirmation that clickhouse_query_run is read-only and authenticated; obtain credentials. If not safe, set up a read-only ClickHouse user instead."),
      numbered("Get OpenMetadata API access and credentials. Confirm endpoints for table list and table-schema-by-name."),
      numbered("Identify one target business team for the pilot (recommended: Operations) and a primary stakeholder."),
      numbered("Collect 20–30 real questions that team asks today, with the SQL an analyst would write for each."),
      numbered("Define 4–6 business domains for the Intent Agent (e.g., Partners, Policies, Claims, Payments, Commissions, Operations)."),
      numbered("Lock initial business definitions (≥ 15) with the data team — what “active partner”, “signed up”, “lapsed policy”, etc. mean in SQL."),
      h3("Deliverables"),
      bullet("Confirmed access list and credentials (stored in secrets manager)."),
      bullet("Initial golden Q→SQL set (≥ 20 pairs)."),
      bullet("Domain definitions document."),
      bullet("Business definitions document."),

      h2("6.2 Phase 1 — Spine (Week 1)"),
      h3("Goals"),
      bullet("Prove end-to-end that a question can yield correct ClickHouse SQL and a result."),
      h3("Tasks"),
      numbered("Scaffold FastAPI backend with one endpoint: POST /ask {question} → {sql, rows}."),
      numbered("Implement SQL Generator stage only (single Claude call) with full schema passed in-prompt for a small subset of 3–5 tables."),
      numbered("Implement Guardrails (sqlglot parse, SELECT-only, LIMIT, timeout)."),
      numbered("Implement Executor that calls clickhouse_query_run (or read-only client)."),
      numbered("Wire a minimal Streamlit UI: text box, send button, result table."),
      numbered("Implement basic audit logging."),
      h3("Deliverables"),
      bullet("Running prototype that answers 5 hand-picked questions correctly."),
      bullet("Audit table populated."),
      h3("Acceptance criteria"),
      bullet("5/5 hand-picked questions return correct results."),
      bullet("Any non-SELECT input is blocked by guardrails (verified by test)."),

      h2("6.3 Phase 2 — Knowledge base (Week 2)"),
      h3("Goals"),
      bullet("Add the RAG knowledge layer for accuracy and grounding."),
      h3("Tasks"),
      numbered("Stand up Chroma (vector DB)."),
      numbered("Integrate Vanna.ai; load the curated Q→SQL pairs and business definitions."),
      numbered("Build the OpenMetadata sync job (nightly cron): pull table list and one-line descriptions, embed into the vector index."),
      numbered("Add the live OpenMetadata schema-fetch step inside the SQL Generator."),
      numbered("Expand initial table coverage."),
      h3("Deliverables"),
      bullet("Working RAG pipeline with live OpenMetadata schema fetch."),
      bullet("Nightly sync job in production with monitoring."),
      h3("Acceptance criteria"),
      bullet("Golden-set execution accuracy ≥ 70%."),
      bullet("Schema fetched live in <500ms p95."),

      h2("6.4 Phase 3 — Agent pipeline (Weeks 3–4)"),
      h3("Goals"),
      bullet("Decompose the monolithic call into specialised agents (the QueryGPT pattern)."),
      h3("Tasks"),
      numbered("Implement the Prompt Enhancer stage."),
      numbered("Implement the Intent Agent (domain classification)."),
      numbered("Implement the Table Agent with the user-confirmation UI step."),
      numbered("Implement the Column Prune Agent."),
      numbered("Implement the Result Formatter with plain-English summary and one auto-chart."),
      numbered("Implement chat-mode refinement (in-thread corrections)."),
      numbered("Build the golden evaluation harness (Vanilla and Decoupled flows; intent accuracy, table overlap, exec success, similarity)."),
      h3("Deliverables"),
      bullet("Full agent pipeline live."),
      bullet("Evaluation harness producing scores per pull request."),
      h3("Acceptance criteria"),
      bullet("Golden-set execution accuracy ≥ 85%."),
      bullet("Intent classification ≥ 85%."),
      bullet("User-confirmation step active for every multi-table query."),

      h2("6.5 Phase 4 — Harden and pilot (Week 5)"),
      h3("Goals"),
      bullet("Make the tool safe, observable, and ready for the pilot team."),
      h3("Tasks"),
      numbered("Complete audit log fields and a simple internal admin view."),
      numbered("Add per-user rate limits and per-query cost ceiling."),
      numbered("Implement the SQL preview UI step (\"Run\" requires explicit click)."),
      numbered("Write user-facing onboarding doc and a 5-minute walkthrough video."),
      numbered("Run a private beta with 5 users from the pilot team."),
      numbered("Triage feedback, fix high-impact issues, refresh golden set."),
      h3("Deliverables"),
      bullet("Production-ready pilot release."),
      bullet("Onboarding documentation."),
      bullet("Initial weekly metrics dashboard."),
      h3("Acceptance criteria"),
      bullet("≥ 70% of pilot users report the tool is faster than the analyst queue."),
      bullet("Zero destructive-query incidents."),
      bullet("≤ 5% production error rate (queries that fail to execute)."),

      new Paragraph({ children: [new PageBreak()] }),

      // 7. TIMELINE
      h1("7. Timeline and Milestones"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [1400, 2000, 5960],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Week", 1400), headerCell("Phase", 2000), headerCell("Milestone", 5960) ]}),
          new TableRow({ children: [
            cell("Week 0", 1400, { fill: "EAF1F8" }),
            cell("Phase 0", 2000),
            cell("Access confirmed, golden Q→SQL set drafted, domains and definitions locked.", 5960) ]}),
          new TableRow({ children: [
            cell("Week 1", 1400, { fill: "EAF1F8" }),
            cell("Phase 1", 2000),
            cell("End-to-end spine: 5 hand-picked questions answered correctly via Streamlit UI.", 5960) ]}),
          new TableRow({ children: [
            cell("Week 2", 1400, { fill: "EAF1F8" }),
            cell("Phase 2", 2000),
            cell("Knowledge base live; live OpenMetadata fetch wired; ≥ 70% golden-set accuracy.", 5960) ]}),
          new TableRow({ children: [
            cell("Weeks 3–4", 1400, { fill: "EAF1F8" }),
            cell("Phase 3", 2000),
            cell("Full agent pipeline (Intent, Table-with-confirm, Prune); evaluation harness; ≥ 85% accuracy.", 5960) ]}),
          new TableRow({ children: [
            cell("Week 5", 1400, { fill: "EAF1F8" }),
            cell("Phase 4", 2000),
            cell("Pilot release to 5 Operations users; onboarding doc; metrics dashboard.", 5960) ]}),
          new TableRow({ children: [
            cell("Week 6+", 1400, { fill: "EAF1F8" }),
            cell("Iteration", 2000),
            cell("Weekly cadence: triage user issues, grow golden set, expand domain coverage, increase pilot size.", 5960) ]}),
        ],
      }),

      // 8. ROLES & RESPONSIBILITIES
      h1("8. Roles and Responsibilities"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Role", 2400), headerCell("Responsibilities", 6960) ]}),
          new TableRow({ children: [
            cell("Product Manager (you)", 2400, { fill: "EAF1F8" }),
            cell("End-to-end project ownership; stakeholder alignment; golden Q→SQL set curation; business definitions lock-in; domain identification; pilot user recruitment; success-metric tracking; risk escalation.", 6960) ]}),
          new TableRow({ children: [
            cell("Engineering lead", 2400, { fill: "EAF1F8" }),
            cell("Architectural decisions; code review; deployment standards; on-call ownership post-launch.", 6960) ]}),
          new TableRow({ children: [
            cell("Backend engineer(s)", 2400, { fill: "EAF1F8" }),
            cell("Implement pipeline stages, agents, guardrails, executor, OpenMetadata client, audit log.", 6960) ]}),
          new TableRow({ children: [
            cell("Frontend engineer", 2400, { fill: "EAF1F8" }),
            cell("Streamlit UI: chat, table preview, confirmation step, result rendering, chart toggle.", 6960) ]}),
          new TableRow({ children: [
            cell("Data team", 2400, { fill: "EAF1F8" }),
            cell("Source of truth for business definitions; validates golden SQL; advises on ClickHouse dialect quirks; owns OpenMetadata.", 6960) ]}),
          new TableRow({ children: [
            cell("Security / Data Governance", 2400, { fill: "EAF1F8" }),
            cell("Approves read-only credentials approach; reviews PII exposure; signs off on audit log retention policy.", 6960) ]}),
          new TableRow({ children: [
            cell("Platform / DevOps", 2400, { fill: "EAF1F8" }),
            cell("Deployment infrastructure, secrets, logging, monitoring hooks.", 6960) ]}),
          new TableRow({ children: [
            cell("Pilot users (Operations)", 2400, { fill: "EAF1F8" }),
            cell("Use the tool in real workflows; provide weekly feedback; suggest new questions for the golden set.", 6960) ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 9. DEPENDENCIES / PREREQUISITES
      h1("9. Dependencies and Prerequisites"),
      p("These items must be unblocked before the corresponding phase can start. PM (you) drives the conversation for each."),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [4000, 1800, 3560],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Dependency", 4000), headerCell("Needed by", 1800), headerCell("Owner / contact", 3560) ]}),
          new TableRow({ children: [
            cell("Confirmation that clickhouse_query_run is read-only and authenticated; otherwise provision a read-only ClickHouse user.", 4000, { fill: "EAF1F8" }),
            cell("Phase 1", 1800), cell("Engineering / Data team", 3560) ]}),
          new TableRow({ children: [
            cell("OpenMetadata API access and credentials, including endpoints for table list and table-schema-by-name.", 4000, { fill: "EAF1F8" }),
            cell("Phase 2", 1800), cell("Data team", 3560) ]}),
          new TableRow({ children: [
            cell("Anthropic API account and key (with reasonable monthly quota).", 4000, { fill: "EAF1F8" }),
            cell("Phase 1", 1800), cell("Platform / Procurement", 3560) ]}),
          new TableRow({ children: [
            cell("Approved deployment target (VM, Kubernetes, or internal PaaS).", 4000, { fill: "EAF1F8" }),
            cell("Phase 4", 1800), cell("Platform / DevOps", 3560) ]}),
          new TableRow({ children: [
            cell("Pilot team identified and a primary point of contact assigned.", 4000, { fill: "EAF1F8" }),
            cell("Phase 0", 1800), cell("PM + Business head", 3560) ]}),
          new TableRow({ children: [
            cell("Golden Q→SQL pairs (≥ 20) signed off by Data team.", 4000, { fill: "EAF1F8" }),
            cell("Phase 2", 1800), cell("PM + Data team", 3560) ]}),
          new TableRow({ children: [
            cell("Business definitions document (≥ 15) signed off.", 4000, { fill: "EAF1F8" }),
            cell("Phase 2", 1800), cell("PM + Business stakeholders + Data team", 3560) ]}),
          new TableRow({ children: [
            cell("Data Governance sign-off on audit log contents and retention.", 4000, { fill: "EAF1F8" }),
            cell("Phase 4", 1800), cell("Security / Data Governance", 3560) ]}),
        ],
      }),

      // 10. ASSUMPTIONS
      h1("10. Assumptions"),
      bullet("Turtlemint already operates a ClickHouse data warehouse and OpenMetadata catalog in production."),
      bullet("The clickhouse_query_run endpoint will be made available for tool use, or a read-only equivalent will be provisioned."),
      bullet("Anthropic API is approved for internal use; data sent to it consists only of: the user’s question, the lightweight schema, and the curated examples — never customer/PII data values."),
      bullet("Pilot users are willing to confirm SQL preview before running queries during the MVP phase."),
      bullet("Schema changes in OpenMetadata are documented in column descriptions sufficiently for an LLM to use them."),
      bullet("Business definitions can be aligned within Phase 0 (the project will be blocked if domain owners cannot agree)."),

      // 11. RISKS
      h1("11. Risks and Mitigations"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2800, 1000, 1000, 4560],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Risk", 2800), headerCell("Likelihood", 1000), headerCell("Impact", 1000), headerCell("Mitigation", 4560) ]}),
          new TableRow({ children: [
            cell("LLM hallucinates non-existent tables/columns.", 2800, { fill: "EAF1F8" }),
            cell("High", 1000), cell("High", 1000),
            cell("Live OpenMetadata fetch; SQL parser validation; column-existence check before execution; user confirmation; chat refinement.", 4560) ]}),
          new TableRow({ children: [
            cell("Subtly wrong SQL returns wrong numbers users trust.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("Critical", 1000),
            cell("Mandatory SQL preview; plain-English explanation; growing golden set; pilot with engaged users who can spot regressions.", 4560) ]}),
          new TableRow({ children: [
            cell("Destructive query reaches the database.", 2800, { fill: "EAF1F8" }),
            cell("Low", 1000), cell("Critical", 1000),
            cell("Read-only DB user (physical safety); SELECT-only parser check (logical safety); execution endpoint reviewed for safety.", 4560) ]}),
          new TableRow({ children: [
            cell("OpenMetadata API too slow or unreliable.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("Medium", 1000),
            cell("Short-lived in-process cache per request; circuit breaker; fall back to last good schema with a warning banner.", 4560) ]}),
          new TableRow({ children: [
            cell("Cost runaway from LLM usage.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("Medium", 1000),
            cell("Per-user daily token budget; cap on agent chain length; Column Prune Agent to shrink context; cached agent outputs where safe.", 4560) ]}),
          new TableRow({ children: [
            cell("Schema drift makes vector index stale.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("Low", 1000),
            cell("By design, the index is only used for table discovery, never for SQL generation. Stale index causes a wrong-table suggestion the user catches in the confirm step — not wrong SQL.", 4560) ]}),
          new TableRow({ children: [
            cell("Business definitions disputed across teams.", 2800, { fill: "EAF1F8" }),
            cell("High", 1000), cell("High", 1000),
            cell("Phase 0 alignment exercise; conservative defaults documented and visible in the tool when a definition is used.", 4560) ]}),
          new TableRow({ children: [
            cell("Sensitive data exposure to a third-party API.", 2800, { fill: "EAF1F8" }),
            cell("Low", 1000), cell("Critical", 1000),
            cell("Only the question text and schema metadata are sent to Anthropic — never row data. Confirm with Security before launch.", 4560) ]}),
          new TableRow({ children: [
            cell("Scope creep into write-capable features.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("High", 1000),
            cell("Explicit out-of-scope list; SOW change-control required for any deviation.", 4560) ]}),
          new TableRow({ children: [
            cell("Pilot users disengage; no feedback loop.", 2800, { fill: "EAF1F8" }),
            cell("Medium", 1000), cell("Medium", 1000),
            cell("PM owns weekly check-ins with each pilot user; rapid issue triage; visible roadmap of fixes.", 4560) ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 12. SAFETY & GOVERNANCE
      h1("12. Safety, Security and Governance"),
      h2("12.1 Data flow boundaries"),
      bullet("Anthropic API receives only: the user’s question, table/column names and descriptions, business definitions, and curated example SQL. It never receives row-level data from ClickHouse."),
      bullet("ClickHouse receives only generated SQL via the existing endpoint, executed under a read-only credential."),
      bullet("OpenMetadata is read-only — the tool never modifies catalog entries."),

      h2("12.2 Guardrail summary"),
      numbered("Read-only database credential (physical control)."),
      numbered("SQL parser allows only SELECT (logical control)."),
      numbered("Automatic LIMIT (default 1000) appended if absent."),
      numbered("Query timeout (default 30 seconds)."),
      numbered("Mandatory SQL preview before execution for the user."),
      numbered("Plain-English explanation rendered alongside the SQL."),
      numbered("Audit log row per question with full traceability."),
      numbered("Per-user and per-day query cap to bound cost and abuse."),

      h2("12.3 Audit log fields"),
      bullet("timestamp, user_id, raw_question, enhanced_question"),
      bullet("intent, candidate_tables, confirmed_tables"),
      bullet("generated_sql, executed_sql (post-guardrail), success_flag"),
      bullet("row_count, error_message, latency_ms, agent_token_usage"),
      bullet("client_ip, session_id"),

      h2("12.4 Retention and access"),
      bullet("Audit log retention: 90 days hot, 1 year cold (subject to Security sign-off)."),
      bullet("Audit log access restricted to PM, engineering lead, and Security."),
      bullet("No PII written to the audit log beyond user_id (no row data, no extracted personal info)."),

      // 13. OPEN DECISIONS
      h1("13. Open Decisions and Questions"),
      p("These must be answered before or during Phase 0."),
      numbered("Is the existing clickhouse_query_run endpoint read-only and authenticated? If not, can a read-only equivalent be provisioned for this tool?"),
      numbered("Does Turtlemint’s OpenMetadata expose tables and full schema via REST API? What are the endpoints and authentication mechanism?"),
      numbered("Does the OpenMetadata setup emit change webhooks, or will we sync via polling?"),
      numbered("Is Anthropic API approved for internal use? If not, what is the approval process?"),
      numbered("Which business team runs the pilot, and who is the primary stakeholder?"),
      numbered("What are the canonical business definitions for the top 15 disputed terms (active partner, lapsed policy, settled claim, …)?"),
      numbered("Is the lightweight vector index (table names + 1-line summaries on our side) acceptable under governance, or must we use OpenMetadata’s own search?"),
      numbered("What is the deployment target (existing internal PaaS / Kubernetes / VM)?"),
      numbered("Are existing logging and monitoring stacks reusable for this tool?"),
      numbered("What is the budget ceiling for LLM API usage (monthly)?"),

      // 14. EFFORT ESTIMATE
      h1("14. Effort Estimate"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [3200, 2000, 4160],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Role", 3200), headerCell("Allocation", 2000), headerCell("Duration", 4160) ]}),
          new TableRow({ children: [
            cell("Product Manager (you)", 3200, { fill: "EAF1F8" }),
            cell("~60% FTE", 2000), cell("Weeks 0–5 + ongoing", 4160) ]}),
          new TableRow({ children: [
            cell("Backend engineer (lead)", 3200, { fill: "EAF1F8" }),
            cell("100% FTE", 2000), cell("Weeks 1–5", 4160) ]}),
          new TableRow({ children: [
            cell("Backend engineer (support)", 3200, { fill: "EAF1F8" }),
            cell("50% FTE", 2000), cell("Weeks 2–4", 4160) ]}),
          new TableRow({ children: [
            cell("Frontend engineer (Streamlit)", 3200, { fill: "EAF1F8" }),
            cell("30% FTE", 2000), cell("Weeks 1–4", 4160) ]}),
          new TableRow({ children: [
            cell("Data team partner", 3200, { fill: "EAF1F8" }),
            cell("~20% FTE", 2000), cell("Weeks 0–5", 4160) ]}),
          new TableRow({ children: [
            cell("Security review", 3200, { fill: "EAF1F8" }),
            cell("Time-boxed", 2000), cell("Week 4–5 (one cycle)", 4160) ]}),
          new TableRow({ children: [
            cell("Platform / DevOps", 3200, { fill: "EAF1F8" }),
            cell("Time-boxed", 2000), cell("Week 4 (deployment)", 4160) ]}),
        ],
      }),
      p("LLM API budget: order-of-magnitude estimate at ≈ $0.05–$0.20 per question end-to-end (multi-agent calls). 5 pilot users × ~20 questions/day = ~$5–$20/day during pilot. To be re-estimated after Phase 2 measurements."),

      // 15. COMMUNICATION
      h1("15. Communication and Reporting"),
      bullet("Weekly status note (PM → stakeholders): progress vs. milestone, blockers, accuracy metrics, top user-reported issues."),
      bullet("End-of-phase demo: live walkthrough with the pilot team and data team."),
      bullet("Daily standup (engineering only) during build phases."),
      bullet("Pilot office hours (weekly) once Phase 4 is live."),
      bullet("Incident process: any wrong-answer incident raised by a pilot user is triaged within 1 business day; root cause and fix logged."),

      // 16. ACCEPTANCE & EXIT
      h1("16. Project Acceptance"),
      p("The project is considered delivered when all of the following hold:"),
      numbered("All Phase 4 acceptance criteria are met."),
      numbered("Pilot has run for at least two weeks with ≥ 5 active users."),
      numbered("Audit log shows zero destructive-query incidents."),
      numbered("≥ 70% of pilot users self-report the tool as faster than the analyst queue (survey)."),
      numbered("A documented backlog for the next phase exists (broader rollout, more domains, advanced charts)."),

      new Paragraph({ children: [new PageBreak()] }),

      // 17. GLOSSARY
      h1("17. Glossary"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Term", 2400), headerCell("Meaning", 6960) ]}),
          new TableRow({ children: [
            cell("SQL", 2400, { fill: "EAF1F8" }),
            cell("Structured Query Language — the language used to read/write data in a relational database. The tool hides this from users.", 6960) ]}),
          new TableRow({ children: [
            cell("ClickHouse", 2400, { fill: "EAF1F8" }),
            cell("Turtlemint’s analytics database. SQL dialect is mostly standard with a few syntax differences.", 6960) ]}),
          new TableRow({ children: [
            cell("OpenMetadata", 2400, { fill: "EAF1F8" }),
            cell("Turtlemint’s data catalog — the source of truth for tables, columns, descriptions, and lineage.", 6960) ]}),
          new TableRow({ children: [
            cell("LLM", 2400, { fill: "EAF1F8" }),
            cell("Large Language Model. Claude (Anthropic) is used as the brain for all agents.", 6960) ]}),
          new TableRow({ children: [
            cell("Agent", 2400, { fill: "EAF1F8" }),
            cell("A single LLM call assigned one narrow task (e.g., classify intent). The system uses several agents in sequence.", 6960) ]}),
          new TableRow({ children: [
            cell("RAG", 2400, { fill: "EAF1F8" }),
            cell("Retrieval-Augmented Generation. Fetching relevant notes (schema/examples) and giving them to the LLM with the question.", 6960) ]}),
          new TableRow({ children: [
            cell("Vector database", 2400, { fill: "EAF1F8" }),
            cell("A database that searches by meaning. Stores embeddings of text so the system can find “related” items, not just exact matches.", 6960) ]}),
          new TableRow({ children: [
            cell("Guardrails", 2400, { fill: "EAF1F8" }),
            cell("Code-based safety checks between LLM output and the database (SELECT-only, LIMIT, timeout, preview).", 6960) ]}),
          new TableRow({ children: [
            cell("Golden set", 2400, { fill: "EAF1F8" }),
            cell("A maintained list of real questions with their verified correct SQL. Used to score every change to the system.", 6960) ]}),
          new TableRow({ children: [
            cell("Vanna.ai", 2400, { fill: "EAF1F8" }),
            cell("Open-source library that wraps the RAG pattern for text-to-SQL — manages examples, vector store, and prompt construction.", 6960) ]}),
          new TableRow({ children: [
            cell("sqlglot", 2400, { fill: "EAF1F8" }),
            cell("Python library that parses SQL — used to confirm the generated query is a single safe SELECT.", 6960) ]}),
          new TableRow({ children: [
            cell("Streamlit", 2400, { fill: "EAF1F8" }),
            cell("Python framework for fast internal-tool web UIs.", 6960) ]}),
          new TableRow({ children: [
            cell("FastAPI", 2400, { fill: "EAF1F8" }),
            cell("Python web framework used for the backend service.", 6960) ]}),
        ],
      }),

      // 18. APPENDIX
      h1("18. Appendix A — Reference: Uber QueryGPT"),
      p("Uber published their text-to-SQL system, QueryGPT, in 2024. The system processes ≈ 1.2 million queries per month and reduced query authoring time from ≈ 10 minutes to ≈ 3 minutes; 78% of users in early adoption reported a productivity gain. The key public lessons we adopt:"),
      bullet("A single end-to-end LLM call is not enough — break the task into specialised agents."),
      bullet("Adding an Intent layer (workspace classification) was the largest single accuracy gain over the original simple-RAG version."),
      bullet("Human-in-the-loop confirmation at table selection is essential."),
      bullet("Trimming irrelevant columns before SQL generation improves accuracy and cost."),
      bullet("A golden-set evaluation framework with Vanilla and Decoupled flows is the only reliable way to know whether changes improve or regress the system."),
      bullet("Hallucinations never fully disappear; validation agents and chat-mode corrections are continuous mitigations, not one-time fixes."),

      h1("Appendix B — Decision Log"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [1200, 4080, 4080],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Date", 1200), headerCell("Decision", 4080), headerCell("Rationale", 4080) ]}),
          new TableRow({ children: [
            cell("2026-05-18", 1200, { fill: "EAF1F8" }),
            cell("Adopt RAG + multi-agent architecture (QueryGPT-style).", 4080),
            cell("Single-call LLM-to-SQL hallucinates at scale; agent decomposition is the proven fix.", 4080) ]}),
          new TableRow({ children: [
            cell("2026-05-19", 1200, { fill: "EAF1F8" }),
            cell("Use Claude as the model for all agents.", 4080),
            cell("Strong SQL reasoning, large context window, single-vendor simplicity.", 4080) ]}),
          new TableRow({ children: [
            cell("2026-05-20", 1200, { fill: "EAF1F8" }),
            cell("Hybrid schema strategy: lightweight vector index for discovery + live OpenMetadata fetch for SQL.", 4080),
            cell("Avoids the staleness risk of a stored schema copy while preserving semantic-search discovery.", 4080) ]}),
          new TableRow({ children: [
            cell("2026-05-20", 1200, { fill: "EAF1F8" }),
            cell("Pilot scope = one team (Operations).", 4080),
            cell("Narrow audience leads to consistent question patterns and a faster path to trust (Uber lesson).", 4080) ]}),
        ],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("F:\\Natural Language SQL Query\\NL-SQL-SOW.docx", buffer);
  console.log("written");
});

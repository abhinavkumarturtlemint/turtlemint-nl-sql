const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, TableOfContents, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageBreak, PageNumber,
  Header, Footer
} = require("docx");

const CONTENT_WIDTH = 9360; // US Letter, 1" margins

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 300 },
    children: [new TextRun({ text, ...opts })],
  });
}

function rich(runs, spacingAfter = 120) {
  return new Paragraph({
    spacing: { after: spacingAfter, line: 300 },
    children: runs.map(r => new TextRun(r)),
  });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}

function bullet(text, boldLead) {
  const children = [];
  if (boldLead) {
    children.push(new TextRun({ text: boldLead + " ", bold: true }));
  }
  children.push(new TextRun(text));
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 290 },
    children,
  });
}

function numbered(text, boldLead) {
  const children = [];
  if (boldLead) children.push(new TextRun({ text: boldLead + " ", bold: true }));
  children.push(new TextRun(text));
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 80, line: 290 },
    children,
  });
}

function headerCell(text, w) {
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: cellMargins,
    shading: { fill: "2E75B6", type: ShadingType.CLEAR },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF" })] })],
  });
}
function cell(text, w, opts = {}) {
  const runs = Array.isArray(text)
    ? text.map(t => new TextRun(t))
    : [new TextRun(text)];
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ children: runs })],
  });
}

const doc = new Document({
  creator: "Claude",
  title: "Natural Language SQL Query Processor — Explained Simply",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal",
        run: { size: 48, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { after: 120 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
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
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun("Natural Language SQL Query Processor  |  Page "),
          new TextRun({ children: [PageNumber.CURRENT] }),
        ],
      })] }),
    },
    children: [
      new Paragraph({ style: "Title", spacing: { before: 2400, after: 120 },
        children: [new TextRun("Natural Language SQL")] }),
      new Paragraph({ style: "Title", spacing: { after: 240 },
        children: [new TextRun("Query Processor")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "Letting business people ask questions in plain English instead of writing SQL", italics: true, size: 24, color: "595959" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2000 },
        children: [new TextRun({ text: "A simple, end-to-end explanation", size: 22, color: "595959" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 },
        children: [new TextRun({ text: "Prepared 18 May 2026", size: 20, color: "808080" })] }),

      new Paragraph({ children: [new PageBreak()] }),

      h1("Contents"),
      new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new PageBreak()] }),

      // 1. THE PROBLEM
      h1("1. The Problem We Are Solving"),
      p("Business people often need answers that live inside a company's database — things like “how many partners signed up last month” or “which region brought the most revenue”. The data is right there, but to get it out you normally have to write SQL, a technical query language."),
      p("SQL is not their forte. So today they either learn a hard skill they don’t want, or they wait in a queue for an analyst to pull the number for them. Both are slow and frustrating."),
      rich([
        { text: "The goal: ", bold: true },
        { text: "let a business user type a question in plain English and get the answer back — no SQL, no waiting on an analyst." },
      ]),

      // 2. THE BIG PICTURE
      h1("2. The Big Picture (in one idea)"),
      p("We are building a translator that sits between a business person and the database. They ask in English; it figures out the SQL, runs it safely, and shows a clean answer."),
      h2("A simple analogy: the restaurant"),
      p("Think of a restaurant. The system has the same parts:"),
      bullet("orders in plain English. They do not need to know how the kitchen works.", "The customer (the business user)"),
      bullet("takes the order and coordinates everything.", "The waiter (your app)"),
      bullet("turns the order into a recipe — here, the English question into SQL.", "The kitchen (the AI model)"),
      bullet("checks nothing harmful goes out.", "The food-safety inspector (guardrails)"),
      bullet("holds the ingredients — the actual data.", "The pantry (the database)"),
      p("The customer never sees the kitchen. They just get a well-presented dish — a clear answer."),

      // 3. JOURNEY OF ONE QUESTION
      h1("3. How It Works: The Journey of One Question"),
      p("Every natural-language-to-SQL tool, no matter how fancy, is just these seven steps. We will follow one real question all the way through:"),
      rich([{ text: "“How many partners signed up last month?”", italics: true, bold: true }], 200),

      numbered("The user types the question into a simple web page. No SQL, no jargon.", "Ask —"),
      numbered("The web page sends the question to your server over the internet (an HTTP request — the same thing the cURL command does by hand).", "Send —"),
      numbered("Your server does not just forward the question. It attaches context: the database’s table names, columns, and your business definitions (for example, “a partner lives in the spectrum.partner table” and “signed up means the created date”). This bundle is called the prompt.", "Add context —"),
      numbered("The server sends the prompt to the AI model. It reads the question plus the context and writes the SQL, for example: SELECT count(*) FROM spectrum.partner WHERE created_at >= '2026-04-01' AND created_at < '2026-05-01'.", "AI writes SQL —"),
      numbered("Before anything runs, your server checks the SQL: Is it only reading data? Is it trying to delete or change anything? It adds a safety row limit. Only safe queries pass.", "Guardrails check —"),
      numbered("The approved SQL runs on the database (ClickHouse, at Turtlemint). The database returns the raw result, e.g. { count: 1428 }.", "Run —"),
      numbered("The server turns the raw result into something human — a clear number, a table, or a chart — and optionally a one-line plain-English summary: “1,428 partners signed up last month.”", "Answer —"),
      p("That is the entire system. Everything else is just making each step more accurate, safer, or nicer to look at."),

      new Paragraph({ children: [new PageBreak()] }),

      // 4. TECH STACK
      h1("4. The Technology Stack (what we use and why)"),
      p("Each part below maps to one layer of the system. The choices favour the fastest path to something that works, with every piece swappable later."),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [1900, 2400, 5060],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Layer", 1900),
            headerCell("Technology", 2400),
            headerCell("Why this one (in plain words)", 5060),
          ]}),
          new TableRow({ children: [
            cell("Frontend (what the user sees)", 1900, { fill: "EAF1F8" }),
            cell("Streamlit", 2400),
            cell("A Python tool that turns a few dozen lines of code into a working chat-style web page. For an internal tool used by a few people, a heavy custom website would be wasted effort.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Backend (the coordinator)", 1900, { fill: "EAF1F8" }),
            cell("Python + FastAPI", 2400),
            cell("Python because every AI library lives there. FastAPI is a popular, fast way to build the “waiter” that connects the web page, the AI, and the database.", 5060),
          ]}),
          new TableRow({ children: [
            cell("The brain", 1900, { fill: "EAF1F8" }),
            cell("Claude (Anthropic API)", 2400),
            cell("Does the actual English-to-SQL translation. You do not host it; you call it over the internet and pay per use. Strong at SQL and at following the rules you give it.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Accuracy layer", 1900, { fill: "EAF1F8" }),
            cell("Vanna.ai", 2400),
            cell("A library built specifically for English-to-SQL. It stores your schema and example question-and-answer pairs and feeds the right ones to the AI. This is what turns “okay” accuracy into “trustworthy”.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Memory for context", 1900, { fill: "EAF1F8" }),
            cell("Vector database (e.g. Chroma)", 2400),
            cell("Comes with Vanna. Stores your examples and definitions so the system fetches only the relevant ones for each question. Think of it as the system’s notes folder.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Database", 1900, { fill: "EAF1F8" }),
            cell("ClickHouse (already exists at Turtlemint)", 2400),
            cell("You are not building this — it is the company’s data. Your tool just needs to speak its dialect of SQL and know how to send queries to it.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Execution", 1900, { fill: "EAF1F8" }),
            cell("Turtlemint’s clickhouse_query_run endpoint", 2400),
            cell("This actually runs the query. Reusing this existing endpoint means less to build — but the team must confirm it is safe and read-only first.", 5060),
          ]}),
          new TableRow({ children: [
            cell("Safety", 1900, { fill: "EAF1F8" }),
            cell("Your own guardrail code", 2400),
            cell("Not a product you install — it is checks you write: only allow read queries, add row limits, log everything, and preview the SQL to the user.", 5060),
          ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 5. GUARDRAILS
      h1("5. Guardrails: Keeping It Safe"),
      p("Guardrails are the safety checks placed between the AI’s output and the real database, so a wrong or dangerous query never reaches the data. Like guardrails on a mountain road — they do not drive the car, they just stop it going off a cliff."),
      p("The key principle: never trust the AI’s SQL blindly. It can misread a question or, rarely, produce something destructive. These checks catch that before anything runs:"),
      bullet("connect using a database account that can only read. Even if the AI writes a delete command, the database itself refuses it. This is a physical limit, not a check you can forget.", "Read-only database user —"),
      bullet("before running, confirm the query only reads data. Block anything that deletes, drops, updates, or changes data.", "Query type check —"),
      bullet("automatically cap how many rows come back, so “show me everything” cannot freeze the database or run up cost.", "Row and cost limits —"),
      bullet("show the user the generated SQL (and a plain-English restatement) before running, for anything important. Even non-technical users can catch “wait, that’s last year, I wanted last month.”", "Query preview —"),
      bullet("stop any query that runs too long, so one bad query cannot hog the database.", "Timeout —"),
      bullet("record every question, the SQL it produced, who asked, and the result. Not prevention — but essential for understanding anything that goes wrong.", "Audit log —"),
      rich([
        { text: "Why this matters most here: ", bold: true },
        { text: "a business user cannot tell a subtly wrong query from a right one. They will trust whatever number comes back. Guardrails are how you protect them from confidently-wrong answers." },
      ]),

      // 6. THE BUILD PLAN
      h1("6. How It Gets Built: The Plan"),
      p("None of this is research — it is a well-trodden path. A realistic order of work:"),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [1500, 2100, 5760],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Phase", 1500),
            headerCell("Timeframe", 2100),
            headerCell("Goal", 5760),
          ]}),
          new TableRow({ children: [
            cell("1. Prove the brain", 1500, { fill: "EAF1F8" }),
            cell("A few days", 2100),
            cell("No app yet. Just call the AI by hand with one real question plus a real table’s structure. Question: does it produce correct ClickHouse SQL? If yes, the whole idea is validated.", 5760),
          ]}),
          new TableRow({ children: [
            cell("2. Wire the pipeline", 1500, { fill: "EAF1F8" }),
            cell("Week 1", 2100),
            cell("Build the thin version: web page → backend → AI → run query → show table. Ugly but working end to end. One question in, one answer out.", 5760),
          ]}),
          new TableRow({ children: [
            cell("3. Make it accurate", 1500, { fill: "EAF1F8" }),
            cell("Weeks 2–3", 2100),
            cell("Add Vanna plus 20–30 example question-and-SQL pairs and your business definitions. The most valuable phase — accuracy jumps from roughly 60% to around 90%.", 5760),
          ]}),
          new TableRow({ children: [
            cell("4. Make it safe and trusted", 1500, { fill: "EAF1F8" }),
            cell("Week 4", 2100),
            cell("Add all guardrails, show the SQL before running, plain-English explanations, and the audit log. This is what makes business people actually trust it.", 5760),
          ]}),
        ],
      }),

      // 7. PM LENS
      h1("7. What Decides Success (the product view)"),
      p("The engineering above is standard. The parts that decide whether this succeeds are product decisions:"),
      numbered("The accuracy in Phase 3 comes from feeding it the questions business people actually ask. Collecting those is a people task, not an engineering one.", "Get the right example questions —"),
      numbered("What exactly is an “active partner”? “Revenue”? If the organisation disagrees, the tool cannot be right. Driving that alignment is a product job.", "Nail the business definitions —"),
      numbered("Before building, the team must confirm: is the clickhouse_query_run endpoint read-only? Is it authenticated? Is it OK to build on top of? Lead that conversation.", "Confirm the safety story —"),
      numbered("Decide the rule: does every query get previewed? Which questions are safe to auto-run? That is a judgement call about risk versus convenience.", "Set the trust bar —"),
      rich([
        { text: "Bottom line: ", bold: true },
        { text: "the technology is feasible and well understood. Trust is the actual product — not SQL generation. The work that matters most plays to a product manager’s strengths." },
      ]),

      // GLOSSARY
      h1("8. Quick Glossary"),
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 7160],
        rows: [
          new TableRow({ tableHeader: true, children: [
            headerCell("Term", 2200),
            headerCell("Plain meaning", 7160),
          ]}),
          new TableRow({ children: [
            cell("SQL", 2200, { fill: "EAF1F8" }),
            cell("The technical language used to ask a database for data. What we are trying to hide from the user.", 7160),
          ]}),
          new TableRow({ children: [
            cell("LLM / AI model", 2200, { fill: "EAF1F8" }),
            cell("The “brain” (e.g. Claude) that translates English into SQL.", 7160),
          ]}),
          new TableRow({ children: [
            cell("API", 2200, { fill: "EAF1F8" }),
            cell("A way for one program to ask another program for something over the internet.", 7160),
          ]}),
          new TableRow({ children: [
            cell("cURL", 2200, { fill: "EAF1F8" }),
            cell("A command-line tool to call an API by hand — used for testing and reading API docs, not part of the final product.", 7160),
          ]}),
          new TableRow({ children: [
            cell("Schema", 2200, { fill: "EAF1F8" }),
            cell("The structure of the database: its table names, columns, and how they relate.", 7160),
          ]}),
          new TableRow({ children: [
            cell("Prompt", 2200, { fill: "EAF1F8" }),
            cell("The bundle of question plus context that you send to the AI.", 7160),
          ]}),
          new TableRow({ children: [
            cell("Guardrails", 2200, { fill: "EAF1F8" }),
            cell("Safety checks between the AI’s output and the database.", 7160),
          ]}),
          new TableRow({ children: [
            cell("ClickHouse", 2200, { fill: "EAF1F8" }),
            cell("The specific database Turtlemint uses to store data.", 7160),
          ]}),
        ],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("F:\\Natural Language SQL Query\\NL-SQL-Explained.docx", buffer);
  console.log("written");
});

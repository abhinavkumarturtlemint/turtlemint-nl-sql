# Turtlemint NL-SQL — User Guide

A 2-minute guide for business users. No SQL knowledge needed.

## What this tool does

You ask a question about Turtlemint data in plain English; the tool figures out
the query, runs it safely, and shows you the answer — with a plain-English
summary and (when useful) a chart.

> Note: it currently runs on **dummy demo data** (made-up partners, policies,
> claims). The numbers are not real yet — this is for trying out the experience.

## How to use it

1. **Ask** — type a question, or click an example. Examples:
   - *How many partners signed up last month?*
   - *Total premium by product type*
   - *Top 5 partners by number of policies sold*
   - *Which state has the highest health premium?*

2. **Confirm the tables** — the tool shows which data tables it will use and
   why. If it looks wrong, add/remove tables from the dropdown. This is your
   chance to keep it on track.

3. **Review the SQL** — you'll see a plain-English explanation and the query.
   You don't need to read the SQL, but it's there for transparency. Click
   **Run query**.

4. **Read the answer** — you get a summary sentence, a results table, an
   optional chart, and a **Download CSV** button.

5. **Refine** — not quite right? Use the **Refine** box (e.g. *"only last
   month"* or *"break it down by state"*) and the tool re-runs with your tweak.

## Tips for good questions

- Be specific about the time range ("last month", "this year", "in 2025").
- Name what you want to group by ("by state", "by product type", "per partner").
- One question at a time works best.

## What keeps it safe

- It can **only read** data — it can never change or delete anything.
- Every query is **previewed** before it runs, and **logged**.
- Results are **row-limited** so nothing runs away.

## When the answer looks off

- Check the tables it picked (Step 2) — wrong table = wrong answer.
- Read the one-line explanation — does it match what you meant?
- Try rephrasing, or use **Refine**.
- Still wrong? Send the question + what you expected to the project owner so it
  can be added to the quality test set.

## Good to know

- The tool uses AI to write the query, so it can occasionally be wrong on tricky
  questions. The preview + summary are there so you can sanity-check before
  trusting a number.
- There's a daily limit on queries per user (to control cost during the pilot).

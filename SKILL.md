---
name: paper-review
description: Use when the user asks for a peer review, critique, or meta-review of an academic paper (PDF, DOCX, or extracted text). Spawns N independent reviewer subagents in parallel using anonymized NATO codenames, then synthesizes a meta-review identifying common and unique concerns and a CSV concerns table. Adapted from poldrack/ai-peer-review. Triggers on phrases like "peer review this paper", "critique this PDF", "review like a reviewer would", "meta-review", "разбери эту статью как рецензент".
---

# Paper Peer Review

Multi-reviewer peer review of an academic paper. Models the workflow of [poldrack/ai-peer-review](https://github.com/poldrack/ai-peer-review) but uses parallel Claude subagents in place of multiple proprietary LLMs, so it works with no extra API keys.

## Inputs

| Argument | Required | Default | Notes |
|---|---|---|---|
| `paper` | yes | — | Path to a PDF, DOCX, or `.txt`/`.md` of the paper. |
| `domain` | no | inferred | Reviewer field, e.g. `"neuroscience and brain imaging"`. Inferred from the paper's title/abstract if not supplied. |
| `num_reviewers` | no | `5` | Independent reviewers to spawn. Min 3, max 8. |
| `output_dir` | no | `./papers/<paper-stem>/` | Where review artifacts are written. |
| `skip_meta` | no | `false` | If `true`, only individual reviews are produced. |
| `overwrite` | no | `false` | If `false`, reuse any `review_*.md` already present and only run missing reviewers + meta. |

If the user invokes the skill ambiguously, ask only for `paper` — infer the rest.

## Workflow

### 1. Extract paper text

- PDF → use `pypdf` (`python -c "from pypdf import PdfReader; ..."`) or `pdftotext` if available.
- DOCX → use `python-docx` or `pandoc`.
- `.txt`/`.md` → read directly.

If extraction yields fewer than ~1000 characters or text is mostly garbled (common with scanned PDFs), tell the user and stop — OCR is out of scope for this skill.

### 2. Sanity check

Confirm the document looks like an academic paper (abstract, methods/results, references). If not, ask the user to confirm before proceeding.

### 3. Spawn reviewers in parallel — MANDATORY

Issue all `num_reviewers` Agent calls in **one tool-use block** (one assistant message with multiple `Agent` invocations). Sequential review generation defeats the purpose and is much slower.

For each reviewer:
- `subagent_type`: `general-purpose`
- `description`: `"Independent peer review (codename <nato>)"`
- `prompt`: contents of `prompts/reviewer.md` with `{domain}`, `{reviewer_id}`, `{paper_text}` substituted.

NATO codenames in order: `alfa, bravo, charlie, delta, echo, foxtrot, golf, hotel`.

Reviewers must NOT see each other's outputs. Each is a single, independent generation.

### 4. Save individual reviews

Write each subagent's return text to `<output_dir>/review_<nato>.md`. Keep the codename → (nothing, since they are all Claude) mapping trivial — the field exists in `results.json` for compatibility with the original tool.

### 5. Synthesize the meta-review

Do this **in the main thread** (no subagent), so synthesis is grounded in your own context.

- Read each `review_<nato>.md` back from disk (or use the in-memory results).
- Build the prompt from `prompts/metareview.md` with `{reviews_text}` filled in (concatenate `Review from <codename>:\n\n<text>\n\n` for each).
- Generate the meta-review yourself (i.e., output it as text, then `Write` it to disk). Do NOT spawn a subagent for this step — the model needs full context to weigh concerns against the originals.

### 6. Extract the concerns table

The meta-review contains a `CONCERNS_TABLE_DATA` block with JSON. Parse it with a small Python snippet (or `json` + regex), convert to a DataFrame with columns `concern, alfa, bravo, …`, and save as `<output_dir>/concerns_table.csv`.

Strip the `CONCERNS_TABLE_DATA` block out of the saved `meta_review.md` (keep the human-readable part only).

### 7. Save the bundle

Write `<output_dir>/results.json`:

```json
{
  "individual_reviews": { "alfa": "…", "bravo": "…" },
  "meta_review": "…",
  "reviewer_mapping": { "alfa": "claude-subagent-1", "bravo": "claude-subagent-2" }
}
```

## Outputs

```
<output_dir>/
  review_alfa.md
  review_bravo.md
  …
  meta_review.md
  concerns_table.csv
  results.json
```

## Rules

- **Parallelism is mandatory** — one assistant message, N `Agent` calls. Sequential is wrong.
- **Anonymity matters** — when synthesizing, refer to reviewers only by NATO codename. Don't disclose that they're all Claude subagents inside the meta-review prose.
- **Don't soften the criticism.** The meta-review must preserve specific, actionable critiques. If a reviewer recommended "Reject", say so — don't average it into "Major revision" silently.
- **Reuse existing reviews** when `overwrite=false` and `review_<nato>.md` already exists in `output_dir`. Only run the missing reviewers + meta-review.
- **No fabricated citations.** If a reviewer claims a paper says X, that claim must be grounded in the supplied `paper_text`. Reviewer prompts already enforce this; don't dilute it.

## Optional: true multi-LLM mode

The original tool calls 6 different proprietary LLMs (GPT-4o, Claude 3.7 Sonnet, Gemini 2.5 Pro, DeepSeek R1, Llama 4 Maverick) for genuine model diversity. If the user explicitly asks for that and has the package installed:

```bash
pip install ai-peer-review  # or: pip install git+https://github.com/poldrack/ai-peer-review
ai-peer-review review <paper.pdf>
```

Run that as a Bash command and let it produce its own outputs. This skill's subagent path is a Claude-only substitute, not a replacement.

## Installation

This directory is the skill. To make it discoverable by Claude Code:

```bash
# user-level (available in every project)
ln -s "$(pwd)" ~/.claude/skills/paper-review

# or project-level
ln -s "$(pwd)" <your-project>/.claude/skills/paper-review
```

Restart the Claude Code session afterwards so the skill is picked up.

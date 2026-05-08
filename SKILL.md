---
name: paper-review
description: Use when the user asks for a peer review, critique, or meta-review of an academic paper (PDF, DOCX, or extracted text). Spawns N independent reviewer subagents in parallel under anonymized NATO codenames, then synthesizes a meta-review identifying common and unique concerns plus a CSV concerns table. Adapted from poldrack/ai-peer-review. Triggers on phrases like "peer review this paper", "critique this PDF", "review like a reviewer would", "meta-review this manuscript", "act as reviewer 2".
---

# Paper Peer Review

Multi-reviewer peer review of an academic paper. Models the workflow of [poldrack/ai-peer-review](https://github.com/poldrack/ai-peer-review) but uses parallel Claude subagents in place of multiple proprietary LLMs, so it works with no extra API keys.

## Inputs

| Argument | Required | Default | Notes |
|---|---|---|---|
| `paper` | yes | — | Path to a PDF, DOCX, or `.txt`/`.md` of the paper. |
| `domain` | no | inferred | Reviewer field, e.g. `"neuroscience and brain imaging"`. Inferred from the paper's title/abstract if not supplied. |
| `num_reviewers` | no | `3` | Independent reviewers to spawn. Min 3, max 8. |
| `output_dir` | no | `./papers/<paper-stem>/` | Where review artifacts are written. |
| `skip_meta` | no | `false` | If `true`, only individual reviews are produced. |
| `overwrite` | no | `false` | If `false`, reuse any `review_*.md` already present and only run missing reviewers + meta. |
| `alignment_critic` | no | `true` | If `true`, one of the `num_reviewers` slots is filled by an AI-Alignment-Forum-style critic (see `prompts/reviewer_alignment_forum.md`) instead of a generic reviewer. Set `false` to use only generic reviewers. |

If the user invokes the skill ambiguously, ask only for `paper` — infer the rest.

## Workflow

### 1. Extract paper text

- PDF → use `pypdf` (`python -c "from pypdf import PdfReader; ..."`) or `pdftotext` if available.
- DOCX → use `python-docx` or `pandoc`.
- `.txt`/`.md` → read directly.

If extraction yields fewer than ~1000 characters or text is mostly garbled (common with scanned PDFs), tell the user and stop — OCR is out of scope for this skill.

### 2. Sanity check

Confirm the document looks like an academic paper (abstract, methods/results, references). If not, ask the user to confirm before proceeding.

### 3. Spawn reviewers in parallel via `spawn_reviewers.py`

**Do NOT use the Agent tool to spawn reviewers.** In headless `claude -p` mode the host serializes tool_use blocks, which makes Agent-based parallelism collapse into sequential ~3 min/reviewer runs. We sidestep this by spawning reviewers as independent `claude -p` subprocesses through a Python helper.

Issue exactly **one Bash call**:

```bash
python3 {skill_dir}/scripts/spawn_reviewers.py \
  --paper-text-file /tmp/paper_text.txt \
  --output-dir <output_dir> \
  --skill-dir {skill_dir} \
  --num-reviewers <N> \
  --domain "<domain>" \
  --model sonnet \
  $([ <alignment_critic> = false ] && echo --no-alignment-critic) \
  $([ <overwrite> = true ] && echo --overwrite)
```

What this does:
- Forks `N` `claude -p --model sonnet` subprocesses concurrently. True OS-level parallelism — total wall-clock = `max(reviewer_time)`, not `sum(reviewer_time)`.
- Each child reads its prompt from stdin (paper_text + reviewer instructions), writes its review to `<output_dir>/review_<codename>.md` directly.
- Each child is a full Claude Code instance with tool access (Bash, arxiv_search, etc.) — no functional regression vs. Agent-based path.
- One slot is randomly assigned `prompts/reviewer_alignment_forum.md` if `alignment_critic=true`. Anonymity is preserved (the script does not disclose which slot was the critic).
- Skips reviewers whose `review_<codename>.md` already exists, unless `--overwrite` is passed (corresponds to skill's `overwrite=true`).

NATO codenames in order: `alfa, bravo, charlie, delta, echo, foxtrot, golf, hotel`. The script picks the first `N`.

The script writes progress lines to stderr (`[spawn_reviewers] alfa started (pid=…, t+0.1s)`, `[spawn_reviewers] alfa OK (t+45.2s)`) so you can verify all reviewers started in roughly the same second — that is the parallelism check.

Sonnet is mandatory for reviewers (`--model sonnet`). Don't downgrade to Haiku or upgrade to Opus without explicit user request — Sonnet 4.6 is the design point.

Reviewers must NOT see each other's outputs. The script enforces this by giving each subprocess its own stdin and not sharing state.

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

### 7. Surface per-reviewer verdicts to the user

In the final assistant message that reports the review is done, include a compact verdict table — one line per codename — pulled from each `review_<nato>.md`'s **Verdict** section. Example:

```
alfa     — Major revision
bravo    — Reject
charlie  — Major revision
---
Consensus: Major revision
```

The user must see individual verdicts at a glance without opening files.

### 8. Save the bundle

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

- **Use `spawn_reviewers.py`, not the Agent tool.** Headless Claude Code serializes Agent calls; `claude -p` subprocesses do not. The script is the only supported path.
- **Sonnet for reviewers is mandatory** — `spawn_reviewers.py` defaults to `--model sonnet`; don't override unless the user explicitly asks.
- **Anonymity matters** — when synthesizing, refer to reviewers only by NATO codename. Don't disclose that they're all Claude subagents inside the meta-review prose.
- **Don't soften the criticism.** The meta-review must preserve specific, actionable critiques. If a reviewer recommended "Reject", say so — don't average it into "Major revision" silently.
- **Reuse existing reviews** when `overwrite=false` and `review_<nato>.md` already exists in `output_dir`. Only run the missing reviewers + meta-review.
- **No fabricated citations.** If a reviewer claims a paper says X, that claim must be grounded in the supplied `paper_text`. Reviewer prompts already enforce this; don't dilute it.

## Diversity via String Seed of Thought (SSoT)

All reviewer prompts open with a `Step 0 — Seed your perspective` block adapted from [String Seed of Thought (arXiv:2510.21150)](https://arxiv.org/abs/2510.21150). Each reviewer first emits a 32-char random hex `SEED`, then deterministically derives a `LENS` (or `AXIS` for the alignment critic) and a `STANCE` from byte-slices of that seed.

Why: N parallel Sonnet reviewers with the same prompt collapse to highly correlated critiques — temperature alone does not give enough viewpoint diversity. SSoT injects entropy explicitly and routes it through a discrete mapping, so reviewer alfa might argue the paper from "External validity, Adversarial" while bravo presses "Statistical methodology, Steelman-then-press". The seed is preserved in the saved `review_<nato>.md` for reproducibility — re-running with the same seed should produce the same review angle.

Don't strip the SSoT block from prompts. Don't seed the reviewers from the host (the model emitting its own SEED is the point of the technique).

## arXiv lookup (`scripts/arxiv_search.py`)

Every reviewer (standard and alignment-forum) has unconditional access to `python3 {skill_dir}/scripts/arxiv_search.py "<query>"` via Bash. The script returns `[arxiv_id] (year) Title / Authors / Summary` rows, capped at 8 results, sorted by relevance (or `--sort date` for recency). The arxiv client uses 5 s delay + 4 retries to absorb arXiv's per-IP throttling under concurrent reviewer access.

Reviewers are **required** to run at least one arXiv query (mandatory minimum = 1, hard cap = 3). Typical high-value queries: missing prior art, stronger baselines, replication attempts, follow-up counter-results, "first to do X" verification, established benchmarks the paper should have used. A red-team without a literature check is half a red-team — and earlier prompt versions made the call optional, which Sonnet correctly read as "skip" since the paper text is fully in the prompt.

Rules enforced in each reviewer prompt:
- **Min 1, max 3 calls per reviewer.** With a 3-reviewer panel that is 3–9 sequential arXiv hits, absorbed by the client's 5 s delay + 4 retries.
- **Cite by arXiv ID only.** Reviewers must never cite a paper they did not see in search output.
- **No meta-commentary about the tool.** Findings get integrated into Major/Minor concerns with their arXiv IDs — no "I searched arXiv and found…" framing.
- **Silent fallback on error.** `Error: arxiv package not installed` or `HTTP 429` → no retry, no mention in the review, mandatory-call requirement waived.

Dependency: `pip install arxiv`. Not bundled — install once in the environment that runs the reviewer subagents. Without it, reviewers degrade gracefully (no prior-art lookup, otherwise normal review).

## The alignment-forum critic

By default one panel slot is filled by a reviewer that follows Neel Nanda's *[Highly Opinionated Advice on How to Write ML Papers](https://www.alignmentforum.org/posts/eJGptPbbFPZGLpjsp/highly-opinionated-advice-on-how-to-write-ml-papers)* — narrative compression, novelty attribution, hard red-teaming of evidence (cherry-picking, post-hoc analysis, weak baselines, missing ablations, p-value skepticism, alternative explanations), reproducibility checks, and an explicit "what did this paper actually update in my beliefs?" question.

The critic produces the same Markdown shape as the standard reviewer (Summary / Major / Minor / Verdict, plus a `Belief update` block) so the meta-review and concerns table can ingest its output without special-casing. Each major concern is tagged with the framework section it came from (e.g. `[Evidence — baselines]`).

This adds genuine viewpoint diversity to a panel that would otherwise be all-Claude-of-the-same-flavour. Disable with `alignment_critic=false` if you specifically want a uniform panel.

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

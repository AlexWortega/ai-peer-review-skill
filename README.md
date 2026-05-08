# ai-peer-review-skill

A [Claude Code](https://claude.com/claude-code) skill that runs a multi-reviewer peer review of an academic paper.

Drop a PDF in, get back N independent reviews + a synthesized meta-review + a CSV table of which reviewer raised which concern.

## What it does

Given a PDF (or DOCX / `.txt` / `.md`) of a paper, the skill:

1. Extracts the text.
2. **Spawns N reviewer subagents in parallel** with anonymized NATO codenames (`alfa`, `bravo`, `charlie`, …). Each subagent sees only the paper and produces an independent, structured review (summary → major concerns → minor concerns → verdict).
   - By default, one of the panel slots is filled by an **AI Alignment Forum-style critic** that follows Neel Nanda's *[Highly Opinionated Advice on How to Write ML Papers](https://www.alignmentforum.org/posts/eJGptPbbFPZGLpjsp/highly-opinionated-advice-on-how-to-write-ml-papers)* — hard red-teaming on narrative, novelty, baselines, ablations, post-hoc analysis, p-value rigor, reproducibility, and an explicit "what did this update in my beliefs?" check. Disable with `alignment_critic=false`.
3. **Synthesizes a meta-review** in the main thread, identifying common vs unique concerns, ranking the reviewers by usefulness, and producing a final verdict.
4. **Extracts a concerns table** — a boolean matrix of `concern × reviewer` — and saves it as CSV.
5. Bundles everything into `results.json`.

Output layout:

```
papers/<paper-stem>/
├── review_alfa.md
├── review_bravo.md
├── review_charlie.md
├── review_delta.md
├── review_echo.md
├── meta_review.md
├── concerns_table.csv
└── results.json
```

## Where it came from

This is a Claude Code skill port of [**poldrack/ai-peer-review**](https://github.com/poldrack/ai-peer-review) by Russ Poldrack — a Python tool that calls 6 different proprietary LLMs (GPT-4o, GPT-4o-mini, Claude 3.7 Sonnet, Gemini 2.5 Pro, DeepSeek R1, Llama 4 Maverick) to peer-review a paper, then synthesizes a meta-review.

The port differs in two ways:

| | Original | This skill |
|---|---|---|
| Reviewers | 6 different proprietary LLMs | N parallel Claude subagents (default 5) |
| API keys needed | OpenAI + Anthropic + Google + Together | None beyond Claude Code itself |
| Diversity | True cross-model diversity | Independent generations, single model family |
| Domain | Hard-coded to neuroscience | `domain` argument, inferred from paper if omitted |

The skill keeps the original's artifact layout (`review_*.md`, `meta_review.md`, `concerns_table.csv`, `results.json`) and the NATO-codename anonymization scheme so outputs are interchangeable.

If you actually need cross-model diversity (e.g. for a methods paper *about* AI peer review), use the original `poldrack/ai-peer-review` Python tool instead. The SKILL.md documents this fallback explicitly.

## Install

```bash
git clone https://github.com/AlexWortega/ai-peer-review-skill.git
ln -s "$(pwd)/ai-peer-review-skill" ~/.claude/skills/paper-review
```

(or symlink into `<project>/.claude/skills/paper-review` for project-scoped install.)

Restart your Claude Code session so the skill is picked up.

## Use

In Claude Code:

> Peer-review this paper: `~/Downloads/manuscript.pdf`

or

> /paper-review ~/Downloads/manuscript.pdf

Optional knobs (just say them in plain language):

- domain — `"neuroscience and brain imaging"`, `"reinforcement learning"`, etc.
- num_reviewers — 3 to 8 (default 5)
- output_dir — defaults to `./papers/<paper-stem>/`
- skip_meta — only individual reviews, no synthesis
- overwrite — regenerate existing `review_*.md` files

## Layout

```
.
├── SKILL.md                              # frontmatter + workflow Claude follows
├── prompts/
│   ├── reviewer.md                       # generic reviewer template
│   ├── reviewer_alignment_forum.md       # AAF-style critic (Nanda framework)
│   └── metareview.md                     # synthesis template
└── README.md                             # this file
```

## Credits

- Original tool and prompt design: [Russell Poldrack](https://github.com/poldrack) — [poldrack/ai-peer-review](https://github.com/poldrack/ai-peer-review)
- Skill adaptation: this repo

## License

MIT (skill adaptation only). The upstream `poldrack/ai-peer-review` repo is unlicensed at the time of this port; only the design and workflow are referenced here, no upstream code is redistributed.

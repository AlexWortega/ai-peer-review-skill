"""Spawn N peer reviewer subprocesses via claude -p in parallel.

Each reviewer is its own `claude -p` subprocess running concurrently. This
sidesteps the headless Claude Code host's tendency to serialize Agent tool
calls (one tool_use per turn), which we observed adding ~3 minutes of
unnecessary wall-clock time per reviewer in production runs.

Reviewers retain full tool access (Bash for arxiv_search, etc.) since each
child is a real Claude Code instance.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path


NATO = ["alfa", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]


def build_prompt(template: Path, *, reviewer_id: str, paper_text: str, skill_dir: str, domain: str) -> str:
    text = template.read_text()
    return (
        text.replace("{reviewer_id}", reviewer_id)
        .replace("{skill_dir}", skill_dir)
        .replace("{domain}", domain)
        .replace("{paper_text}", paper_text)
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Spawn parallel peer reviewers via claude -p.")
    p.add_argument("--paper-text-file", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--skill-dir", required=True)
    p.add_argument("--num-reviewers", type=int, default=3)
    p.add_argument("--alignment-critic", dest="alignment_critic", action="store_true", default=True)
    p.add_argument("--no-alignment-critic", dest="alignment_critic", action="store_false")
    p.add_argument("--domain", default="this paper's domain (inferred from text)")
    p.add_argument("--model", default="sonnet")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    n = max(3, min(8, args.num_reviewers))
    codenames = NATO[:n]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_dir = str(Path(args.skill_dir).resolve())
    paper_text = Path(args.paper_text_file).read_text()

    standard_template = Path(skill_dir) / "prompts" / "reviewer.md"
    af_template = Path(skill_dir) / "prompts" / "reviewer_alignment_forum.md"

    af_idx = random.randrange(n) if args.alignment_critic else -1

    procs: list[tuple[str, subprocess.Popen | None, object]] = []
    start = time.time()
    for i, code in enumerate(codenames):
        out_path = output_dir / f"review_{code}.md"
        if out_path.exists() and not args.overwrite:
            print(f"[spawn_reviewers] skip {code} (exists, --overwrite not set)", file=sys.stderr, flush=True)
            procs.append((code, None, None))
            continue
        template = af_template if i == af_idx else standard_template
        prompt = build_prompt(
            template,
            reviewer_id=code,
            paper_text=paper_text,
            skill_dir=skill_dir,
            domain=args.domain,
        )
        out_fh = open(out_path, "w")
        proc = subprocess.Popen(
            [
                "claude",
                "--dangerously-skip-permissions",
                "--model", args.model,
                "-p",
            ],
            stdin=subprocess.PIPE,
            stdout=out_fh,
            stderr=subprocess.PIPE,
            text=True,
        )
        proc.stdin.write(prompt)
        proc.stdin.close()
        elapsed = time.time() - start
        print(
            f"[spawn_reviewers] {code} started (pid={proc.pid}, template={template.name}, t+{elapsed:.1f}s)",
            file=sys.stderr,
            flush=True,
        )
        procs.append((code, proc, out_fh))

    rc_total = 0
    for code, proc, out_fh in procs:
        if proc is None:
            continue
        rc = proc.wait()
        if out_fh is not None:
            out_fh.close()
        elapsed = time.time() - start
        if rc == 0:
            print(f"[spawn_reviewers] {code} OK (t+{elapsed:.1f}s)", file=sys.stderr, flush=True)
        else:
            err = proc.stderr.read() if proc.stderr else ""
            print(
                f"[spawn_reviewers] {code} FAIL rc={rc} (t+{elapsed:.1f}s): {err[:500]}",
                file=sys.stderr,
                flush=True,
            )
            rc_total = max(rc_total, rc)

    return rc_total


if __name__ == "__main__":
    sys.exit(main())

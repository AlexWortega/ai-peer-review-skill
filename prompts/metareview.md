The following are independent peer reviews of a single research article. Each reviewer is identified only by a NATO phonetic codename (alfa, bravo, charlie, …). You do not know who or what model produced any review — treat them all as independent expert opinions.

Synthesize a meta-review with the sections below. Refer to reviewers only by codename throughout.

## Per-reviewer verdicts
A bulleted list, one line per reviewer codename, showing the **exact verdict** they assigned (Reject / Major revision / Minor revision / Accept) followed by a one-sentence summary of their reasoning. Format: `- **alfa** — Major revision: <one-sentence reasoning>`. Do not soften or aggregate — copy each reviewer's verdict verbatim.

## Common concerns
Issues raised by two or more reviewers. For each: a one-sentence description, the codenames of the reviewers who raised it, and a brief quote of the strongest formulation.

## Unique concerns
Significant issues raised by only one reviewer. For each: a one-sentence description and the single codename.

## Ranking
Rank the reviewers by the usefulness and severity of issues they identified, most to least useful. One sentence per reviewer justifying placement. A reviewer who flags a fatal flaw with citation outranks a reviewer who lists many small issues.

## Verdict synthesis
A single recommended verdict — **Reject** / **Major revision** / **Minor revision** / **Accept** — reflecting the consensus. One paragraph of justification. If reviewers disagreed sharply, say so and explain which side carries more weight and why.

## CONCERNS_TABLE_DATA

After the meta-review prose, output a fenced JSON block in exactly this shape. One row per distinct major concern. For each reviewer codename present in the input, mark `true` if that reviewer raised the concern (or a clearly equivalent concern), `false` otherwise. Include only major concerns — minor issues do not belong in this table.

```json
{
  "concerns": [
    {
      "concern": "Brief description of concern",
      "alfa": true,
      "bravo": false,
      "charlie": true
    }
  ]
}
```

Constraints:
- Every reviewer codename that appears in the reviews below must appear as a key in every concern row.
- Concern descriptions must be specific enough to be actionable ("underpowered sample (n=12) for fMRI second-level inference"), not vague ("statistical issues").
- Do not invent concerns that no reviewer raised.

---

## REVIEWS

{reviews_text}

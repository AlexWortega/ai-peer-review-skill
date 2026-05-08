"""arXiv search helper for paper-review reviewers.

Used by reviewer subagents to verify novelty claims and surface missing
prior art when their assigned LENS / AXIS is novelty-related. Returns
verifiable arXiv IDs so the reviewer can cite without fabricating.
"""

import argparse


def query_arxiv(query: str, max_papers: int = 8, sort: str = "relevance") -> str:
    try:
        import arxiv
    except ImportError:
        return "Error: arxiv package not installed. Run: pip install arxiv"

    sort_map = {
        "relevance": arxiv.SortCriterion.Relevance,
        "date": arxiv.SortCriterion.SubmittedDate,
    }
    sort_by = sort_map.get(sort, arxiv.SortCriterion.Relevance)

    try:
        client = arxiv.Client(page_size=max_papers, delay_seconds=5.0, num_retries=4)
        search = arxiv.Search(query=query, max_results=max_papers, sort_by=sort_by)
        rows = []
        for p in client.results(search):
            arxiv_id = p.get_short_id()
            authors = ", ".join(a.name for a in p.authors[:3])
            if len(p.authors) > 3:
                authors += " et al."
            year = p.published.year if p.published else "n.d."
            summary = " ".join(p.summary.split())
            if len(summary) > 500:
                summary = summary[:500].rstrip() + "…"
            rows.append(
                f"[{arxiv_id}] ({year}) {p.title}\n"
                f"  Authors: {authors}\n"
                f"  Summary: {summary}"
            )
        return "\n\n".join(rows) if rows else "No papers found."
    except Exception as e:
        return f"Error querying arXiv: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Search arXiv for papers.")
    parser.add_argument("query", type=str, help="Search query string.")
    parser.add_argument("--max-papers", type=int, default=8, help="Max results (default 8).")
    parser.add_argument(
        "--sort",
        choices=["relevance", "date"],
        default="relevance",
        help="Sort by relevance (default) or submission date.",
    )
    args = parser.parse_args()
    print(query_arxiv(args.query, args.max_papers, args.sort))


if __name__ == "__main__":
    main()

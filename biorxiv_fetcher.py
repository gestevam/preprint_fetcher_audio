from __future__ import annotations
"""
bioRxiv Daily Preprint Fetcher — minimal, network-safe implementation.

Only outbound connection: one HTTPS GET to api.biorxiv.org per run.
No scraping, no image downloading, no third-party dependencies.
Standard library only (requests is the sole external package).

Reruns during the same day add new results rather than overwriting.
"""

import json
import logging
import subprocess
import time
from datetime import date, timedelta
from dataclasses import dataclass, asdict, field
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"config.json not found at {config_path}")
    with config_path.open() as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Preprint:
    doi: str
    title: str
    authors: list
    abstract: str
    date: str
    category: str
    url: str
    keywords_matched: list = field(default_factory=list)
    authors_matched: list = field(default_factory=list)

# ---------------------------------------------------------------------------
# bioRxiv API
# ---------------------------------------------------------------------------

BIORXIV_API = "https://api.biorxiv.org/details/biorxiv"

def _safe_get(url: str, timeout: int = 60) -> dict | None:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "biorxiv-feed/1.0"},
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        log.warning(f"Request timed out: {url}")
    except requests.exceptions.SSLError:
        log.warning(f"SSL error: {url}")
    except requests.exceptions.ConnectionError:
        log.warning(f"Could not connect: {url}")
    except requests.exceptions.HTTPError as e:
        log.warning(f"HTTP {e.response.status_code} from {url}")
    except (json.JSONDecodeError, ValueError):
        log.warning(f"Invalid JSON from {url}")
    return None


def fetch_for_date(target: date):
    date_str = target.strftime("%Y-%m-%d")
    url = f"{BIORXIV_API}/{date_str}/{date_str}/0/json"
    log.info(f"Fetching {url}")
    data = _safe_get(url)
    if data is None:
        return []
    papers = data.get("collection", [])
    if not isinstance(papers, list):
        log.warning("Unexpected API response shape")
        return []
    return papers

# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    return text.lower()

def match_paper(paper: dict, keywords: list[str], authors: list) -> tuple[list, list]:
    searchable = _normalise(paper.get("title", "") + " " + paper.get("abstract", ""))
    author_str = _normalise(paper.get("authors", ""))
    kw_hits = [kw for kw in keywords if _normalise(kw) in searchable]
    au_hits = [au for au in authors if _normalise(au) in author_str]
    return kw_hits, au_hits

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_fetch(config: dict | None = None) -> list[Preprint]:
    if config is None:
        config = load_config()

    keywords:    list = config.get("keywords", [])
    authors:     list = config.get("authors", [])
    categories:  list = [c.lower() for c in config.get("categories", [])]
    days_back:   int       = max(1, int(config.get("days_back", 1)))
    max_results: int       = min(200, int(config.get("max_results", 50)))
    output_dir             = Path(config.get("output_dir", "./feed_output"))

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "feed.json"

    # Load existing results for today — reruns add, not overwrite
    existing: dict[str, dict] = {}
    if out_path.exists():
        try:
            saved = json.loads(out_path.read_text())
            if saved.get("generated") == str(date.today()):
                for p in saved.get("preprints", []):
                    existing[p["doi"]] = p
                log.info(f"Loaded {len(existing)} existing results for today")
        except Exception:
            pass

    seen_dois: set[str] = set(existing.keys())
    new_results: list = []

    for day_offset in range(days_back):
        if len(existing) + len(new_results) >= max_results:
            break

        target = date.today() - timedelta(days=day_offset)
        raw_papers = fetch_for_date(target)

        for paper in raw_papers:
            if len(existing) + len(new_results) >= max_results:
                break

            doi = paper.get("doi", "").strip()
            if not doi or doi in seen_dois:
                continue

            paper_cat = paper.get("category", "").lower()
            if categories and paper_cat not in categories:
                continue

            kw_hits, au_hits = match_paper(paper, keywords, authors)
            if not kw_hits and not au_hits:
                continue

            seen_dois.add(doi)
            author_list = [a.strip() for a in paper.get("authors", "").split(";") if a.strip()]

            new_results.append(Preprint(
                doi=doi,
                title=paper.get("title", "").strip(),
                authors=author_list,
                abstract=paper.get("abstract", "").strip(),
                date=paper.get("date", str(target)),
                category=paper.get("category", "").title(),
                url=f"https://www.biorxiv.org/content/{doi}",
                keywords_matched=kw_hits,
                authors_matched=au_hits,
            ))

        if day_offset < days_back - 1:
            time.sleep(0.5)

    log.info(f"{len(new_results)} new preprints found this run")

    # Merge new into existing, preserving today's accumulated results
    all_preprints = list(existing.values()) + [asdict(p) for p in new_results]

    # Sort: author matches first, then keyword matches
    all_preprints.sort(
        key=lambda p: (len(p["authors_matched"]), len(p["keywords_matched"])),
        reverse=True
    )

    payload = {
        "generated": str(date.today()),
        "total": len(all_preprints),
        "filters": {"keywords": keywords, "authors": authors},
        "preprints": all_preprints,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info(f"Saved {len(all_preprints)} total preprints for today → {out_path}")

    # Generate HTML report
    try:
        from generate_html import run as generate_html
        html_path = generate_html()
        log.info(f"HTML report → {html_path}")
    except Exception as e:
        log.warning(f"Could not generate HTML: {e}")

    # Generate audio feed
    try:
        from audio_feed import run as play_audio
        play_audio()
        log.info("Audio feed complete")
    except Exception as e:
        log.warning(f"Could not generate audio: {e}")

    return new_results


if __name__ == "__main__":
    new = run_fetch()
    print(f"\n✓ {len(new)} new preprints added this run")

    html_file = Path("./feed_output/index.html")
    if html_file.exists():
        subprocess.run(["open", str(html_file.resolve())])

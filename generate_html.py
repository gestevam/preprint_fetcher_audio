from __future__ import annotations
"""
generate_html.py — Reads feed.json and writes a polished light HTML report.
Called automatically by biorxiv_fetcher.py after each fetch, or run manually.

Usage:
    python generate_html.py
"""

import json
import re
from datetime import date
from pathlib import Path

FEED_PATH = Path("./feed_output/feed.json")
OUT_PATH  = Path("./feed_output/index.html")


def sentence_preview(abstract: str, n: int = 2) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', abstract.strip())
    return " ".join(sentences[:n])


def category_color(category: str) -> tuple[str, str]:
    mapping = {
        "neuroscience":      ("#dbeafe", "#1d4ed8"),
        "cell biology":      ("#dcfce7", "#15803d"),
        "genomics":          ("#fef9c3", "#854d0e"),
        "bioinformatics":    ("#fee2e2", "#b91c1c"),
        "biochemistry":      ("#ede9fe", "#6d28d9"),
        "cancer biology":    ("#ffe4e6", "#be123c"),
        "systems biology":   ("#cffafe", "#0e7490"),
        "genetics":          ("#d1fae5", "#065f46"),
        "immunology":        ("#ffedd5", "#c2410c"),
        "microbiology":      ("#e0f2fe", "#0369a1"),
        "biophysics":        ("#fae8ff", "#86198f"),
        "molecular biology": ("#f0fdf4", "#166534"),
    }
    return mapping.get(category.lower(), ("#f1f5f9", "#334155"))


def build_html(data: dict) -> str:
    preprints = data.get("preprints", [])
    generated = data.get("generated", str(date.today()))
    filters   = data.get("filters", {})
    keywords  = filters.get("keywords", [])
    authors   = filters.get("authors", [])
    total     = data.get("total", len(preprints))

    def pills(items, bg, fg):
        return "".join(
            f'<span style="background:{bg};color:{fg};border:0.5px solid {fg}30;'
            f'border-radius:20px;padding:2px 10px;font-size:11px;font-weight:500;">{i}</span>'
            for i in items
        )

    kw_pills = pills(keywords, "#eff6ff", "#1d4ed8")
    au_pills = pills(authors,  "#f0fdf4", "#15803d")

    cards_html = ""
    for i, p in enumerate(preprints):
        bg, fg = category_color(p.get("category", ""))
        cat     = p.get("category", "").title()
        title   = p.get("title", "")
        url     = p.get("url", "#")
        aulist  = p.get("authors", [])
        kw_hit  = p.get("keywords_matched", [])
        au_hit  = p.get("authors_matched", [])
        preview = sentence_preview(p.get("abstract", ""), 2)
        pdate   = p.get("date", "")

        def fmt_author(a):
            for wa in authors:
                if wa.lower() in a.lower():
                    return f'<span style="color:#15803d;font-weight:500;">{a}</span>'
            return a

        author_str = ", ".join(fmt_author(a) for a in aulist[:6])
        if len(aulist) > 6:
            author_str += f' <span style="color:#94a3b8;">+{len(aulist)-6} more</span>'

        match_tags = ""
        for kw in kw_hit:
            match_tags += f'<span style="background:#eff6ff;color:#1d4ed8;border:0.5px solid #bfdbfe;border-radius:12px;padding:1px 8px;font-size:10px;">⌖ {kw}</span> '
        for au in au_hit:
            match_tags += f'<span style="background:#f0fdf4;color:#15803d;border:0.5px solid #bbf7d0;border-radius:12px;padding:1px 8px;font-size:10px;">★ {au}</span> '

        delay = i * 0.05

        cards_html += f"""
        <article style="background:#ffffff;border:0.5px solid #e2e8f0;
            border-radius:14px;padding:20px 24px;margin-bottom:10px;
            animation:fadeUp 0.4s ease both;animation-delay:{delay}s;
            transition:border-color 0.2s,box-shadow 0.2s;"
            onmouseover="this.style.borderColor='#cbd5e1';this.style.boxShadow='0 2px 12px rgba(0,0,0,0.06)'"
            onmouseout="this.style.borderColor='#e2e8f0';this.style.boxShadow='none'">

            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
                <span style="background:{bg};color:{fg};border-radius:20px;padding:2px 10px;
                    font-size:10px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">{cat}</span>
                <span style="color:#94a3b8;font-size:11px;">{pdate}</span>
                {match_tags}
            </div>

            <a href="{url}" target="_blank" style="text-decoration:none;">
                <h2 style="font-size:15px;font-weight:500;color:#0f172a;line-height:1.5;
                    margin:0 0 8px;letter-spacing:-0.01em;transition:color 0.15s;"
                    onmouseover="this.style.color='#2563eb'"
                    onmouseout="this.style.color='#0f172a'">{title}</h2>
            </a>

            <p style="font-size:12px;color:#64748b;margin:0 0 10px;line-height:1.5;">{author_str}</p>

            <p style="font-size:13px;color:#475569;line-height:1.65;margin:0 0 14px;">{preview}</p>

            <a href="{url}" target="_blank"
                style="display:inline-block;font-size:11px;font-weight:500;color:#2563eb;
                text-decoration:none;padding:5px 14px;border-radius:20px;
                border:0.5px solid #bfdbfe;background:#eff6ff;
                transition:background 0.15s;"
                onmouseover="this.style.background='#dbeafe'"
                onmouseout="this.style.background='#eff6ff'">
                Read preprint →
            </a>
        </article>
        """

    empty = ""
    if not preprints:
        empty = """
        <div style="text-align:center;padding:60px 20px;color:#94a3b8;">
            <div style="font-size:32px;margin-bottom:12px;">◎</div>
            <p style="font-size:14px;">No matching preprints today.</p>
            <p style="font-size:12px;margin-top:6px;">Try expanding your keywords or setting days_back to 7 in config.json.</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>bioRxiv Feed — {generated}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ background: #f8fafc; min-height: 100%; }}
  body {{
    background: #f8fafc;
    color: #0f172a;
    font-family: 'DM Sans', -apple-system, sans-serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(12px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
  ::selection {{ background: #bfdbfe; }}
  a {{ color: inherit; }}
</style>
</head>
<body>

<header style="margin-bottom:36px;animation:fadeUp 0.4s ease both;">
    <div style="display:flex;align-items:baseline;justify-content:space-between;
        border-bottom:0.5px solid #e2e8f0;padding-bottom:16px;margin-bottom:16px;">
        <div>
            <span style="font-family:'DM Mono',monospace;font-size:11px;color:#94a3b8;
                letter-spacing:0.1em;text-transform:uppercase;">bioRxiv</span>
            <h1 style="font-size:22px;font-weight:300;color:#0f172a;letter-spacing:-0.03em;
                margin-top:2px;">Daily Preprint Feed</h1>
        </div>
        <div style="text-align:right;">
            <div style="font-family:'DM Mono',monospace;font-size:11px;color:#94a3b8;">{generated}</div>
            <div style="font-size:13px;color:#475569;margin-top:2px;">
                <span style="color:#16a34a;">●</span> {total} match{'es' if total != 1 else ''}
            </div>
        </div>
    </div>

    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
        <span style="font-size:11px;color:#94a3b8;margin-right:4px;font-family:'DM Mono',monospace;">filters</span>
        {kw_pills}
        {au_pills}
    </div>
</header>

<main>
    {empty}
    {cards_html}
</main>

<footer style="margin-top:40px;padding-top:16px;border-top:0.5px solid #e2e8f0;
    text-align:center;font-size:11px;color:#cbd5e1;font-family:'DM Mono',monospace;">
    generated {generated} · biorxiv-feed
</footer>

</body>
</html>"""

    return html


def run():
    if not FEED_PATH.exists():
        print(f"No feed found at {FEED_PATH}. Run biorxiv_fetcher.py first.")
        return

    data = json.loads(FEED_PATH.read_text())
    html = build_html(data)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"✓ HTML written → {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    run()

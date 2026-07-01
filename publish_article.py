#!/usr/bin/env python3
"""
Auto-publisher for raquel-campos.com
Called by linkedin_weekly_posts.py after generating the weekly posts.
Generates a long-form article, writes HTML to articles/, updates index.json,
and git-pushes so Cloudflare Pages auto-deploys.
"""

import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path

SITE_DIR = Path(__file__).parent


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def generate_article_html(title: str, date: str, topic: str, tags: list,
                           body_html: str, excerpt: str,
                           linkedin_posts: str, reading_time: int,
                           slug: str, sources: list = None) -> str:
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    article_url = f"https://raquel-campos.com/articles/{slug}.html"
    title_encoded = title.replace('"', '&quot;')

    sources_html = ""
    if sources:
        items = ""
        for s in sources:
            link_open = f'<a href="{s["url"]}" target="_blank" rel="noopener">' if s.get("url") else ""
            link_close = "</a>" if s.get("url") else ""
            items += f'''
      <div class="article-source-item" id="src{s["num"]}">
        <div class="article-source-num">{s["num"]}</div>
        <div class="article-source-detail">
          {link_open}{s["title"]}{link_close}
          <span class="article-source-pub">{s["source"]} &middot; {s["date"]}</span>
        </div>
      </div>'''
        sources_html = f'''
<div class="article-sources">
  <h3 class="article-sources-title">Sources</h3>
  {items}
</div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Raquel Campos</title>
  <meta name="description" content="{excerpt}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{excerpt}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{article_url}">
  <link rel="stylesheet" href="../style.css">
  <link rel="icon" href="../favicon.ico">
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="../index.html" class="nav-logo">Raquel <span>Campos</span></a>
    <ul class="nav-links">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../about.html">About</a></li>
      <li><a href="../articles.html" class="active">Articles</a></li>
      <li><a href="../contact.html">Contact</a></li>
    </ul>
  </div>
</nav>

<div class="tagline-bar">
  <span>Industrial Research &nbsp;·&nbsp; Connecting global signals to supply chain &nbsp;·&nbsp; Published every Monday</span>
</div>

<div class="article-header">
  <div class="article-header-inner">
    <p class="article-meta">{date} &nbsp;·&nbsp; {topic} &nbsp;·&nbsp; {reading_time} min read</p>
    <h1>{title}</h1>
    <p class="deck">{excerpt}</p>
    <div style="margin-top:1.25rem;">{tags_html}</div>
  </div>
</div>

<div class="article-body">
{body_html}
</div>

{sources_html}

<div class="article-footer">

  <div class="share-bar">
    <span class="share-label">Share this article</span>
    <div class="share-buttons">
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={article_url}" target="_blank" rel="noopener" class="share-btn share-btn--linkedin">LinkedIn</a>
      <a href="https://twitter.com/intent/tweet?url={article_url}&text={title_encoded}" target="_blank" rel="noopener" class="share-btn share-btn--x">X / Twitter</a>
      <button onclick="copyLink('{article_url}', this)" class="share-btn share-btn--copy">Copy link</button>
    </div>
  </div>

  <div class="linkedin-teaser">
    <h4>This week on LinkedIn</h4>
    <p>Three shorter posts expanding on these signals — follow along for the weekly take.</p>
    <a href="https://www.linkedin.com/in/raquelscampos/" class="btn btn-dark" target="_blank" rel="noopener">Follow on LinkedIn →</a>
  </div>
  <p style="margin-top: 2rem; font-size: 0.9rem; color: var(--text-muted);">
    ← <a href="../articles.html">Back to all articles</a>
  </p>
</div>

<footer class="footer">
  <div class="footer-inner">
    <div class="footer-logo">Raquel <span>Campos</span></div>
    <ul class="footer-links">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../about.html">About</a></li>
      <li><a href="../articles.html">Articles</a></li>
      <li><a href="../contact.html">Contact</a></li>
    </ul>
    <p class="footer-copy">&copy; {datetime.now().year} Raquel Campos</p>
  </div>
</footer>

<script>
function copyLink(url, btn) {{
  navigator.clipboard.writeText(url).then(() => {{
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy link', 2000);
  }});
}}
</script>

</body>
</html>
"""


def markdown_to_html(text: str) -> str:
    """Minimal markdown → HTML: headings, bold, paragraphs, blockquotes."""
    lines = text.split("\n")
    html_lines = []
    in_para = False

    for line in lines:
        line = line.rstrip()

        if line.startswith("## "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("> "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<blockquote><p>{line[2:]}</p></blockquote>")
        elif line == "":
            if in_para: html_lines.append("</p>"); in_para = False
        else:
            # inline bold, italic, citations
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            line = re.sub(r"\[(\d+)\]", r'<sup><a href="#src\1" class="cite">[\1]</a></sup>', line)
            if not in_para:
                html_lines.append("<p>")
                in_para = True
            html_lines.append(line)

    if in_para:
        html_lines.append("</p>")

    return "\n".join(html_lines)


def update_index(slug: str, title: str, date: str, topic: str,
                  tags: list, excerpt: str, reading_time: int) -> None:
    index_path = SITE_DIR / "articles" / "index.json"
    with open(index_path) as f:
        data = json.load(f)

    data["articles"] = [a for a in data["articles"] if a["slug"] != slug]

    data["articles"].insert(0, {
        "slug": slug,
        "title": title,
        "date": date,
        "topic": topic,
        "tags": tags,
        "excerpt": excerpt,
        "reading_time": reading_time,
    })

    with open(index_path, "w") as f:
        json.dump(data, f, indent=2)


def git_push(message: str) -> None:
    cmds = [
        ["git", "-C", str(SITE_DIR), "add", "-A"],
        ["git", "-C", str(SITE_DIR), "commit", "-m", message],
        ["git", "-C", str(SITE_DIR), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  git warning: {result.stderr.strip()}")


def publish(title: str, topic: str, tags: list, body_markdown: str,
             excerpt: str, linkedin_posts: str, sources: list = None) -> str:
    """
    Main entry point. Call this from linkedin_weekly_posts.py.
    Returns the URL of the published article.
    """
    date = datetime.now().strftime("%B %d, %Y")
    slug = slugify(title)
    body_html = markdown_to_html(body_markdown)
    word_count = len(body_markdown.split())
    reading_time = max(1, round(word_count / 200))

    html = generate_article_html(
        title=title, date=date, topic=topic, tags=tags,
        body_html=body_html, excerpt=excerpt, linkedin_posts=linkedin_posts,
        reading_time=reading_time, slug=slug, sources=sources or []
    )

    article_path = SITE_DIR / "articles" / f"{slug}.html"
    with open(article_path, "w") as f:
        f.write(html)

    update_index(slug, title, date, topic, tags, excerpt, reading_time)

    git_push(f"publish: {title}")

    url = f"https://raquel-campos.com/articles/{slug}.html"
    print(f"  Published: {url}")
    return url


if __name__ == "__main__":
    # Test publish — verifies citations and sources section render correctly
    publish(
        title="The Automation Pitch Is Wrong: Geopolitical Instability Is a Better ROI Argument Than Efficiency",
        topic="Geopolitics & Supply Chain",
        tags=["warehouse automation", "geopolitics", "intralogistics", "supply chain resilience"],
        body_markdown="""## The pitch that no longer lands

For the past decade, warehouse automation vendors have led with the same argument: cost-per-pick. Install the system, reduce headcount, watch the payback period hit three years. [1]

The logic was clean when the world was stable. It isn't clean anymore.

The Hormuz disruption changed something structural. A six-week lane restriction rippled into AMR component shortages — the servo motors and LiDAR units that come out of factories in eastern China and transit through the Gulf. [2] Automation timelines at three major European 3PLs I track slipped by four to seven months. Not because the technology failed. Because the parts didn't arrive.

## What the smarter buyers figured out

The companies that signed automation contracts in Q1 weren't buying efficiency. They were buying **independence from labour market volatility**. [3]

That framing survives a supply chain shock. Cost-per-pick doesn't — because the denominator changes every time a lane closes or a tariff shifts.

The vendors who understand this are now leading with resilience, not efficiency. They're closing deals the others can't explain why they're losing.

## What this means if you're making a decision today

If you're evaluating an automation investment right now, the question isn't "what's my payback period at current labour costs?" The question is: **what is this system worth when the next disruption hits?** [1]

That reframe changes which systems pencil out — and which vendors are worth talking to.""",
        excerpt="Automation vendors are still leading with cost-per-pick. But the Hormuz disruption has quietly changed the decision calculus — and the companies that understand this will close deals the others can't explain why they're losing.",
        linkedin_posts="---\nTest LinkedIn post content here.\n---",
        sources=[
            {"num": "1", "title": "Looking at why supply chain tech ROI falls short", "source": "Logistics Management", "date": "June 23, 2026", "url": "https://www.logisticsmgmt.com/"},
            {"num": "2", "title": "Strait of Hormuz disruption: shipping delays ripple into automation supply chains", "source": "Supply Chain Dive", "date": "June 21, 2026", "url": "https://www.supplychaindive.com/"},
            {"num": "3", "title": "European 3PLs accelerate automation investment despite global uncertainty", "source": "DC Velocity", "date": "June 25, 2026", "url": "https://www.dcvelocity.com/"},
        ]
    )

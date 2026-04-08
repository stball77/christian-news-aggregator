#!/usr/bin/env python3
"""
Simple RSS aggregator for Christian news using only the Python standard library.

This script fetches a list of RSS feeds, extracts the latest entries and
generates a static HTML file with aggregated headlines.  It uses only
standard‑library modules, so there is no need to install third‑party
dependencies.  Run it in an environment with Internet access to update
the output.  You can schedule the script with cron to refresh the site
periodically.

Usage:
    python aggregator.py

The script writes an `index.html` file in the current directory.

"""
import datetime
import html
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# List of (Source name, RSS feed URL).  Feel free to add or remove feeds.
FEEDS = [
    ("Christianity Today", "https://feeds.christianitytoday.com/christianitytoday/ctmag"),
    ("The Christian Post", "https://www.christianpost.com/services/rss/feed/"),
    ("Mission Network News", "https://www.mnnonline.org/rss/pubNewsTease.rdf"),
    ("Worthy News", "https://www.worthynews.com/feed"),
    ("ESV Daily Light", "https://www.esvbible.org/devotions/rss/daily-light/"),
    ("BibleGateway Verse of the Day", "https://www.biblegateway.com/votd/get/?format=atom"),
    ("Focus on the Family", "https://feeds2.feedburner.com/FocusOnTheFamilyDailyBroadcast"),
    ("Catholic News Agency", "https://www.catholicnewsagency.com/rss/news.xml"),
    ("United Methodist News", "https://archives.umc.org/rss/RSS_UMNS15.xml"),
]

def fetch_feed(url: str) -> bytes:
    """Retrieve the raw XML for an RSS or Atom feed."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()

def parse_rss_feed(xml_data: bytes, source_name: str, max_items: int = 5):
    """Parse RSS/Atom XML and return a list of entries.

    Each entry is a dict with keys: source, title, link, pub_date, description.
    The pub_date is a datetime.date instance for sorting.
    """
    # Attempt to decode using UTF‑8; fallback to UTF‑8 with replacement.
    try:
        text = xml_data.decode("utf-8")
    except UnicodeDecodeError:
        text = xml_data.decode("utf-8", "replace")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        print(f"Error parsing XML from {source_name}: {exc}", file=sys.stderr)
        return []

    # Determine whether feed is RSS or Atom by checking tag names
    entries = []
    if root.tag == 'rss' or root.tag.endswith('rss'):
        # RSS format
        channel = root.find('channel')
        if channel is None:
            return []
        for item in channel.findall('item')[:max_items]:
            title = item.findtext('title') or 'Untitled'
            link = item.findtext('link') or ''
            pub_str = item.findtext('pubDate')
            description = item.findtext('description') or ''
            pub_date = None
            if pub_str:
                try:
                    pub_date_dt = parsedate_to_datetime(pub_str)
                    pub_date = pub_date_dt.date()
                except Exception:
                    pub_date = None
            entries.append({
                'source': source_name,
                'title': title.strip(),
                'link': link.strip(),
                'pub_date': pub_date or datetime.date.today(),
                'description': description.strip()
            })
    else:
        # Atom format (default namespace may exist)
        # Remove namespace prefixes
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'
        for entry in root.findall(f'.//{ns}entry')[:max_items]:
            title = entry.findtext(f'{ns}title') or 'Untitled'
            link_elem = entry.find(f'{ns}link')
            link = link_elem.get('href') if link_elem is not None else ''
            pub_str = entry.findtext(f'{ns}updated') or entry.findtext(f'{ns}published')
            description = entry.findtext(f'{ns}summary') or ''
            pub_date = None
            if pub_str:
                try:
                    pub_date_dt = parsedate_to_datetime(pub_str)
                    pub_date = pub_date_dt.date()
                except Exception:
                    pub_date = None
            entries.append({
                'source': source_name,
                'title': title.strip(),
                'link': link.strip(),
                'pub_date': pub_date or datetime.date.today(),
                'description': description.strip()
            })
    return entries

def generate_html(entries, output_path: str):
    """Generate an HTML file listing aggregated news entries."""
    now = datetime.datetime.now()
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S')
    # Sort entries by publication date descending
    entries_sorted = sorted(entries, key=lambda e: e['pub_date'], reverse=True)
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang='en'>")
    html_parts.append("<head>")
    html_parts.append("  <meta charset='utf-8'>")
    html_parts.append("  <title>Christian News Aggregator</title>")
    html_parts.append("  <meta name='description' content='Aggregated Christian news from multiple sources.'>")
    html_parts.append("  <meta name='viewport' content='width=device-width, initial-scale=1'>")
    html_parts.append("  <style>body{font-family:Arial, sans-serif;max-width:800px;margin:0 auto;padding:20px;}h1{color:#2c3e50;}article{margin-bottom:20px;border-bottom:1px solid #ddd;padding-bottom:10px;}article h2{margin:0;}small{color:#888;}</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    html_parts.append("  <h1>Christian News Aggregator</h1>")
    html_parts.append(f"  <p><em>Last updated: {html.escape(last_updated)}</em></p>")
    for entry in entries_sorted:
        title_html = html.escape(entry['title'])
        link_html = html.escape(entry['link'])
        desc = html.escape(entry['description'])
        date_str = entry['pub_date'].strftime('%Y-%m-%d')
        source = html.escape(entry['source'])
        html_parts.append("  <article>")
        html_parts.append(f"    <h2><a href='{link_html}'>{title_html}</a></h2>")
        if desc:
            html_parts.append(f"    <p>{desc}</p>")
        html_parts.append(f"    <p><small>{source} – {date_str}</small></p>")
        html_parts.append("  </article>")
    html_parts.append("  <footer><p>Content is aggregated from external RSS feeds. All trademarks and copyrights belong to their respective owners. Only headlines and summaries are displayed; click through to read the original articles.</p></footer>")
    html_parts.append("</body></html>")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_parts))

def main():
    all_entries = []
    for source_name, url in FEEDS:
        print(f"Fetching {source_name}...")
        try:
            xml_data = fetch_feed(url)
        except Exception as exc:
            print(f"  Failed to fetch {url}: {exc}")
            continue
        entries = parse_rss_feed(xml_data, source_name, max_items=5)
        if not entries:
            print(f"  No entries found for {source_name}")
        all_entries.extend(entries)
    if not all_entries:
        print("No entries were fetched. Check your network connection or feed URLs.")
        return
    output_file = os.path.join(os.path.dirname(__file__), 'index.html')
    generate_html(all_entries, output_file)
    print(f"Generated {output_file} with {len(all_entries)} entries.")

if __name__ == '__main__':
    main()
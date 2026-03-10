import os
import fnmatch
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from agents import function_tool


def _url_matches_pattern(url: str):
    """Check if a URL matches any of the configured university URL patterns."""
    raw_patterns = os.getenv("UNIVERSITY_URL_PATTERN", "")
    
    if not raw_patterns:
        return False
    
    patterns = [p.strip().lower() for p in raw_patterns.split(",") if p.strip()]
    parsed = urlparse(url.lower())
    hostname = parsed.netloc
    full = parsed.netloc + parsed.path

    for p in patterns:
        if fnmatch.fnmatch(hostname, p) or fnmatch.fnmatch(full, p):
            return True
    return False


def _get_university_domains():
    """Extract bare domains from the UNIVERSITY_URL_PATTERN env variable for use in Tavily include_domains."""
    raw = os.getenv("UNIVERSITY_URL_PATTERN", "")
    if not raw:
        return []
    domains = []

    for pat in raw.split(","):
        pat = pat.strip().lower()
        if not pat:
            continue
        pat = pat.lstrip("*").lstrip(".")
        domain = pat.split("/")[0]
        if domain:
            domains.append(domain)
    return domains


@function_tool
def search_university_website(query: str):
    """Search ONLY the university's official website using the configured UNIVERSITY_URL_PATTERN.
    Always use this tool first before web_search. Returns results exclusively from the
    university's domain."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set in the environment."
    domains = _get_university_domains()
    if not domains:
        return "Error: UNIVERSITY_URL_PATTERN is not set. Cannot restrict search to university website."
    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5, include_domains=domains)
        entries = []
        for r in results.get("results", []):
            entries.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['content']}")
        if not entries:
            return "No results found on the university's official website for this query."
        return "\n\n---\n\n".join(entries)
    except Exception as e:
        return f"University website search failed: {e}"


@function_tool
def web_search(query: str):
    """FALLBACK ONLY - search the open web using Tavily. Only use this if search_university_website
    returned no useful results or the information is clearly not on the university website
    (e.g. general study tips, external scholarship databases). Returns results from any website."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set in the environment. Please add it to your .env file."
    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5)
        entries = []
        for r in results.get("results", []):
            entries.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['content']}")
        return "\n\n---\n\n".join(entries) if entries else "No results found."
    except Exception as e:
        return f"Search failed: {e}"

# Note: This tool is called after a search returns a relevent URL
@function_tool
def fetch_university_page(url: str):
    """Fetch and return the text content of a university webpage. The URL must match the
    configured UNIVERSITY_URL_PATTERN."""
    if not _url_matches_pattern(url):
        return (
            f"Access denied: '{url}' does not match the configured UNIVERSITY_URL_PATTERN. "
            "Only pages on the official university domain can be fetched with this tool."
        )

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; UniversityStudentAgent/1.0)"

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return f"Failed to fetch page: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    if len(text) > 8000:
        text = text[:8000] + "\n\n[Content truncated — page has more information]"
    return text

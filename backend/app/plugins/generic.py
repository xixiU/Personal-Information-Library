"""Generic plugin - 通用爬取策略."""
import re
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.plugins.base import CrawlerPlugin


class GenericPlugin(CrawlerPlugin):
    """Generic crawler plugin for standard HTML pages."""

    def __init__(self, config: Dict = None):
        """Initialize generic plugin."""
        super().__init__(config)
        self.timeout = config.get("timeout", 30) if config else 30
        self.user_agent = config.get("user_agent", "Mozilla/5.0") if config else "Mozilla/5.0"

    async def fetch(self, url: str) -> str:
        """Fetch content from URL using httpx."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    async def parse(self, html: str, url: str) -> Dict:
        """Parse HTML and extract main content using readability-like algorithm."""
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        content = self._extract_content(soup)

        # Extract metadata
        metadata = self._extract_metadata(soup, url)

        return {"title": title, "content": content, "metadata": metadata}

    async def discover_links(self, html: str, base_url: str) -> List[str]:
        """Discover links from HTML."""
        soup = BeautifulSoup(html, "lxml")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)

            # Only include same-domain links
            if self._is_same_domain(absolute_url, base_url):
                # Clean URL (remove fragments)
                clean_url = absolute_url.split("#")[0]
                if clean_url and clean_url not in links:
                    links.append(clean_url)

        return links

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try <title> tag
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try <h1> tag
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using simple readability algorithm."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content container
        main_content = None

        # Look for common content containers
        for selector in ["article", "main", '[role="main"]', ".content", "#content"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # If no container found, use body
        if not main_content:
            main_content = soup.body

        if main_content:
            # Extract text from paragraphs
            paragraphs = main_content.find_all("p")
            content = "\n\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            return content

        return ""

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata from HTML."""
        metadata = {"url": url}

        # Extract meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            metadata["description"] = meta_desc["content"]

        # Extract meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            metadata["keywords"] = meta_keywords["content"]

        # Extract author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            metadata["author"] = meta_author["content"]

        return metadata

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        return domain1 == domain2

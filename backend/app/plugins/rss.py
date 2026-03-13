"""RSS plugin - RSS/Atom 订阅源爬取插件."""
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.plugins.base import CrawlerPlugin

logger = logging.getLogger(__name__)


class RSSPlugin(CrawlerPlugin):
    """RSS/Atom feed crawler plugin.

    支持 RSS 2.0 和 Atom 格式，将每个 <item>/<entry> 作为独立内容解析。
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.timeout = config.get("timeout", 30) if config else 30
        self.user_agent = (
            config.get("user_agent", "Mozilla/5.0 (compatible; RSSBot/1.0)")
            if config
            else "Mozilla/5.0 (compatible; RSSBot/1.0)"
        )

    async def fetch(self, url: str) -> str:
        """Fetch RSS/Atom feed content."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    async def parse(self, xml: str, url: str) -> Dict:
        """Parse RSS/Atom feed and return feed-level metadata + all items as content."""
        soup = BeautifulSoup(xml, "xml")

        # 判断格式：RSS 2.0 or Atom
        if soup.find("rss") or soup.find("channel"):
            return self._parse_rss(soup, url)
        elif soup.find("feed"):
            return self._parse_atom(soup, url)
        else:
            # 降级：当普通 HTML 处理
            logger.warning(f"Unknown feed format for {url}, falling back to HTML parse")
            html_soup = BeautifulSoup(xml, "lxml")
            title = html_soup.title.string.strip() if html_soup.title else url
            return {"title": title, "content": html_soup.get_text()[:2000], "metadata": {"url": url}}

    def _parse_rss(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析 RSS 2.0 格式."""
        channel = soup.find("channel")
        if not channel:
            return {"title": "Unknown Feed", "content": "", "metadata": {"url": url}}

        feed_title = channel.find("title")
        feed_title = feed_title.get_text().strip() if feed_title else "Unknown Feed"

        feed_link = channel.find("link")
        feed_link = feed_link.get_text().strip() if feed_link else url

        items = channel.find_all("item")
        articles = []

        for item in items:
            title = item.find("title")
            link = item.find("link")
            description = item.find("description")
            pub_date = item.find("pubDate")
            author = item.find("author") or item.find("dc:creator")
            guid = item.find("guid")

            # 提取纯文本内容（description 可能含 HTML/CDATA）
            content_text = ""
            if description:
                desc_html = description.get_text()
                desc_soup = BeautifulSoup(desc_html, "lxml")
                content_text = desc_soup.get_text(separator="\n").strip()

            # 解析发布时间
            pub_date_str = None
            if pub_date:
                try:
                    pub_date_str = parsedate_to_datetime(pub_date.get_text().strip()).isoformat()
                except Exception:
                    pub_date_str = pub_date.get_text().strip()

            articles.append({
                "title": title.get_text().strip() if title else "",
                "link": link.get_text().strip() if link else "",
                "content": content_text,
                "pub_date": pub_date_str,
                "author": author.get_text().strip() if author else "",
                "guid": guid.get_text().strip() if guid else "",
            })

        # 将所有文章拼接为 content，方便 AI 精炼
        content_parts = []
        for i, article in enumerate(articles, 1):
            part = f"## {i}. {article['title']}\n"
            if article["pub_date"]:
                part += f"发布时间：{article['pub_date']}\n"
            if article["link"]:
                part += f"链接：{article['link']}\n"
            part += f"\n{article['content']}"
            content_parts.append(part)

        return {
            "title": feed_title,
            "content": "\n\n---\n\n".join(content_parts),
            "metadata": {
                "url": url,
                "feed_link": feed_link,
                "feed_type": "rss2",
                "item_count": len(articles),
                "items": [
                    {"title": a["title"], "link": a["link"], "pub_date": a["pub_date"]}
                    for a in articles
                ],
            },
        }

    def _parse_atom(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析 Atom 格式."""
        feed = soup.find("feed")
        if not feed:
            return {"title": "Unknown Feed", "content": "", "metadata": {"url": url}}

        feed_title = feed.find("title")
        feed_title = feed_title.get_text().strip() if feed_title else "Unknown Feed"

        entries = feed.find_all("entry")
        articles = []

        for entry in entries:
            title = entry.find("title")
            link = entry.find("link")
            summary = entry.find("summary") or entry.find("content")
            updated = entry.find("updated") or entry.find("published")
            author = entry.find("author")

            link_href = ""
            if link:
                link_href = link.get("href", "") or link.get_text().strip()

            content_text = ""
            if summary:
                summary_html = summary.get_text()
                summary_soup = BeautifulSoup(summary_html, "lxml")
                content_text = summary_soup.get_text(separator="\n").strip()

            articles.append({
                "title": title.get_text().strip() if title else "",
                "link": link_href,
                "content": content_text,
                "pub_date": updated.get_text().strip() if updated else "",
                "author": author.find("name").get_text().strip() if author and author.find("name") else "",
            })

        content_parts = []
        for i, article in enumerate(articles, 1):
            part = f"## {i}. {article['title']}\n"
            if article["pub_date"]:
                part += f"发布时间：{article['pub_date']}\n"
            if article["link"]:
                part += f"链接：{article['link']}\n"
            part += f"\n{article['content']}"
            content_parts.append(part)

        return {
            "title": feed_title,
            "content": "\n\n---\n\n".join(content_parts),
            "metadata": {
                "url": url,
                "feed_type": "atom",
                "item_count": len(articles),
                "items": [
                    {"title": a["title"], "link": a["link"], "pub_date": a["pub_date"]}
                    for a in articles
                ],
            },
        }

    async def discover_links(self, xml: str, base_url: str) -> List[str]:
        """从 RSS 条目中提取文章链接，用于整站爬取模式."""
        soup = BeautifulSoup(xml, "xml")
        links = []

        # RSS 2.0
        for item in soup.find_all("item"):
            link = item.find("link")
            if link:
                href = link.get_text().strip()
                if href and href.startswith("http"):
                    links.append(href)

        # Atom
        for entry in soup.find_all("entry"):
            link = entry.find("link")
            if link:
                href = link.get("href", "")
                if href and href.startswith("http"):
                    links.append(href)

        return list(dict.fromkeys(links))  # 去重保序

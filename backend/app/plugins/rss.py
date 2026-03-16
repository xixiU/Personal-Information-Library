"""RSS plugin - RSS/Atom 订阅源爬取插件."""
import asyncio
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

    def supports_link_discovery(self) -> bool:
        """RSS 插件总是需要链接发现，不依赖 crawl_mode 配置."""
        return True

    async def fetch(self, url: str) -> str:
        """Fetch RSS/Atom feed content."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
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
            except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout fetching {url}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    raise
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                raise

    async def parse(self, xml: str, url: str) -> Dict:
        """Parse RSS/Atom feed and return feed-level metadata with discovered links.

        对于 RSS feed 入口页,返回 feed 的基本信息作为内容,
        discovered links 会在 discover_links() 中返回用于创建子任务。
        """
        soup = BeautifulSoup(xml, "xml")

        # 判断格式：RSS 2.0 or Atom
        if soup.find("rss") or soup.find("channel"):
            return self._parse_rss_feed_info(soup, url)
        elif soup.find("feed"):
            return self._parse_atom_feed_info(soup, url)
        else:
            # 降级：当普通 HTML 处理
            logger.warning(f"Unknown feed format for {url}, falling back to HTML parse")
            html_soup = BeautifulSoup(xml, "lxml")
            title = html_soup.title.string.strip() if html_soup.title else url
            return {"title": title, "content": html_soup.get_text()[:2000], "metadata": {"url": url}}

    def _parse_rss_feed_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析 RSS 2.0 格式，返回 feed 完整信息作为爬取结果.

        这是入口页的爬取结果，包含 feed 的完整描述和文章列表。
        """
        channel = soup.find("channel")
        if not channel:
            return {"title": "Unknown Feed", "content": "", "metadata": {"url": url}}

        feed_title = channel.find("title")
        feed_title = feed_title.get_text().strip() if feed_title else "Unknown Feed"

        feed_link = channel.find("link")
        feed_link = feed_link.get_text().strip() if feed_link else url

        feed_description = channel.find("description")
        feed_description = feed_description.get_text().strip() if feed_description else ""

        items = channel.find_all("item")
        articles = []

        for item in items:
            title = item.find("title")
            link = item.find("link")
            description = item.find("description")
            pub_date = item.find("pubDate")
            author = item.find("author") or item.find("dc:creator")

            # 提取描述文本（可能包含 HTML）
            desc_text = ""
            if description:
                desc_html = description.get_text()
                desc_soup = BeautifulSoup(desc_html, "lxml")
                desc_text = desc_soup.get_text(separator="\n").strip()[:200]  # 限制长度

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
                "description": desc_text,
                "pub_date": pub_date_str,
                "author": author.get_text().strip() if author else "",
            })

        # 生成完整的 feed 内容（作为入口页的爬取结果）
        content_parts = [
            f"# {feed_title}",
            "",
            f"**Feed URL**: {url}",
            f"**Feed Link**: {feed_link}",
            "",
        ]

        if feed_description:
            content_parts.extend([
                "## 描述",
                feed_description,
                "",
            ])

        content_parts.extend([
            f"## 文章列表 (共 {len(articles)} 篇)",
            "",
        ])

        for i, article in enumerate(articles, 1):
            content_parts.append(f"### {i}. {article['title']}")
            if article["author"]:
                content_parts.append(f"**作者**: {article['author']}")
            if article["pub_date"]:
                content_parts.append(f"**发布时间**: {article['pub_date']}")
            if article["link"]:
                content_parts.append(f"**链接**: {article['link']}")
            if article["description"]:
                content_parts.append(f"\n{article['description']}")
            content_parts.append("")

        return {
            "title": feed_title,
            "content": "\n".join(content_parts),
            "metadata": {
                "url": url,
                "feed_link": feed_link,
                "feed_type": "rss2",
                "feed_description": feed_description,
                "item_count": len(articles),
                "items": [
                    {"title": a["title"], "link": a["link"], "pub_date": a["pub_date"]}
                    for a in articles
                ],
            },
        }

    def _parse_atom_feed_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """解析 Atom 格式，返回 feed 完整信息作为爬取结果."""
        feed = soup.find("feed")
        if not feed:
            return {"title": "Unknown Feed", "content": "", "metadata": {"url": url}}

        feed_title = feed.find("title")
        feed_title = feed_title.get_text().strip() if feed_title else "Unknown Feed"

        feed_subtitle = feed.find("subtitle")
        feed_subtitle = feed_subtitle.get_text().strip() if feed_subtitle else ""

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

            desc_text = ""
            if summary:
                summary_html = summary.get_text()
                summary_soup = BeautifulSoup(summary_html, "lxml")
                desc_text = summary_soup.get_text(separator="\n").strip()[:200]

            articles.append({
                "title": title.get_text().strip() if title else "",
                "link": link_href,
                "description": desc_text,
                "pub_date": updated.get_text().strip() if updated else "",
                "author": author.find("name").get_text().strip() if author and author.find("name") else "",
            })

        content_parts = [
            f"# {feed_title}",
            "",
            f"**Feed URL**: {url}",
            "",
        ]

        if feed_subtitle:
            content_parts.extend(["## 描述", feed_subtitle, ""])

        content_parts.extend([f"## 文章列表 (共 {len(articles)} 篇)", ""])

        for i, article in enumerate(articles, 1):
            content_parts.append(f"### {i}. {article['title']}")
            if article["author"]:
                content_parts.append(f"**作者**: {article['author']}")
            if article["pub_date"]:
                content_parts.append(f"**发布时间**: {article['pub_date']}")
            if article["link"]:
                content_parts.append(f"**链接**: {article['link']}")
            if article["description"]:
                content_parts.append(f"\n{article['description']}")
            content_parts.append("")

        return {
            "title": feed_title,
            "content": "\n".join(content_parts),
            "metadata": {
                "url": url,
                "feed_type": "atom",
                "feed_description": feed_subtitle,
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

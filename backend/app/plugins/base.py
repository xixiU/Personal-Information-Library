"""Base plugin class - 插件基类."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class CrawlerPlugin(ABC):
    """Base class for crawler plugins."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize plugin with configuration."""
        self.config = config or {}

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """
        Fetch content from URL.

        Args:
            url: URL to fetch

        Returns:
            Raw HTML content
        """
        pass

    @abstractmethod
    async def parse(self, html: str, url: str) -> Dict:
        """
        Parse HTML content and extract structured data.

        Args:
            html: Raw HTML content
            url: Source URL

        Returns:
            Dictionary with extracted data:
            {
                "title": str,
                "content": str,
                "metadata": dict
            }
        """
        pass

    @abstractmethod
    async def discover_links(self, html: str, base_url: str) -> List[str]:
        """
        Discover links from HTML for full-site crawling.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs
        """
        pass

    def get_name(self) -> str:
        """Get plugin name."""
        return self.__class__.__name__

    def get_domain_pattern(self) -> Optional[str]:
        """Get domain pattern for matching."""
        return None

    def supports_link_discovery(self) -> bool:
        """是否支持链接发现（即是否应该走整站爬取逻辑）.

        RSS 等聚合类插件返回 True，表示爬取入口页后需要继续爬取子链接。
        普通单页插件返回 False。
        """
        return False

"""PLG-U01/U02: Plugin framework tests."""
import pytest
from typing import Dict, List

from app.plugins.base import CrawlerPlugin
from app.plugins.generic import GenericPlugin


# --- Test fixtures ---

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page Title</title>
    <meta name="description" content="A test page">
    <meta name="keywords" content="test,example">
    <meta name="author" content="Tester">
</head>
<body>
    <nav><a href="/nav-link">Nav</a></nav>
    <main>
        <h1>Main Heading</h1>
        <p>First paragraph of content.</p>
        <p>Second paragraph of content.</p>
        <a href="/page2">Page 2</a>
        <a href="https://example.com/page3">Page 3</a>
        <a href="https://other.com/external">External</a>
    </main>
    <footer>Footer</footer>
</body>
</html>
"""

EMPTY_HTML = """
<!DOCTYPE html>
<html><head><title></title></head><body></body></html>
"""

HTML_NO_TITLE = """
<!DOCTYPE html>
<html><head></head><body>
<h1>Fallback H1 Title</h1>
<p>Some content.</p>
</body></html>
"""

HTML_NO_TITLE_NO_H1 = """
<!DOCTYPE html>
<html><head></head><body><p>Just text.</p></body></html>
"""


class TestPluginLoading:
    """PLG-U01: 加载有效插件."""

    def test_generic_plugin_instantiation(self):
        """GenericPlugin 可以正常实例化."""
        plugin = GenericPlugin()
        assert plugin is not None
        assert plugin.timeout == 30
        assert plugin.user_agent == "Mozilla/5.0"

    def test_generic_plugin_with_config(self):
        """GenericPlugin 接受自定义配置."""
        config = {"timeout": 60, "user_agent": "CustomBot/1.0"}
        plugin = GenericPlugin(config=config)
        assert plugin.timeout == 60
        assert plugin.user_agent == "CustomBot/1.0"

    def test_generic_plugin_is_crawler_plugin(self):
        """GenericPlugin 是 CrawlerPlugin 的子类."""
        plugin = GenericPlugin()
        assert isinstance(plugin, CrawlerPlugin)

    def test_plugin_get_name(self):
        """get_name 返回类名."""
        plugin = GenericPlugin()
        assert plugin.get_name() == "GenericPlugin"

    def test_plugin_get_domain_pattern_default(self):
        """默认 domain_pattern 为 None."""
        plugin = GenericPlugin()
        assert plugin.get_domain_pattern() is None


class TestInvalidPlugin:
    """PLG-U02: 加载无效插件（缺少必要接口）."""

    def test_cannot_instantiate_abstract_base(self):
        """不能直接实例化抽象基类."""
        with pytest.raises(TypeError):
            CrawlerPlugin()

    def test_incomplete_plugin_missing_fetch(self):
        """缺少 fetch 方法的插件不能实例化."""

        class BadPlugin(CrawlerPlugin):
            async def parse(self, html, url):
                return {}

            async def discover_links(self, html, base_url):
                return []

        with pytest.raises(TypeError):
            BadPlugin()

    def test_incomplete_plugin_missing_parse(self):
        """缺少 parse 方法的插件不能实例化."""

        class BadPlugin(CrawlerPlugin):
            async def fetch(self, url):
                return ""

            async def discover_links(self, html, base_url):
                return []

        with pytest.raises(TypeError):
            BadPlugin()

    def test_incomplete_plugin_missing_discover_links(self):
        """缺少 discover_links 方法的插件不能实例化."""

        class BadPlugin(CrawlerPlugin):
            async def fetch(self, url):
                return ""

            async def parse(self, html, url):
                return {}

        with pytest.raises(TypeError):
            BadPlugin()

    def test_complete_custom_plugin_works(self):
        """实现所有抽象方法的自定义插件可以实例化."""

        class GoodPlugin(CrawlerPlugin):
            async def fetch(self, url):
                return "<html></html>"

            async def parse(self, html, url):
                return {"title": "", "content": "", "metadata": {}}

            async def discover_links(self, html, base_url):
                return []

        plugin = GoodPlugin()
        assert isinstance(plugin, CrawlerPlugin)


class TestGenericPluginParse:
    """GenericPlugin.parse 解析测试."""

    @pytest.fixture
    def plugin(self):
        return GenericPlugin()

    @pytest.mark.asyncio
    async def test_parse_extracts_title(self, plugin):
        """解析标准HTML提取标题."""
        result = await plugin.parse(SAMPLE_HTML, "https://example.com")
        assert result["title"] == "Test Page Title"

    @pytest.mark.asyncio
    async def test_parse_extracts_content(self, plugin):
        """解析标准HTML提取正文."""
        result = await plugin.parse(SAMPLE_HTML, "https://example.com")
        assert "First paragraph" in result["content"]
        assert "Second paragraph" in result["content"]

    @pytest.mark.asyncio
    async def test_parse_extracts_metadata(self, plugin):
        """解析标准HTML提取元数据."""
        result = await plugin.parse(SAMPLE_HTML, "https://example.com")
        assert result["metadata"]["description"] == "A test page"
        assert result["metadata"]["keywords"] == "test,example"
        assert result["metadata"]["author"] == "Tester"

    @pytest.mark.asyncio
    async def test_parse_empty_html(self, plugin):
        """解析空HTML不报错."""
        result = await plugin.parse(EMPTY_HTML, "https://example.com")
        assert result["content"] == ""

    @pytest.mark.asyncio
    async def test_parse_title_fallback_to_h1(self, plugin):
        """title标签为空时回退到h1."""
        result = await plugin.parse(HTML_NO_TITLE, "https://example.com")
        assert result["title"] == "Fallback H1 Title"

    @pytest.mark.asyncio
    async def test_parse_title_fallback_to_untitled(self, plugin):
        """无title和h1时返回Untitled."""
        result = await plugin.parse(HTML_NO_TITLE_NO_H1, "https://example.com")
        assert result["title"] == "Untitled"


class TestGenericPluginDiscoverLinks:
    """GenericPlugin.discover_links 链接发现测试."""

    @pytest.fixture
    def plugin(self):
        return GenericPlugin()

    @pytest.mark.asyncio
    async def test_discover_same_domain_links(self, plugin):
        """发现同域名链接."""
        links = await plugin.discover_links(SAMPLE_HTML, "https://example.com")
        assert "https://example.com/page2" in links
        assert "https://example.com/page3" in links

    @pytest.mark.asyncio
    async def test_exclude_external_links(self, plugin):
        """排除外部域名链接."""
        links = await plugin.discover_links(SAMPLE_HTML, "https://example.com")
        assert "https://other.com/external" not in links

    @pytest.mark.asyncio
    async def test_resolve_relative_urls(self, plugin):
        """相对路径解析为绝对URL."""
        links = await plugin.discover_links(SAMPLE_HTML, "https://example.com")
        # /page2 should be resolved to https://example.com/page2
        assert any("example.com/page2" in link for link in links)

    @pytest.mark.asyncio
    async def test_deduplicate_links(self, plugin):
        """链接去重."""
        html = """
        <html><body>
        <a href="/same">Link 1</a>
        <a href="/same">Link 2</a>
        </body></html>
        """
        links = await plugin.discover_links(html, "https://example.com")
        same_links = [l for l in links if l.endswith("/same")]
        assert len(same_links) == 1

    @pytest.mark.asyncio
    async def test_remove_fragments(self, plugin):
        """移除URL中的fragment."""
        html = '<html><body><a href="/page#section1">Link</a></body></html>'
        links = await plugin.discover_links(html, "https://example.com")
        for link in links:
            assert "#" not in link

    @pytest.mark.asyncio
    async def test_empty_html_no_links(self, plugin):
        """空HTML返回空链接列表."""
        links = await plugin.discover_links(EMPTY_HTML, "https://example.com")
        assert links == []


class TestGenericPluginHelpers:
    """GenericPlugin 辅助方法测试."""

    def test_is_same_domain_true(self):
        """同域名判断为True."""
        plugin = GenericPlugin()
        assert plugin._is_same_domain(
            "https://example.com/a", "https://example.com/b"
        ) is True

    def test_is_same_domain_false(self):
        """不同域名判断为False."""
        plugin = GenericPlugin()
        assert plugin._is_same_domain(
            "https://a.com/x", "https://b.com/y"
        ) is False

    def test_is_same_domain_with_subdomain(self):
        """子域名视为不同域名."""
        plugin = GenericPlugin()
        assert plugin._is_same_domain(
            "https://sub.example.com/a", "https://example.com/b"
        ) is False

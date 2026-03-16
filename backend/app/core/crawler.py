"""Crawler engine - 爬取引擎."""
import asyncio
import logging
import random
import hashlib
from typing import Optional, Set
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import settings
from app.models.task import Task
from app.models.source import Source, CrawlMode
from app.models.result import CrawlResult
from app.plugins.base import CrawlerPlugin
from app.plugins.generic import GenericPlugin

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """爬取引擎，负责执行爬取任务."""

    # User-Agent池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        """初始化爬取引擎."""
        self.plugin_cache: dict[int, CrawlerPlugin] = {}  # plugin_id -> 插件实例缓存

        # 单域名并发控制（域名 -> Semaphore）
        self.domain_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(2)  # 每个域名最多2个并发
        )

        # 请求限速（域名 -> 上次请求时间）
        self.last_request_time: dict[str, float] = {}

        # 循环链接检测（信源ID -> URL集合）
        self.visited_urls: dict[int, Set[str]] = defaultdict(set)

    def _load_plugin_by_id(self, plugin_id: int, db: Session) -> Optional[CrawlerPlugin]:
        """
        根据 plugin_id 从数据库加载插件.

        Args:
            plugin_id: 插件ID
            db: 数据库会话

        Returns:
            插件实例，失败返回 None
        """
        # 检查缓存
        if plugin_id in self.plugin_cache:
            return self.plugin_cache[plugin_id]

        from app.models.plugin import Plugin

        plugin_record = db.query(Plugin).filter(
            Plugin.id == plugin_id,
            Plugin.enabled == True
        ).first()

        if not plugin_record:
            logger.error(f"Plugin {plugin_id} not found or disabled")
            return None

        try:
            # 动态导入插件类
            module_path, class_name = plugin_record.plugin_class.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            plugin_class = getattr(module, class_name)

            # 实例化插件并缓存
            plugin_instance = plugin_class()
            self.plugin_cache[plugin_id] = plugin_instance

            logger.info(f"Loaded plugin: {plugin_record.name} (id={plugin_id})")
            return plugin_instance

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return None

    def get_plugin(self, source: Source, db: Session) -> CrawlerPlugin:
        """
        获取信源对应的插件.

        Args:
            source: 信源对象
            db: 数据库会话

        Returns:
            插件实例
        """
        # 如果指定了 plugin_id，尝试加载对应插件
        if source.plugin_id:
            plugin = self._load_plugin_by_id(source.plugin_id, db)
            if plugin:
                return plugin
            logger.warning(f"Failed to load plugin {source.plugin_id}, falling back to GenericPlugin")

        # 默认使用 GenericPlugin
        if 0 not in self.plugin_cache:
            self.plugin_cache[0] = GenericPlugin()

        return self.plugin_cache[0]

    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent."""
        return random.choice(self.USER_AGENTS)

    def _get_domain(self, url: str) -> str:
        """从URL提取域名."""
        return urlparse(url).netloc

    async def _rate_limit(self, domain: str):
        """
        请求限速.

        Args:
            domain: 域名
        """
        if domain in self.last_request_time:
            elapsed = asyncio.get_event_loop().time() - self.last_request_time[domain]
            wait_time = settings.crawler_rate_limit - elapsed
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)

        self.last_request_time[domain] = asyncio.get_event_loop().time()

    def _is_visited(self, source_id: int, url: str) -> bool:
        """
        检查URL是否已访问（循环检测）.

        Args:
            source_id: 信源ID
            url: URL

        Returns:
            是否已访问
        """
        # 使用URL哈希来节省内存
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return url_hash in self.visited_urls[source_id]

    def _mark_visited(self, source_id: int, url: str):
        """
        标记URL为已访问.

        Args:
            source_id: 信源ID
            url: URL
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.visited_urls[source_id].add(url_hash)

    async def crawl(self, task: Task, db: Session) -> Optional[CrawlResult]:
        """
        执行爬取任务.

        Args:
            task: 任务对象
            db: 数据库会话

        Returns:
            爬取结果对象，失败返回None
        """
        try:
            # 获取信源配置
            source = db.query(Source).filter(Source.id == task.source_id).first()
            if not source:
                logger.error(f"Source {task.source_id} not found")
                return None

            # 获取插件
            plugin = self.get_plugin(source, db)

            # 获取目标URL
            url = task.url or source.url
            if not url:
                logger.error(f"No URL for task {task.id}")
                return None

            # 循环检测
            if self._is_visited(source.id, url):
                logger.warning(f"URL already visited: {url}")
                return None

            logger.info(f"Crawling URL: {url}")

            # 获取域名
            domain = self._get_domain(url)

            # 单域名并发控制
            async with self.domain_semaphores[domain]:
                # 请求限速
                await self._rate_limit(domain)

                # 获取随机User-Agent
                user_agent = self._get_random_user_agent()

                # 更新插件配置
                plugin.config["user_agent"] = user_agent

                # 1. Fetch页面
                html = await plugin.fetch(url)

                # 标记为已访问
                self._mark_visited(source.id, url)

            # 2. Parse内容
            parsed_data = await plugin.parse(html, url)

            # 3. 保存爬取结果
            crawl_result = CrawlResult(
                task_id=task.id,
                source_id=source.id,
                url=url,
                title=parsed_data.get("title"),
                content=parsed_data.get("content"),
                raw_html=html if source.config and source.config.get("save_html") else None,
                meta_data=parsed_data.get("metadata"),
                created_at=datetime.utcnow(),
            )
            db.add(crawl_result)
            db.commit()

            logger.info(f"Crawl result saved: {crawl_result.id}")

            # 4. 如果是整站爬取，或插件本身支持链接发现（如 RSS），则发现新链接并创建子任务
            if source.crawl_mode == CrawlMode.FULL_SITE or plugin.supports_link_discovery():
                await self._handle_full_site_crawl(
                    task, source, plugin, html, url, db
                )

            return crawl_result

        except Exception as e:
            logger.error(f"Crawl failed for task {task.id}: {e}", exc_info=True)
            raise

    async def _handle_full_site_crawl(
        self,
        parent_task: Task,
        source: Source,
        plugin: CrawlerPlugin,
        html: str,
        base_url: str,
        db: Session,
    ):
        """
        处理整站爬取，发现新链接并创建子任务.

        Args:
            parent_task: 父任务
            source: 信源对象
            plugin: 插件实例
            html: 页面HTML
            base_url: 基础URL
            db: 数据库会话
        """
        try:
            # 获取配置
            config = source.config or {}
            max_depth = config.get("max_depth", settings.crawler_max_depth)
            max_pages = config.get("max_pages", 100)

            # 计算当前深度
            current_depth = parent_task.payload.get("depth", 0) if parent_task.payload else 0

            # 检查深度限制
            if current_depth >= max_depth:
                logger.info(f"Reached max depth {max_depth}, stop discovering links")
                return

            # 检查页面数量限制
            total_tasks = db.query(Task).filter(
                Task.source_id == source.id,
                Task.type == "crawl"
            ).count()

            if total_tasks >= max_pages:
                logger.info(f"Reached max pages {max_pages}, stop discovering links")
                return

            # 发现新链接
            links = await plugin.discover_links(html, base_url)
            logger.info(f"Discovered {len(links)} links from {base_url}")

            # 过滤链接
            filtered_links = []
            for link in links:
                # 跳过已访问的URL（循环检测）
                if self._is_visited(source.id, link):
                    continue

                # 跳过已在数据库中的URL
                existing = db.query(Task).filter(
                    Task.source_id == source.id,
                    Task.url == link
                ).first()
                if existing:
                    continue

                # URL模式过滤
                if "url_pattern" in config:
                    import re
                    if not re.search(config["url_pattern"], link):
                        continue

                # 排除模式过滤
                if "exclude_pattern" in config:
                    import re
                    if re.search(config["exclude_pattern"], link):
                        continue

                filtered_links.append(link)

            logger.info(f"Found {len(filtered_links)} new links to crawl after filtering")

            # 创建子任务
            from app.core.scheduler import get_scheduler
            scheduler = get_scheduler()

            created_count = 0
            for link in filtered_links[:max_pages - total_tasks]:  # 限制数量
                # 创建子任务
                child_task = Task(
                    type="crawl",
                    status="pending",
                    priority=max(parent_task.priority - 1, 0),  # 子任务优先级降低，最低为0
                    source_id=source.id,
                    parent_task_id=parent_task.id,
                    url=link,
                    payload={"depth": current_depth + 1},
                    created_at=datetime.utcnow(),
                )
                db.add(child_task)
                db.flush()  # 获取ID

                # 提交到调度器
                await scheduler.submit_task(child_task.id, priority=child_task.priority)
                created_count += 1

            db.commit()
            logger.info(f"Created {created_count} child tasks")

        except Exception as e:
            logger.error(f"Failed to handle full site crawl: {e}", exc_info=True)

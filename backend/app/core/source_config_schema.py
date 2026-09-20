"""Source config schema - 信源配置字段元数据（契约冻结）."""

# 按契约 §2 冻结的配置项定义

SINGLE_PAGE_SCHEMA = {
    "source_type": "single_page",
    "fields": [
        {
            "name": "content_selector",
            "type": "text",
            "label": "内容选择器",
            "default": "",
            "help": "CSS 选择器，留空自动提取正文",
            "advanced": True,
        },
        {
            "name": "timeout",
            "type": "number",
            "label": "请求超时(秒)",
            "default": 30,
            "min": 5,
            "max": 120,
            "help": "",
            "advanced": True,
        },
        {
            "name": "max_retries",
            "type": "number",
            "label": "重试次数",
            "default": 3,
            "min": 0,
            "max": 5,
            "help": "",
            "advanced": True,
        },
    ],
}

FULL_SITE_SCHEMA = {
    "source_type": "full_site",
    "fields": [
        {
            "name": "max_depth",
            "type": "number",
            "label": "最大深度",
            "default": 2,
            "min": 1,
            "max": 5,
            "help": "爬取子链接的层数",
            "advanced": False,
        },
        {
            "name": "max_pages",
            "type": "number",
            "label": "最大页数",
            "default": 50,
            "min": 1,
            "max": 500,
            "help": "总共爬取的页面上限",
            "advanced": False,
        },
        {
            "name": "same_domain_only",
            "type": "switch",
            "label": "仅同域名",
            "default": True,
            "help": "仅爬取与入口同域名的链接",
            "advanced": False,
        },
        {
            "name": "url_whitelist",
            "type": "textarea",
            "label": "URL 白名单",
            "default": "",
            "help": "每行一个正则，只爬匹配的 URL（可选）",
            "advanced": True,
        },
        {
            "name": "timeout",
            "type": "number",
            "label": "请求超时(秒)",
            "default": 30,
            "min": 5,
            "max": 120,
            "help": "",
            "advanced": True,
        },
        {
            "name": "max_retries",
            "type": "number",
            "label": "重试次数",
            "default": 3,
            "min": 0,
            "max": 5,
            "help": "",
            "advanced": True,
        },
    ],
}

RSS_SCHEMA = {
    "source_type": "rss",
    "fields": [
        {
            "name": "max_items",
            "type": "number",
            "label": "保留条目数",
            "default": 20,
            "min": 1,
            "max": 200,
            "help": "每次最多爬取的文章数",
            "advanced": False,
        },
        {
            "name": "fetch_full_content",
            "type": "switch",
            "label": "爬取全文",
            "default": True,
            "help": "关闭则只保留 feed 摘要",
            "advanced": False,
        },
        {
            "name": "timeout",
            "type": "number",
            "label": "请求超时(秒)",
            "default": 30,
            "min": 5,
            "max": 120,
            "help": "",
            "advanced": True,
        },
    ],
}

# Schema 注册表
CONFIG_SCHEMAS = {
    "single_page": SINGLE_PAGE_SCHEMA,
    "full_site": FULL_SITE_SCHEMA,
    "rss": RSS_SCHEMA,
}

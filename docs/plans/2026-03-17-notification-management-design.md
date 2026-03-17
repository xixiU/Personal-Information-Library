# 通知管理功能详细设计

> 设计日期: 2026-03-17
> 基于调研文档: [notification-management-research.md](./2026-03-17-notification-management-research.md)

## 一、功能概述

### 1.1 目标

在分类管理基础上增加通知能力，当精炼产生符合条件的新内容时，自动通过用户配置的渠道推送通知。

核心价值：从「人找信息」变为「信息找人」。

### 1.2 系统流程

```
Source → Task(crawl) → CrawlResult → Task(refine) → RefinedResult
                                                          ↓
                                              NotificationEngine.evaluate()
                                                          ↓
                                              匹配 Category 下的 NotificationRule
                                                          ↓
                                          ┌───────────────┼───────────────┐
                                          ↓               ↓               ↓
                                       即时发送        聚合入队        定时摘要(P2)
                                          ↓               ↓
                                     Notifier.send()  APScheduler延迟
                                          ↓               ↓
                                     NotificationLog  批量合并发送
```

### 1.3 触发点

精炼完成后触发（`refiner.py` 回调），此时具备完整信息：
- 质量评分 (quality_score)
- 关键词 (keywords)
- 摘要 (summary)
- 分类归属 (category)
- 原文链接 (url)

---

## 二、三种通知模式

### 2.1 即时通知（Instant）

每条精炼结果立即单独发送。

**适用场景**：
- 高质量内容（quality_score >= 高阈值），数量少但价值高
- 关键词匹配，命中即推
- 采集异常（本身低频）

**配置示例**：
```json
{"mode": "instant", "min_quality_score": 85}
{"mode": "instant", "keywords": ["GPT", "融资"]}
```

**流程**：精炼完成 → 条件匹配 → 立即调用 Notifier.send() → 写入 NotificationLog(status=success/failed)

### 2.2 聚合通知（Batch）

在时间窗口内收集多条结果，合并为一条汇总消息发送。

**适用场景**：
- 普通新内容通知，量大但不需要逐条看
- 避免通知轰炸

**聚合策略：时间窗口 + 数量上限，先到先触发**
- `batch_window`：时间窗口（秒），默认 1800（30分钟）
- `batch_max_count`：数量上限，默认 10，达到即发送不等窗口结束

**配置示例**：
```json
{"mode": "batch", "batch_window": 1800, "batch_max_count": 10}
{"mode": "batch", "batch_window": 3600, "batch_max_count": 20, "min_quality_score": 60}
```

**流程**：
```
精炼完成 → 条件匹配 → 写入 NotificationLog(status=pending)
                          ↓
              检查该 rule 是否已有活跃的 batch job
                ↓                    ↓
              没有                  有
                ↓                    ↓
    注册 APScheduler 延迟任务     检查 pending 数量
    (batch_window 秒后执行)           ↓
                                 >= batch_max_count?
                                   ↓          ↓
                                  是          否
                                   ↓          ↓
                              立即触发发送   等待窗口到期
```

**延迟任务执行逻辑**：
1. 查询该 rule 下所有 status=pending 的 NotificationLog
2. 按 refined_result 关联查询标题、摘要、评分
3. 合并为一条汇总消息
4. 调用 Notifier.send()
5. 批量更新 NotificationLog status → success/failed

**汇总消息格式（Telegram 示例）**：
```
📋 *IT技术* 新增 5 条内容

1. *深入理解 RAG 架构* ⭐92
2. *LLM 微调实战指南* ⭐87
3. *向量数据库选型对比* ⭐85
4. *Prompt Engineering 技巧* ⭐78
5. *AI Agent 框架概览* ⭐72

🔗 查看详情: http://localhost:5173/results
```

### 2.3 定时摘要（Scheduled）— Phase 2

按 cron 表达式定时汇总发送。

**适用场景**：低频关注的分类，每日/每周看一次即可。

**配置示例**：
```json
{"mode": "scheduled", "cron": "0 9 * * *"}
```

Phase 1 不实现，预留 mode 字段即可。

---

## 三、数据模型设计

### 3.1 NotificationChannel（通知渠道）

```python
class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    channel_type = Column(String(20), nullable=False)  # webhook / telegram
    config = Column(JSON, nullable=False, default={})
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    rules = relationship("NotificationRule", back_populates="channel")
```

**channel_type 枚举**：
- `webhook` — 通用 HTTP Webhook
- `telegram` — Telegram Bot

**config 字段结构**：

Webhook:
```json
{
  "url": "https://example.com/webhook",
  "method": "POST",
  "headers": {"Authorization": "Bearer xxx"},
  "body_template": null,
  "secret": "hmac_secret_key"
}
```

Telegram:
```json
{
  "bot_token": "123456:ABC-DEF",
  "chat_id": "-1001234567890",
  "parse_mode": "Markdown",
  "disable_preview": false,
  "disable_notification": false
}
```

### 3.2 NotificationRule（通知规则）

```python
class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), nullable=False)
    rule_type = Column(String(30), nullable=False)  # new_content / quality_threshold / keyword_match
    notify_mode = Column(String(20), nullable=False, default="instant")  # instant / batch / scheduled
    conditions = Column(JSON, nullable=False, default={})
    message_template = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    category = relationship("Category", lazy="joined")
    channel = relationship("NotificationChannel", back_populates="rules", lazy="joined")
    logs = relationship("NotificationLog", back_populates="rule")
```

**rule_type 枚举**：
- `new_content` — 新内容通知（无额外条件）
- `quality_threshold` — 质量阈值
- `keyword_match` — 关键词匹配

**notify_mode 枚举**：
- `instant` — 即时发送
- `batch` — 聚合发送
- `scheduled` — 定时摘要（P2）

**conditions 字段结构**：
```json
// 即时 + 新内容
{"mode": "instant"}

// 即时 + 质量阈值
{"mode": "instant", "min_quality_score": 85}

// 即时 + 关键词
{"mode": "instant", "keywords": ["AI", "LLM"]}

// 聚合 + 新内容
{"mode": "batch", "batch_window": 1800, "batch_max_count": 10}

// 聚合 + 质量阈值
{"mode": "batch", "batch_window": 1800, "batch_max_count": 10, "min_quality_score": 60}
```

### 3.3 NotificationLog（通知日志）

```python
class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("notification_rules.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), nullable=False)
    refined_result_id = Column(Integer, ForeignKey("refined_results.id"), nullable=True)
    batch_id = Column(String(36), nullable=True)   # 聚合批次 ID（UUID），同批次共享
    status = Column(String(20), nullable=False, default="pending")  # pending / success / failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    rule = relationship("NotificationRule", back_populates="logs")
```

**status 枚举**：
- `pending` — 等待发送（聚合模式下入队）
- `success` — 发送成功
- `failed` — 发送失败

**batch_id**：聚合模式专用，同一批次的日志共享同一个 UUID，便于查询和关联。

### 3.4 模型关系图

```
Category ──1:N──→ NotificationRule ──N:1──→ NotificationChannel
                       │
                       │ 1:N
                       ↓
                 NotificationLog ──N:1──→ RefinedResult
```

---

## 四、后端架构设计

### 4.1 文件结构

```
backend/app/
├── core/
│   └── notifier.py              # 通知引擎（评估、调度、聚合）
├── notifiers/
│   ├── __init__.py
│   ├── base.py                  # BaseNotifier 抽象基类
│   ├── webhook.py               # WebhookNotifier
│   └── telegram.py              # TelegramNotifier
├── models/
│   └── notification.py          # 3 个模型定义
├── schemas/
│   └── notification.py          # Pydantic schemas
└── api/
    ├── notification_channels.py # 渠道 CRUD API
    └── notification_rules.py    # 规则 CRUD API（挂在 categories 下）
```

### 4.2 BaseNotifier 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class NotificationMessage:
    """通知消息数据"""
    title: str
    summary: str
    url: str
    quality_score: Optional[int]
    keywords: list[str]
    category_name: str
    source_name: str
    timestamp: str

@dataclass
class BatchNotificationMessage:
    """聚合通知消息数据"""
    category_name: str
    items: list[NotificationMessage]
    total_count: int

class BaseNotifier(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """发送单条通知"""
        pass

    @abstractmethod
    async def send_batch(self, message: BatchNotificationMessage) -> bool:
        """发送聚合通知"""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """验证配置，返回 (是否合法, 错误信息)"""
        pass

    @abstractmethod
    async def send_test(self) -> bool:
        """发送测试消息"""
        pass
```

### 4.3 WebhookNotifier

```python
class WebhookNotifier(BaseNotifier):
    async def send(self, message: NotificationMessage) -> bool:
        url = self.config["url"]
        method = self.config.get("method", "POST")
        headers = self.config.get("headers", {})
        secret = self.config.get("secret")
        body_template = self.config.get("body_template")

        # 渲染消息体
        body = self._render_body(message, body_template)

        # HMAC 签名
        if secret:
            signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        # 发送请求（重试 3 次，指数退避）
        async with httpx.AsyncClient(timeout=10) as client:
            for attempt in range(3):
                try:
                    resp = await client.request(method, url, content=body, headers=headers)
                    resp.raise_for_status()
                    return True
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
            return False
```

### 4.4 TelegramNotifier

```python
class TelegramNotifier(BaseNotifier):
    API_BASE = "https://api.telegram.org/bot{token}"

    async def send(self, message: NotificationMessage) -> bool:
        text = self._format_message(message)
        return await self._send_message(text)

    async def send_batch(self, message: BatchNotificationMessage) -> bool:
        text = self._format_batch_message(message)
        return await self._send_message(text)

    async def _send_message(self, text: str) -> bool:
        url = f"{self.API_BASE.format(token=self.config['bot_token'])}/sendMessage"
        payload = {
            "chat_id": self.config["chat_id"],
            "text": text,
            "parse_mode": self.config.get("parse_mode", "Markdown"),
            "disable_web_page_preview": self.config.get("disable_preview", False),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
```

### 4.5 通知引擎（NotificationEngine）

```python
class NotificationEngine:
    def __init__(self, scheduler: APScheduler):
        self.scheduler = scheduler
        self._notifiers = {
            "webhook": WebhookNotifier,
            "telegram": TelegramNotifier,
        }
        self._active_batch_jobs: dict[int, str] = {}  # rule_id → job_id

    async def evaluate(self, refined_result: RefinedResult, db: Session):
        """精炼完成后调用，评估并触发通知"""
        # 1. 查询关联的 category
        category_id = self._get_category_id(refined_result, db)
        if not category_id:
            return

        # 2. 查询该 category 下所有 enabled 的规则
        rules = db.query(NotificationRule).filter(
            NotificationRule.category_id == category_id,
            NotificationRule.enabled == True,
            NotificationRule.channel.has(NotificationChannel.enabled == True),
        ).all()

        # 3. 逐条评估
        for rule in rules:
            if not self._match_conditions(rule, refined_result):
                continue

            # 4. 去重检查
            exists = db.query(NotificationLog).filter(
                NotificationLog.rule_id == rule.id,
                NotificationLog.refined_result_id == refined_result.id,
            ).first()
            if exists:
                continue

            # 5. 根据 notify_mode 分发
            if rule.notify_mode == "instant":
                await self._send_instant(rule, refined_result, db)
            elif rule.notify_mode == "batch":
                await self._enqueue_batch(rule, refined_result, db)

    def _match_conditions(self, rule: NotificationRule, result: RefinedResult) -> bool:
        """评估触发条件"""
        conditions = rule.conditions or {}

        # 质量阈值
        min_score = conditions.get("min_quality_score")
        if min_score and (result.quality_score is None or result.quality_score < min_score):
            return False

        # 关键词匹配
        keywords = conditions.get("keywords")
        if keywords:
            result_keywords = (result.keywords or "").lower()
            result_summary = (result.summary or "").lower()
            if not any(kw.lower() in result_keywords or kw.lower() in result_summary for kw in keywords):
                return False

        return True

    async def _send_instant(self, rule, refined_result, db):
        """即时发送"""
        notifier = self._get_notifier(rule.channel)
        message = self._build_message(refined_result, rule, db)
        success = await notifier.send(message)

        log = NotificationLog(
            rule_id=rule.id,
            channel_id=rule.channel_id,
            refined_result_id=refined_result.id,
            status="success" if success else "failed",
            sent_at=datetime.utcnow() if success else None,
        )
        db.add(log)
        db.commit()

    async def _enqueue_batch(self, rule, refined_result, db):
        """聚合入队"""
        # 写入 pending 日志
        batch_id = self._active_batch_jobs.get(rule.id)
        if not batch_id:
            batch_id = str(uuid.uuid4())
            self._active_batch_jobs[rule.id] = batch_id

        log = NotificationLog(
            rule_id=rule.id,
            channel_id=rule.channel_id,
            refined_result_id=refined_result.id,
            batch_id=batch_id,
            status="pending",
        )
        db.add(log)
        db.commit()

        # 检查是否达到数量上限
        batch_max = rule.conditions.get("batch_max_count", 10)
        pending_count = db.query(NotificationLog).filter(
            NotificationLog.rule_id == rule.id,
            NotificationLog.batch_id == batch_id,
            NotificationLog.status == "pending",
        ).count()

        if pending_count >= batch_max:
            # 立即触发
            await self._flush_batch(rule.id, batch_id, db)
        elif rule.id not in self._active_batch_jobs or not self._has_scheduled_job(rule.id):
            # 注册延迟任务
            batch_window = rule.conditions.get("batch_window", 1800)
            self.scheduler.add_job(
                self._flush_batch_job,
                trigger="date",
                run_date=datetime.utcnow() + timedelta(seconds=batch_window),
                args=[rule.id, batch_id],
                id=f"batch_{rule.id}_{batch_id}",
                replace_existing=True,
            )

    async def _flush_batch(self, rule_id, batch_id, db):
        """执行聚合发送"""
        # 查询 pending 日志
        logs = db.query(NotificationLog).filter(
            NotificationLog.rule_id == rule_id,
            NotificationLog.batch_id == batch_id,
            NotificationLog.status == "pending",
        ).all()

        if not logs:
            return

        rule = db.query(NotificationRule).get(rule_id)
        notifier = self._get_notifier(rule.channel)

        # 构建聚合消息
        items = []
        for log in logs:
            result = db.query(RefinedResult).get(log.refined_result_id)
            if result:
                items.append(self._build_message(result, rule, db))

        batch_msg = BatchNotificationMessage(
            category_name=rule.category.name,
            items=items,
            total_count=len(items),
        )

        success = await notifier.send_batch(batch_msg)

        # 更新日志状态
        now = datetime.utcnow()
        for log in logs:
            log.status = "success" if success else "failed"
            log.sent_at = now if success else None
        db.commit()

        # 清理 batch 状态
        if rule_id in self._active_batch_jobs:
            del self._active_batch_jobs[rule_id]
```

### 4.6 精炼流程集成

在 `refiner.py` 精炼完成后添加通知触发：

```python
# refiner.py - refine() 方法末尾
async def refine(self, crawl_result_id: int, db: Session, ...):
    # ... 现有精炼逻辑 ...
    refined_result = RefinedResult(...)
    db.add(refined_result)
    db.commit()

    # 触发通知评估（异步，不阻塞主流程）
    try:
        await self.notification_engine.evaluate(refined_result, db)
    except Exception as e:
        logger.warning(f"通知评估失败: {e}")  # 不影响精炼结果
```

---

## 五、消息模板设计

### 5.1 模板变量

所有渠道共享同一套模板变量，由 `NotificationMessage` 数据类提供：

| 变量 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `{{title}}` | string | 精炼结果标题 | "深入理解 RAG 架构" |
| `{{summary}}` | string | AI 生成的摘要 | "本文介绍了 RAG 的核心原理..." |
| `{{url}}` | string | 原文链接 | "https://example.com/article" |
| `{{quality_score}}` | int/null | 质量评分 (0-100) | 85 |
| `{{keywords}}` | string | 关键词（逗号分隔） | "RAG, LLM, 向量数据库" |
| `{{category_name}}` | string | 分类名称 | "IT技术" |
| `{{source_name}}` | string | 信源名称 | "Hacker News" |
| `{{timestamp}}` | string | 精炼完成时间 (ISO 8601) | "2026-03-17T10:30:00Z" |

聚合消息额外变量：

| 变量 | 类型 | 说明 |
|------|------|------|
| `{{total_count}}` | int | 本批次内容总数 |
| `{{items}}` | list | 内容列表（每项包含上述所有字段） |

### 5.2 默认消息模板

Phase 1 每个渠道内置默认模板，用户无需配置即可使用。

#### Webhook 默认模板（JSON）

单条即时消息：
```json
{
  "event": "new_content",
  "category": "{{category_name}}",
  "source": "{{source_name}}",
  "title": "{{title}}",
  "summary": "{{summary}}",
  "url": "{{url}}",
  "quality_score": {{quality_score}},
  "keywords": "{{keywords}}",
  "timestamp": "{{timestamp}}"
}
```

聚合消息：
```json
{
  "event": "batch_content",
  "category": "{{category_name}}",
  "total_count": {{total_count}},
  "items": [
    {
      "title": "{{title}}",
      "url": "{{url}}",
      "quality_score": {{quality_score}},
      "summary": "{{summary}}"
    }
  ],
  "timestamp": "{{timestamp}}"
}
```

#### Telegram 默认模板（Markdown）

单条即时消息：
```
📌 *{{category_name}}*

*{{title}}*
{{summary}}

⭐ 质量评分: {{quality_score}}/100
🏷 关键词: {{keywords}}
📡 来源: {{source_name}}
🔗 [查看原文]({{url}})
```

聚合消息：
```
📋 *{{category_name}}* 新增 {{total_count}} 条内容

{% for item in items %}
{{loop.index}}. *{{item.title}}* ⭐{{item.quality_score}}
   {{item.summary[:80]}}...
   🔗 [原文]({{item.url}})
{% endfor %}
```

### 5.3 自定义模板策略

**Phase 1：规则级 message_template 覆盖**

NotificationRule 已有 `message_template` 字段（Text, nullable）。逻辑：
- `message_template` 为空 → 使用渠道默认模板
- `message_template` 非空 → 使用自定义模板

模板渲染引擎使用简单的字符串替换（`{{var}}` → 值），不引入 Jinja2 等重依赖。聚合消息的 items 循环在代码中处理，模板只定义单条格式。

**Phase 2：完整模板编辑器**
- 前端提供可视化模板编辑器（带变量插入按钮和实时预览）
- 支持 Jinja2 语法（条件判断、循环）
- 渠道级默认模板可修改

### 5.4 模板渲染流程

```
NotificationEngine._render_message(rule, refined_result, db)
    ↓
获取模板: rule.message_template || DEFAULT_TEMPLATES[channel_type]
    ↓
构建变量字典: {title, summary, url, quality_score, ...}
    ↓
字符串替换: re.sub(r'\{\{(\w+)\}\}', lambda m: vars[m.group(1)], template)
    ↓
渠道特殊处理:
  - Telegram: 转义 Markdown 特殊字符 (*_[]()~`>#+-=|{}.!)
  - Webhook: 确保 JSON 合法（数值类型不加引号）
    ↓
返回渲染后的消息文本
```

### 5.5 前端模板配置

在通知规则添加/编辑弹窗中，「自定义模板」区域设计：

```
┌─ 消息模板 ─────────────────────────────────┐
│                                              │
│  ○ 使用默认模板    ● 自定义模板              │
│                                              │
│  ┌─ 可用变量 ──────────────────────────┐    │
│  │ [title] [summary] [url]             │    │
│  │ [quality_score] [keywords]          │    │
│  │ [category_name] [source_name]       │    │
│  │ [timestamp]                         │    │
│  │         点击变量标签插入到模板 ↓      │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  ┌─ 模板内容 ──────────────────────────┐    │
│  │ 📌 *{{category_name}}*              │    │
│  │                                      │    │
│  │ *{{title}}*                          │    │
│  │ {{summary}}                          │    │
│  │                                      │    │
│  │ ⭐ 评分: {{quality_score}}/100       │    │
│  │ 🔗 [原文]({{url}})                  │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  [预览效果]                                  │
└──────────────────────────────────────────────┘
```

功能说明：
- 默认选中「使用默认模板」，message_template 存 null
- 切换到「自定义模板」后显示编辑区域，预填默认模板内容供修改
- 变量标签可点击，自动插入 `{{变量名}}` 到光标位置
- 「预览效果」按钮用模拟数据渲染模板，展示最终效果（纯前端渲染，不调用后端）

---

## 六、API 接口设计

### 6.1 通知渠道 API

```
POST   /api/notification-channels
  Body: {name, channel_type, config, enabled?}
  Response: NotificationChannelResponse

GET    /api/notification-channels
  Query: skip, limit
  Response: list[NotificationChannelResponse]
  注意: config 中的敏感字段脱敏（bot_token → "***", secret → "***"）

GET    /api/notification-channels/{id}
  Response: NotificationChannelResponse

PUT    /api/notification-channels/{id}
  Body: {name?, channel_type?, config?, enabled?}
  Response: NotificationChannelResponse

DELETE /api/notification-channels/{id}
  前置检查: 是否有关联的 NotificationRule
  Response: 204

POST   /api/notification-channels/{id}/test
  Response: {success: bool, message: str}
  说明: 发送一条测试消息验证渠道配置
```

### 6.2 通知规则 API

```
POST   /api/categories/{category_id}/notification-rules
  Body: {name, channel_id, rule_type, notify_mode, conditions, message_template?, enabled?}
  Response: NotificationRuleResponse

GET    /api/categories/{category_id}/notification-rules
  Response: list[NotificationRuleResponse]

PUT    /api/categories/{category_id}/notification-rules/{rule_id}
  Body: {name?, channel_id?, rule_type?, notify_mode?, conditions?, message_template?, enabled?}
  Response: NotificationRuleResponse

DELETE /api/categories/{category_id}/notification-rules/{rule_id}
  Response: 204
```

### 6.3 通知日志 API

```
GET    /api/notification-logs
  Query: rule_id?, channel_id?, status?, skip, limit
  Response: list[NotificationLogResponse]
```

---

## 七、前端页面设计

### 7.1 菜单结构调整

```
信源管理
├── 信源列表
└── 分类管理
任务管理
├── 爬取任务
└── 精炼任务
采集结果
系统设置          ← 新增
├── 通知渠道      ← 新增
└── 通知日志      ← 新增 (Phase 2)
```

### 7.2 通知渠道管理页面

路由: `/settings/channels`

功能：
- 渠道列表（表格：名称、类型、状态、操作）
- 新建渠道（弹窗：选择类型 → 动态表单）
- 编辑渠道
- 删除渠道（检查关联规则）
- 测试渠道（发送测试消息）

**动态表单**：根据 channel_type 渲染不同配置项
- Webhook: URL、Method(POST/PUT)、Headers(JSON编辑器)、Secret
- Telegram: Bot Token、Chat ID、Parse Mode(Markdown/HTML)、禁用预览

### 7.3 分类通知规则配置

位置：分类编辑弹窗 → 新增「通知规则」Tab

功能：
- 规则列表（卡片式：渠道名、触发条件、通知模式、状态）
- 添加规则（弹窗）
- 编辑/删除规则
- 启用/禁用开关

**添加规则弹窗字段**：
1. 规则名称（文本）
2. 通知渠道（下拉选择已创建的渠道）
3. 触发条件（下拉：新内容 / 质量阈值 / 关键词匹配）
   - 质量阈值：显示分数输入框
   - 关键词匹配：显示标签输入框
4. 通知模式（下拉：即时 / 聚合）
   - 聚合：显示窗口时间（分钟）和数量上限
5. 自定义模板（可选，文本域）

---

## 八、实施计划

### Phase 1 任务分解

| # | 任务 | 依赖 | 说明 |
|---|------|------|------|
| 1 | 数据模型定义 | 无 | notification.py: 3 个模型 + models/__init__.py 注册 |
| 2 | Pydantic Schema | #1 | schemas/notification.py: Create/Update/Response |
| 3 | BaseNotifier + WebhookNotifier | 无 | notifiers/base.py + webhook.py |
| 4 | TelegramNotifier | #3 | notifiers/telegram.py |
| 5 | NotificationEngine 核心 | #1, #3 | core/notifier.py: evaluate + instant + batch |
| 6 | 通知渠道 API | #1, #2 | api/notification_channels.py: CRUD + test |
| 7 | 通知规则 API | #1, #2 | api/notification_rules.py: CRUD |
| 8 | 精炼流程集成 | #5 | refiner.py 添加通知触发 |
| 9 | main.py 路由注册 | #6, #7 | 注册新路由 |
| 10 | 前端 API 客户端 | #6, #7 | api/notifications.ts |
| 11 | 通知渠道管理页面 | #10 | pages/NotificationChannels.tsx |
| 12 | 分类通知规则 Tab | #10 | CategoryList.tsx 增加通知规则 Tab |
| 13 | App.tsx 菜单和路由 | #11 | 新增系统设置菜单 |
| 14 | 端到端测试 | 全部 | 验证完整流程 |

### Phase 2（后续）
- 通知日志页面
- 关键词匹配规则
- 采集异常通知
- 自定义消息模板编辑器
- 定时摘要模式

---

## 九、技术风险与注意事项

| 风险 | 应对策略 |
|------|---------|
| Token/密钥泄露 | config 中 bot_token、secret 等字段 API 返回时脱敏（替换为 `***`），仅创建/更新时接收明文 |
| 通知发送失败 | 异步执行 + 重试 3 次（指数退避），失败写入 NotificationLog，不阻塞精炼主流程 |
| 批量精炼通知轰炸 | 聚合模式 batch_window + batch_max_count 双重控制 |
| Telegram API 限流 | Bot API 限制 30msg/s per chat，通过 NotificationEngine 内部队列控制发送速率 |
| 聚合窗口内服务重启 | pending 状态的 NotificationLog 在服务启动时检查，超过 batch_window 的自动触发发送 |
| 模板变量注入 | 变量替换时对 Markdown/HTML 特殊字符转义 |
| 渠道删除数据一致性 | 删除前检查关联规则，有关联则拒绝删除 |

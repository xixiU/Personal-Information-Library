# 分类通知管理功能调研

> 调研日期: 2026-03-17

## 一、功能需求分析

### 1.1 核心问题

当前系统完成了「采集 → 精炼 → 分类」的完整链路，但用户无法及时感知到新内容的产生。用户必须主动打开系统查看结果，这在信息时效性要求高的场景下体验较差。

### 1.2 功能定位

通知管理是分类管理的延伸能力——用户为某个分类配置通知规则后，当该分类下产生符合条件的新内容时，系统自动通过指定渠道推送通知。

**核心价值**: 从「人找信息」变为「信息找人」。

### 1.3 与现有架构的关系

```
Source → Task(crawl) → CrawlResult → Task(refine) → RefinedResult
                                                          ↓
                                              Category.notification_rules
                                                          ↓
                                                    触发通知发送
```

通知触发点在精炼完成后，因为此时才有：
- 质量评分 (quality_score)
- 关键词 (keywords)
- 摘要 (summary)
- 分类归属 (category)

---

## 二、使用场景

| 场景 | 触发条件 | 通知内容 | 优先级 |
|------|---------|---------|--------|
| 新内容通知 | 分类下有新的精炼结果 | 标题 + 摘要 + 链接 | P0 |
| 高质量内容 | quality_score >= 阈值 | 标题 + 摘要 + 评分 + 链接 | P0 |
| 关键词匹配 | 精炼结果包含指定关键词 | 标题 + 匹配关键词 + 摘要 | P1 |
| 采集异常 | 任务连续失败 N 次 | 信源名称 + 错误信息 | P1 |
| 定时摘要 | 按 cron 周期汇总 | 时间段内新增内容统计 | P2 |

---

## 三、通知渠道技术方案

### 3.1 Webhook（P0 - 首期实现）

**原理**: HTTP POST 请求，最通用的集成方式。

**配置参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| url | string | Webhook 接收地址 |
| method | enum | POST / PUT |
| headers | json | 自定义请求头（如 Authorization） |
| body_template | string | 消息体模板，支持变量替换 |
| secret | string | 可选，用于签名验证 |

**技术实现**:
- 使用 `httpx.AsyncClient` 发送异步请求
- 支持 HMAC-SHA256 签名（放在 `X-Signature-256` header）
- 超时 10s，失败重试 3 次，指数退避

**消息体模板变量**:
```json
{
  "title": "{{title}}",
  "summary": "{{summary}}",
  "url": "{{url}}",
  "quality_score": {{quality_score}},
  "keywords": {{keywords}},
  "category": "{{category_name}}",
  "source": "{{source_name}}",
  "timestamp": "{{timestamp}}"
}
```

### 3.2 Telegram Bot（P0 - 首期实现）

**原理**: 通过 Telegram Bot API 发送消息。

**配置参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| bot_token | string | Bot API Token |
| chat_id | string | 目标聊天 ID（用户/群组/频道） |
| parse_mode | enum | HTML / Markdown |
| disable_preview | bool | 是否禁用链接预览 |

**技术实现**:
- 调用 `https://api.telegram.org/bot{token}/sendMessage`
- 使用 `httpx.AsyncClient`，无需额外依赖
- 消息格式化为 Markdown/HTML
- 支持静默发送（disable_notification）

**消息模板示例**:
```
📌 *{{category_name}}* 新内容

*{{title}}*
{{summary}}

⭐ 质量评分: {{quality_score}}/100
🔗 [查看原文]({{url}})
```

### 3.3 其他渠道（P2 - 后续扩展）

| 渠道 | 实现方式 | 复杂度 | 备注 |
|------|---------|--------|------|
| 邮件 (SMTP) | `aiosmtplib` | 中 | 需配置 SMTP 服务器 |
| 钉钉机器人 | Webhook + 签名 | 低 | 与 Webhook 类似，加签名逻辑 |
| 企业微信 | Webhook | 低 | 与 Webhook 类似 |
| Slack | Webhook / Bot API | 低 | Incoming Webhook 最简单 |
| Bark (iOS) | HTTP GET | 极低 | `https://api.day.app/{key}/{title}/{body}` |

**扩展策略**: 采用插件化设计，首期实现 Webhook + Telegram，后续渠道通过新增 Notifier 插件扩展，无需修改核心逻辑。

---

## 四、数据模型设计

### 4.1 新增表

#### NotificationChannel（通知渠道）

```python
class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: int                    # 主键
    name: str                  # 渠道名称，如 "我的Telegram"
    channel_type: str          # 渠道类型: webhook / telegram / email
    config: JSON               # 渠道配置（加密存储敏感字段）
    enabled: bool              # 是否启用
    created_at: datetime
    updated_at: datetime
```

`config` 字段示例：
```json
// Webhook
{"url": "https://...", "method": "POST", "headers": {}, "secret": "xxx"}

// Telegram
{"bot_token": "123:ABC", "chat_id": "-100123", "parse_mode": "Markdown"}
```

#### NotificationRule（通知规则）

```python
class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: int                    # 主键
    category_id: int           # FK → categories.id
    channel_id: int            # FK → notification_channels.id
    rule_type: str             # 规则类型: new_content / quality_threshold / keyword_match
    conditions: JSON           # 触发条件
    message_template: str      # 可选，自定义消息模板
    enabled: bool              # 是否启用
    created_at: datetime
    updated_at: datetime
```

`conditions` 字段示例：
```json
// 新内容通知（无额外条件）
{}

// 质量阈值
{"min_quality_score": 80}

// 关键词匹配
{"keywords": ["AI", "LLM", "GPT"]}
```

#### NotificationLog（通知日志）

```python
class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: int                    # 主键
    rule_id: int               # FK → notification_rules.id
    channel_id: int            # FK → notification_channels.id
    refined_result_id: int     # FK → refined_results.id（可选）
    status: str                # success / failed / pending
    error_message: str         # 失败原因
    sent_at: datetime
```

### 4.2 模型关系

```
Category ──1:N──→ NotificationRule ──N:1──→ NotificationChannel
                       │
                       ↓
                 NotificationLog ──→ RefinedResult
```

一个分类可以配置多条通知规则，每条规则绑定一个通知渠道。同一个渠道可以被多条规则复用。

---

## 五、核心架构设计

### 5.1 通知引擎

```
backend/app/core/notifier.py          # 通知引擎主逻辑
backend/app/notifiers/                # 通知渠道插件目录
├── base.py                           # BaseNotifier 抽象基类
├── webhook.py                        # WebhookNotifier
└── telegram.py                       # TelegramNotifier
```

**BaseNotifier 接口**:
```python
class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """发送通知，返回是否成功"""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """验证渠道配置是否合法"""
        pass
```

### 5.2 触发流程

```
RefinedResult 创建完成
       ↓
notifier.evaluate(refined_result)
       ↓
查询该 category 下所有 enabled 的 NotificationRule
       ↓
逐条评估 conditions 是否满足
       ↓
满足 → 渲染消息模板 → 调用对应 channel 的 Notifier.send()
       ↓
写入 NotificationLog
```

**集成点**: 在 `refiner.py` 的精炼完成回调中调用 `notifier.evaluate()`。

### 5.3 防重复与限流

- 同一 refined_result + 同一 rule 只发送一次（通过 NotificationLog 去重）
- 每个 channel 限流：默认 30 条/分钟（可配置）
- 批量精炼场景：合并同一分类的多条结果为一条汇总通知

---

## 六、API 设计

### 6.1 通知渠道 API

```
POST   /api/notification-channels          # 创建渠道
GET    /api/notification-channels          # 列表
GET    /api/notification-channels/{id}     # 详情
PUT    /api/notification-channels/{id}     # 更新
DELETE /api/notification-channels/{id}     # 删除
POST   /api/notification-channels/{id}/test  # 发送测试通知
```

### 6.2 通知规则 API（挂在分类下）

```
POST   /api/categories/{id}/notification-rules          # 创建规则
GET    /api/categories/{id}/notification-rules          # 列表
PUT    /api/categories/{id}/notification-rules/{rule_id}  # 更新
DELETE /api/categories/{id}/notification-rules/{rule_id}  # 删除
```

### 6.3 通知日志 API

```
GET    /api/notification-logs              # 查询日志（支持按 channel/rule/status 筛选）
```

---

## 七、UI/UX 设计建议

### 7.1 通知渠道管理（独立页面）

位置：左侧菜单「系统设置」→「通知渠道」

```
┌─────────────────────────────────────────────────┐
│  通知渠道管理                        [+ 新建渠道] │
├─────────────────────────────────────────────────┤
│  名称          类型        状态     操作          │
│  我的Telegram  Telegram    ✅启用   测试 编辑 删除 │
│  监控Webhook   Webhook     ✅启用   测试 编辑 删除 │
│  备用邮箱      Email       ⏸禁用   测试 编辑 删除 │
└─────────────────────────────────────────────────┘
```

新建/编辑渠道弹窗：
- 选择渠道类型后，动态渲染对应的配置表单
- 「测试」按钮发送一条测试消息验证配置

### 7.2 分类通知规则（嵌入分类详情）

位置：分类管理 → 编辑分类 → 「通知规则」Tab

```
┌─────────────────────────────────────────────────┐
│  分类: AI 技术                                    │
│  [基本信息] [精炼配置] [通知规则]                    │
├─────────────────────────────────────────────────┤
│                                     [+ 添加规则] │
│                                                  │
│  ┌─ 规则 1 ──────────────────────────────────┐  │
│  │ 渠道: 我的Telegram                         │  │
│  │ 触发: 质量评分 ≥ 80                        │  │
│  │ 状态: ✅启用              [编辑] [删除]     │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌─ 规则 2 ──────────────────────────────────┐  │
│  │ 渠道: 监控Webhook                          │  │
│  │ 触发: 关键词匹配 [LLM, RAG]               │  │
│  │ 状态: ✅启用              [编辑] [删除]     │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

添加规则弹窗：
```
┌─────────────────────────────────┐
│  添加通知规则                     │
│                                  │
│  通知渠道:  [我的Telegram    ▼]  │
│                                  │
│  触发条件:  [质量阈值       ▼]   │
│                                  │
│  ┌─ 条件配置 ───────────────┐   │
│  │ 最低质量评分: [80]        │   │
│  └──────────────────────────┘   │
│                                  │
│  自定义模板: (可选)              │
│  ┌──────────────────────────┐   │
│  │                           │   │
│  └──────────────────────────┘   │
│                                  │
│         [取消]  [确定]           │
└─────────────────────────────────┘
```

### 7.3 通知日志（独立页面）

位置：左侧菜单「系统设置」→「通知日志」

展示最近的通知发送记录，支持按状态、渠道、分类筛选，方便排查问题。

---

## 八、实施优先级

### Phase 1（P0 - 核心能力）
1. 数据模型：NotificationChannel + NotificationRule + NotificationLog
2. 通知引擎核心：BaseNotifier + 规则评估逻辑
3. Webhook 通知器
4. Telegram 通知器
5. 精炼完成后的通知触发集成
6. 通知渠道管理 API + 前端页面
7. 分类通知规则 API + 前端（嵌入分类编辑）
8. 测试通知功能

### Phase 2（P1 - 增强体验）
1. 通知日志 API + 前端页面
2. 关键词匹配规则
3. 采集异常通知（任务失败触发）
4. 消息模板自定义
5. 限流与防重复机制

### Phase 3（P2 - 扩展渠道）
1. 邮件通知 (SMTP)
2. 钉钉/企业微信
3. Bark (iOS 推送)
4. 定时摘要通知（cron 汇总）

---

## 九、技术风险与注意事项

| 风险 | 应对策略 |
|------|---------|
| Token/密钥安全 | config 中的敏感字段加密存储，API 返回时脱敏 |
| 通知发送失败 | 异步重试 3 次 + 记录日志，不阻塞主流程 |
| 批量精炼导致通知轰炸 | 同分类短时间内合并为一条汇总通知 |
| Telegram API 限流 | 遵守 Bot API 限制（30msg/s），队列化发送 |
| 模板注入 | 变量替换时转义特殊字符 |

---

## 十、工作量估算

| 模块 | 预估 |
|------|------|
| 数据模型 + Migration | 小 |
| 通知引擎核心 | 中 |
| Webhook + Telegram 通知器 | 中 |
| 后端 API（渠道 + 规则 + 日志） | 中 |
| 前端页面（渠道管理 + 规则配置） | 中 |
| 精炼流程集成 | 小 |
| 测试 | 中 |
| **总计** | **中等规模** |

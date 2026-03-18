# 通知管理待实现功能

> 更新日期: 2026-03-17

## 已实现（Phase 1）

- ✅ NotificationChannel / NotificationRule / NotificationLog 数据模型
- ✅ 通知引擎：BaseNotifier + 规则评估 + 去重
- ✅ WebhookNotifier / TelegramNotifier / FeishuNotifier（消息卡片默认）
- ✅ 即时（instant）和聚合（batch）两种通知模式
- ✅ 通知渠道 CRUD API + 测试接口
- ✅ 分类通知规则 API
- ✅ 前端：通知渠道管理页面（含飞书消息格式选项）
- ✅ 精炼完成后自动触发通知

---

## 待实现

### Phase 2（P1 - 增强体验）

1. **通知日志页面**：查看历史发送记录，按状态/渠道/分类筛选
2. **采集异常通知**：任务连续失败 N 次时触发告警
3. **消息模板自定义**：前端可视化编辑模板，支持变量插入和实时预览

### Phase 3（P2 - 扩展渠道）

| 渠道 | 实现方式 | 备注 |
|------|---------|------|
| 钉钉机器人 | Webhook + 签名 | 与 Webhook 类似 |
| 企业微信 | Webhook | 与 Webhook 类似 |
| Bark (iOS) | HTTP GET | `https://api.day.app/{key}/{title}/{body}` |
| 邮件 (SMTP) | `aiosmtplib` | 需配置 SMTP 服务器 |
| 定时摘要 | cron 汇总 | 按周期汇总发送，非实时触发 |

## 技术风险与注意事项
| 风险 | 应对策略 |
|------|---------|
| Token/密钥泄露 | config 中 bot_token、secret 等字段 API 返回时脱敏（替换为 `***`），仅创建/更新时接收明文 |
| 通知发送失败 | 异步执行 + 重试 3 次（指数退避），失败写入 NotificationLog，不阻塞精炼主流程 |
| 批量精炼通知轰炸 | 聚合模式 batch_window + batch_max_count 双重控制 |
| Telegram API 限流 | Bot API 限制 30msg/s per chat，通过 NotificationEngine 内部队列控制发送速率 |
| 聚合窗口内服务重启 | pending 状态的 NotificationLog 在服务启动时检查，超过 batch_window 的自动触发发送 |
| 模板变量注入 | 变量替换时对 Markdown/HTML 特殊字符转义 |
| 渠道删除数据一致性 | 删除前检查关联规则，有关联则拒绝删除 |
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

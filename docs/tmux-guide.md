# Tmux 使用指南

项目使用 tmux 进行多窗口开发，方便查看不同 agent 的工作进程。

## 基本操作

```bash
# 查看所有会话
tmux ls

# 连接到会话
tmux attach -t <session-name>

# 创建新会话
tmux new -s <session-name>
```

## 窗口操作

在 tmux 会话中使用以下快捷键：

```bash
Ctrl+b c        # 创建新窗口
Ctrl+b n        # 切换到下一个窗口
Ctrl+b p        # 切换到上一个窗口
Ctrl+b 0-9      # 切换到指定编号的窗口
Ctrl+b w        # 列出所有窗口
Ctrl+b ,        # 重命名当前窗口
Ctrl+b &        # 关闭当前窗口
```

## 会话操作

```bash
Ctrl+b d        # 分离会话（后台运行）
Ctrl+b s        # 列出所有会话
Ctrl+b $        # 重命名会话
```

## 面板操作

```bash
Ctrl+b %        # 垂直分割面板
Ctrl+b "        # 水平分割面板
Ctrl+b 方向键   # 切换面板
Ctrl+b x        # 关闭当前面板
```

## 其他

```bash
Ctrl+b ?        # 显示所有快捷键
Ctrl+b [        # 进入复制模式（可滚动查看历史）
q               # 退出复制模式
```

## Claude Code Team Agent 使用场景

在使用 Claude Code 的 Team Agent 模式时，tmux 特别有用：

1. 为每个 agent 创建独立窗口，方便查看各自的工作进度
2. 后台运行长时间任务，分离会话后可以随时重新连接
3. 多面板同时查看前端、后端、测试等不同进程的输出

### 重新激活 Agent

如果 agent 退出，可以在原窗口中重新激活：

```bash
# 1. 连接到原会话
tmux attach -t <session-name>

# 2. 切换到对应窗口
Ctrl+b <窗口编号>

# 3. 在 Claude Code 中重新创建同名 agent
# 注意：agent 无法"恢复"，只能重新创建，之前的上下文会丢失
```

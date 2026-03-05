# 技术博客

一个基于 Jekyll 和 Chirpy 主题的技术博客，用于记录 AI Agent、软件工程等相关技术内容。

## 定位

- AI Agent 技术实践与思考
- 软件工程经验总结
- 技术问题解决记录


## 文章目录

### Effective AI Agent 系列

0. [构建 Agent：写在《Effective AI Agent》手册之前](_posts/2025-12-03-effective-ai-agent-pre.md)
1. [《Effective AI Agent》条目 1：优先在确定性任务中使用显式工作流](_posts/2025-12-07-effective-ai-agent-item01.md)
2. [《Effective AI Agent》条目 2：超越固定流程：用 Agent 解决开放性问题](_posts/2025-12-20-effective-ai-agent-item02.md)
3. [《Effective AI Agent》条目 3：以"问题空间"定义智能体边界，而非"模型能力"](_posts/2025-12-31-effective-ai-agent-item03.md)
4. [《Effective AI Agent》条目 4：把 Agent 模块化为 Planner/Executor/Memory，否则迟早写成意大利面条](_posts/2026-01-03-effective-ai-agent-item04.md)
5. [《Effective AI Agent》条目 5：实现可回放的 Orchestrator 以支撑调试与回归](_posts/2026-01-04-effective-ai-agent-item05.md)
6. [《Effective AI Agent》条目 6：把 ReAct 循环实现为受控的有限状态机](_posts/2026-01-05-effective-ai-agent-item06.md)
7. [《Effective AI Agent》条目 7：强制使用结构化输出作为组件契约](_posts/2026-01-06-effective-ai-agent-item07.md)
8. [《Effective AI Agent》条目 8：为错误进行分类建模，实现差异化重试](_posts/2026-01-07-effective-ai-agent-item08.md)
9. [《Effective AI Agent》条目 9：围绕 KV 缓存组织上下文降本提速](_posts/2026-01-08-effective-ai-agent-item09.md)
10. [《Effective AI Agent》条目 10：文件是 Agent 最可靠的记忆载体，比"无限上下文"更有效](_posts/2026-01-10-effective-ai-agent-item10.md)
11. [《Effective AI Agent》条目 11：为工具调用构建零信任的防御性校验](_posts/2026-03-03-effective-ai-agent-item11.md)


### 译作

- 【译】[AI 下半场](_posts/2025-04-11-The-Second-Half.md)
- 【译】[我们如何构建多智能体研究系统](_posts/2025-06-14-How_we_built_our_multi-agent_research%20system.md)
- 【译】[不要构建多智能体 (Multi-Agents)](_posts/2025-06-12-dont-build-multi-agents.md)
- 【译】[使用 Claude Agent SDK 构建代理](_posts/2025-09-29-building-agents-with-the-claude-agent-sdk.md)
- 【译】[Claude Code 凭什么这么好用？](_posts/2025-08-23-What_makes_Claude_Code_so_damn_good.md)

### Agent 架构分析

- [开源 Agent 架构的设计与实现之：OpenCode](_posts/2025-10-03-Agent-Analysis_opencode.md)
- [开源 Agent 架构的设计与实现之：Codex](_posts/2025-11-02-Agent-Analysis_Codex.md)

### 其他

- [Hello, Agent](_posts/2025-01-22-Hello-Agent.md)
- [记一次 AI 亲子互动：从"奶粉配方"到"小游戏"](_posts/2026-01-11-an-ai-assisted-parenting-journey.md)
- [Vibe Coding：新乐园还是潘多拉魔盒？](_posts/2025-04-20-vibe_coding_devp_macos_app.md)



## 服务启动

```bash
# 使用 rbenv 确保正确的 Ruby 版本
rbenv exec bundle exec jekyll serve
```

启动后访问：http://127.0.0.1:4000/

## 服务停止

在终端按 `Ctrl-C` 停止服务。

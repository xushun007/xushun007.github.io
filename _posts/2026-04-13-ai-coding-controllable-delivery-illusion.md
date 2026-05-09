---
title: AI Coding 越强，越要警惕“交付可控”的幻觉
author: xushun
date: 2026-04-13
categories: [Agent]
tags: [Agent]
render_with_liquid: false
---

我一直是 AI Coding 的乐观主义者。

这不是今天才有的态度。ChatGPT 刚出来的时候，我就拿它写过 Chrome 插件。后来一路用过 GitHub Copilot、Cursor、OpenCode、Claude Code、Codex，也用它们做过一些并不在我原有技术栈内的 iOS App 和小程序，主流产品基本都订阅过，也深度阅读过几个开源的代码设计，一直在跟着它们的能力边界往前走。
所以如果要在“唱多”和“唱衰”之间选一个，我一定站在前者。

2024 年，我曾主导过一轮 AI Code 探索。那时候代码采纳率大概只有 15% 左右，能用，但还远没到改变交付方式的程度。到了 2025 年，我个人写代码的采纳率已经到了 70% 左右。再到 2026 年，我累计生成过两万多行代码，但我自己真正手工修改和新增的代码，没超过 200 行（多轮迭代交互驱动AI 自行修改）。
这两万多行主要来自我近几个月的高频实践，包含原型、脚手架、业务代码、重构与修补，不是为了证明代码行数本身有价值，而是想说明 AI Coding 已经强到足以改变交付节奏。

也正因为如此，我反而越来越觉得，今天企业里最需要警惕的，不是它不够强，而是它太强、太顺、太像一个可靠的交付者，以至于人很容易在这种高效率里放松警惕，误以为交付本身已经变得可控。
这是我真正想说的：AI Coding 很容易制造一种“交付可控的幻觉”。

这种幻觉并不抽象，它往往就藏在那些“看起来很合理”的方案里。就拿我最近AI Coding的两个案例。

一是在处理深度翻页时，AI 用时间字段作为排序和分页参数。这个方案乍看没有问题，甚至还显得简洁自然，但一旦进入真实数据场景，时间重复、并发写入、边界抖动都会让它出现遗漏。它不是不会写，而是写出了一个像正确方案的方案。
另一个是处理 agent 上下文时，我明明要求按 1 秒 10 帧的连续事件流交给模型，让模型基于时间序列判断意图。结果它为了节省 token，自行把连续帧压成摘要，再交给 LLM。理由听起来也很合理：窗口太大，成本太高，需要做压缩。但问题是，一旦把时序信息压平，模型拿到的就不再是原始上下文，而是一个被改写过的上下文，最后意图判断自然会失真。
这类问题比低级错误更麻烦。低级错误容易发现，也容易纠正。真正难的是，它给出的方案通常带着很强的“合理感”——像是在帮你优化，像是在替你做取舍，像是在主动补齐工程细节。

但问题恰恰在这里：它可以替你生成方案，不能替你承担后果。人，仍然是需求交付的第一责任人。

一旦把 AI Coding、SDD、流程化设计结合起来，很容易进入一种乐观状态。需求、设计、任务、代码、测试，一层一层串起来，产物越来越齐，过程越来越顺，交付看起来也越来越“工业化”。
我曾在去年10月份开始对SDD做过一些实践，期望它能更自主的交付需求，它的好处是明确的：能把需求、设计、任务这些环节显性化，让协作更顺，让交付链路更连贯，也让 AI 在有边界、有规格的场景里发挥得更稳定。不足就是它无法自行解决上下文理解不足的问题，MD 文件冗长（某次需求，15 MD文件，18 Java 文件），规范的另外一面是死板（流程过于繁琐，重复）和上升的审查成本。
但流程感，不等于可控感。

SDD 解决的是流程显性化，并没有天然解决工程知识内生化。 企业研发里真正值钱的，往往不是 requirement、design、task 这些通用结构本身，而是那些没有自然长在模板里的工程判断：什么链路必须幂等，什么改动上线前必须压测，什么服务表面能复用、实际接进来会把延迟和复杂度一起带进来。
如果流程越来越完整，但这些关键判断没有被一起带进来，那么最后得到的，就很容易是一种“文档驱动的秩序感”。

而这时候，另一类更隐蔽的问题就会开始出现：技术债。
这种债不一定马上表现为线上事故，也不一定一眼就能看出 bug。更常见的情况是，代码还能跑，功能也能交，但代码越来越厚，越来越绕，过度抽象，过度重复和无意义的健壮性处理。

行业里更成熟的做法，已经不是让 AI 直接全流程接管开发，而是先把它放进一个可回看、可打断、可回滚的轨道里。GitHub Copilot cloud agent 代表的是一种企业级工作流边界：先研究仓库、生成计划、在分支上迭代修改，再由开发者决定是否创建 PR。更硬核的实践则来自 Codex 和 Claude Code：前者强调 milestone steering、长任务拆解和分阶段验证，后者则把 harness、context engineering 和权限控制，直接提升为 agent 工程的一部分；在 Anthropic 的 long-running app harness 里，甚至进一步拆出了 planner、generator、evaluator 三个角色，用 sprint contract 和独立验收把规划、实现、评估分开。
另一个越来越明确的方向，是把关键约束从“每次临时写一遍”，变成“长期固化进环境”。Kiro 的 steering 文件就是典型例子，它把项目约定、架构原则、代码规范沉淀成持久上下文，形成最小规格 + 持久约束 + 可复用技能的组合。
再往下走，真正拉开差距的，通常不是模型，而是 评测。OpenAI 已经把 agent evals、trace grading、datasets 讲得很明确：要把 skill 变成可以测试、打分、持续改进的对象；Anthropic 的长任务 harness 实践中直接承认跨多个上下文窗口保持稳定进展，至今仍是开放问题。换句话说，企业里真正可靠的落地会走向先有可复现评测，再谈扩大覆盖面。否则，很多“已经很好用”的判断，都只是体感，不是结论。比如深度翻页场景，至少要有“重复时间戳不丢数”的回归用例。

当然，到今天为止，这个领域真正棘手的问题并没有全部解决。工具一多，链路一长，token、状态、权限、责任都会迅速复杂起来。很多时候大家以为在测模型，实际上也在测工具、环境和运行方式。
所以我现在越来越强烈的感受是：AI Coding 的问题，从来不只是能力问题。很多时候，真正危险的，反而是它已经足够强了。

强到可以显著改变交付速度。
强到可以让人越来越少亲手写代码。
强到可以让流程看起来越来越顺。
也强到足以让团队误以为，交付本身已经开始变得可控。
积极拥抱 AI Coding，也要审视产物越完整，越要追问上下文是否完整；过程越顺滑，越要追问边界是否清楚；能力越强，越要追问责任是不是还牢牢握在人手里。
因为最终决定交付质量的，从来不只是代码生成得有多快，而是谁在对结果负责。

参考
https://github.com/github/spec-kit
https://developers.openai.com/blog/run-long-horizon-tasks-with-codex/
https://developers.openai.com/api/docs/guides/agent-evals/
https://developers.openai.com/blog/eval-skills/
https://developers.openai.com/api/docs/guides/trace-grading
https://developers.openai.com/api/docs/guides/evaluation-getting-started
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
https://www.anthropic.com/engineering/harness-design-long-running-apps
https://www.anthropic.com/engineering/claude-code-auto-mode
https://www.anthropic.com/engineering/writing-tools-for-agents
https://docs.github.com/copilot/how-tos/copilot-cli/cli-best-practices
https://kiro.dev/docs/steering/
https://kiro.dev/docs/specs/best-practices/
https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/research-plan-iterate

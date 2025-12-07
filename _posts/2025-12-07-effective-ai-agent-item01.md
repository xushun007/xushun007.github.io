---
title: 《Effective AI Agent》条目1：优先在确定性任务中使用显式工作流
author: xushun
date: 2025-12-07
categories: [Agent]
tags: [Agent, Effective AI Agent]
render_with_liquid: false
---

# 第一章：智能体架构基础——核心原则与设计

在 AI 带来的狂热中，我们容易陷入一种“拿着锤子找钉子”的误区，试图用 Agent 解决所有软件工程问题。本章的核心在于界定边界：**识别何时该用传统的代码逻辑，何时该引入不确定的 LLM 推理，以及如何通过架构设计约束这种不确定性。**

## 条目 1：优先在确定性任务中使用显式工作流

### 背景动机

随着 LLM 能力的提升，开发者有一种倾向：将整个业务逻辑扔给一个庞大的 Prompt，期待模型能像人类员工一样自主规划并完成任务。这种“全托管”模式虽然 Demo 演示效果惊艳，但在生产环境中往往是噩梦的开始。它的调试难度极高，延迟不可控，且随着上下文（Context）的增长，模型的遵循指令能力（Instruction Following）会显著下降。


### 原理分析

**智能体（Agent）与工作流（Workflow/Chain）的本质区别在于控制权的归属。**

  * **工作流**：控制权在代码（即开发者）。执行路径是预定义的 DAG（有向无环图），LLM 仅作为节点处理特定任务（如摘要、抽取）。
  * **智能体**：控制权在模型（即 LLM）。模型决定下一步调用什么工具、是否结束循环。

Anthropic 在《Building Effective Agents》中明确区分了「预定义的可组合工作流」与「开放式 Agent」，并建议在能用前者解决问题时，不要轻易启用后者。LangChain 在《How to think about agent frameworks》中也指出，真正难的部分在于保持每一步 LLM 调用的上下文正确，而不是放任模型在不透明的状态空间中自由游走。

从工程角度看，这可以浓缩成一句话：**如果一个流程可以用 `if-else` 或一个有限状态机精确地描述，就不应该交给 Agent 来「发挥」。**

显式工作流天然具备几个优势：逻辑路径可穷举、行为可测试、性能可预估、问题可复现。而 Agent 带来的灵活性，是用不确定性换出来的——只有当任务路径无法预先枚举，需要模型基于运行时环境做动态决策时，这笔交换才是划算的。

### 工程实践

在构建系统时，应采用“工作流优先（Workflow First）”的策略。

1.  **Code is Policy**：将所有硬性业务规则（如审批流程、权限校验、固定数据格式化）写成 Python/Java 代码，而不是 Prompt。
2.  **LLM as a Function**：将 LLM 视为工作流中的一个无状态函数转换器（Transformer），而非决策者。
3.  **逐步升级**：从线性 Chain 开始，只有在遇到单一路径无法覆盖的边缘情况（Corner Case）时，才引入路由（Router）或循环（Loop）机制。



### 参考文献
* Anthropic, *Building Effective Agents* — `https://www.anthropic.com/research/building-effective-agents` 
* LangChain Blog, *How to think about agent frameworks* — `https://blog.langchain.com/how-to-think-about-agent-frameworks/`
* Louis-François Bouchard, *Agents or Workflows?* — `https://www.louisbouchard.ai/agents-vs-workflows/` 
* OpenAI, *How to think about agent frameworks* - `https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf`

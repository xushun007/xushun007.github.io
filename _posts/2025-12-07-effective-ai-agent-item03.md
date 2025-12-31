---
title: 《Effective AI Agent》条目 3：以“问题空间”定义智能体边界，而非“模型能力”
author: xushun
date: 2025-12-31
categories: [Agent]
tags: [Agent, Effective AI Agent]
render_with_liquid: false
---

## 条目 3：以“问题空间”定义智能体边界，而非“模型能力”

### 背景动机

LLM 的通用性是其最大的优势，但对于 Agent 系统架构设计而言，这往往是最大的陷阱。

开发者容易陷入“模型能力中心论”：既然 GPT-5 既懂 Python 又懂法律，为什么不把它们写在一个 Agent 里？于是诞生了**“全能创业合伙人（Co-founder Agent）”**这种典型的**上帝智能体（God Agent）**——试图在一个 Agent 中同时处理代码开发、商业计划书撰写和法律风险审查。

这种架构在 Demo 阶段令人惊艳，但在工程落地时是一场噩梦：

1. **优化互斥（Optimization Conflict）**：为了提升代码生成的准确率而调整 Prompt，可能会意外导致法律审查的语气变得不再严谨。
2. **评估失效（Evaluation Failure）**：你无法为一个“全能者”设定单一的评估指标（Metric）。代码写得好但商业逻辑差，这个 Agent 到底是 90 分还是 40 分？

**智能体的边界不应由底座模型能做什么（What LLM can do）决定，而应由我们要解决的特定领域问题（What Problem to solve）决定。**

### 原理分析

设计 Agent 边界时，我们应参照传统软件架构中的**限界上下文（Bounded Context）**，给 Agent 设定范围、边界和框定具体职责。但需注意两者在 AI 时代的本质差异。

#### 1. 与传统架构的**共同点**：隔离复杂性

在微服务或 DDD 中，我们将“商品”概念在库存域和销售域分开，是为了避免逻辑耦合。同理，在 Agent 中，我们需要**上下文隔离（Context Isolation）**。

* **输入隔离**：一个负责 SQL 生成的 Agent，不需要知道用户的“情感状态”或“上一轮的闲聊内容”。
* **工具隔离**：一个负责文案生成的 Agent，绝对不应持有 `drop_table` 或 `search_logs` 的工具权限。

#### 2. 与传统架构的**差异点**：对抗“过度泛化”

这是 Agent 架构特有的挑战。

* **传统软件**：边界是刚性的。如果你在 `OrderService` 中调用 `draw_ui()`，编译器会直接报错。
* **Agent 系统**：边界是模糊的。如果你问一个“数据库运维 Agent”如何做番茄炒蛋，它会利用其泛化能力热心地回答你。

这种“过度泛化”在工程上是**Bug**而非Feature。它意味着 Agent 容易被 Prompt Injection 攻击，或者在处理模糊指令时“自作聪明”地跳出业务范围。因此，架构师必须通过 System Prompt 和工具白名单，人为地**构建一道“类编译器”的刚性围墙**，强制 Agent “不知道”边界以外的知识。

Andrew Ng 在 *Agentic Reasoning* 演讲中强调：**与其追求一个 Zero-shot 的天才，不如构建一组通过协作解决问题的专才（Narrow Agents）。**

### 业界标杆案例

* **Claude Code (Anthropic)**: Claude Code 是目前工程化落地的典范。尽管 Claude Sonnet 模型本身可以写诗、画图、分析财报，但 **Claude Code 这个 Agent** 被严格限制在“终端开发”的问题空间内。它只关注文件读写、 Bash 命令执行和代码变更。它摒弃了所有与“软件开发循环”无关的通用能力，这使得它在编码任务上的表现远超通用的 Claude 网页版。
* **OpenAI Deep Research**: Deep Research 并没有试图成为一个“文章生成器”。它的核心职责被严格锁定在**“信息挖掘与验证”**。它会自动执行多轮搜索，阅读网页，但它的输出通常是详实的报告材料，而非最终的营销软文。这种将“素材搜集（Research）”与“内容创作（Copywriting）”剥离的设计，避免了事实性错误与文风修饰之间的冲突。

### 工程实践

在定义 Agent 时，应遵循**“一个 Agent，一个核心目标”**的原则。

1. **依据“领域冲突”进行物理拆分**：
如果一个 Agent 的职责横跨了两个性质截然不同的领域（例如“创意写作”与“代码生成”），必须进行物理拆分。请确保每个 Agent 仅对其所在的特定问题空间拥有“全知视角”。

2. **对抗性 System Prompt**：
在 Prompt 中明确定义**“负向约束”**，人为切断模型的泛化能力。
* 例如：“你是一个 Python 代码审查员。如果用户询问代码之外的问题（如人生建议、数学题），请直接回复 `SCOPE_ERROR`。”

3. **工具集的“无知”设计**：
不要为了方便给 Agent 挂载通用工具箱。**写作 Agent 不应该有搜索工具**。如果在写作阶段发现信息不足，这不应由写作 Agent 自己去搜索（这会引入不可控的循环），而应由上层编排层退回给“搜索 Agent”重新执行。

### 示例代码

以下代码展示了如何通过严格的工具裁剪和防御性提示词来构建一个“高内聚”的专家 Agent，而非通用 Agent。

```python
from dataclasses import dataclass, field
from typing import List, Dict

# === 0. 定义核心提示词 (The Soul) ===
# 这里的提示词不仅仅是指令，更是两个限界上下文的“宪法”。

RESEARCHER_PROMPT = """
你是一名严谨的信息搜集员。
你的目标是针对用户问题，收集尽可能多的事实数据和原始材料。
【约束】
1. 只输出客观事实和数据引用。
2. 不要尝试总结、润色或发表观点。
3. 如果信息不足，继续调用搜索工具，直到收集完毕。
"""

WRITER_PROMPT = """
你是一名技术专栏作家。
请基于提供的【上下文材料】，撰写一篇深度分析文章。
【约束】
1. 严格基于材料写作，禁止编造事实。
2. 如果材料中没有相关信息，请明确指出“资料缺失”，而不是试图自己去“猜”或利用训练数据回答。
3. 你的世界是封闭的，你无法访问互联网。
"""

# === 1. 定义限界上下文契约 (The Contract) ===
@dataclass
class ResearchContext:
    topic: str
    raw_materials: List[str] = field(default_factory=list)

# === 2. 搜集专家 (Researcher) ===
# 边界定义：负责“发散”，拥有外部连接能力
class ResearchAgent:
    def __init__(self):
        self.role = "Information Hunter"
        self.system_prompt = RESEARCHER_PROMPT
        # 【物理边界】仅授予搜索/浏览工具，隔离了“编造”的冲动
        self.tools = [google_search, browse_webpage]

    def run(self, topic: str) -> ResearchContext:
        print(f"[{self.role}] 正在执行搜集任务: {topic}...")
        # 模拟：Loop 执行搜索直到信息充足
        # materials = agent_executor(self.system_prompt, self.tools, topic)
        return ResearchContext(
            topic=topic,
            raw_materials=["数据源A: Q3增长率15%", "数据源B: 市场规模200亿"]
        )

# === 3. 写作专家 (Writer) ===
# 边界定义：负责“收敛”，被物理切断互联网
class WriterAgent:
    def __init__(self):
        self.role = "Content Synthesizer"
        self.system_prompt = WRITER_PROMPT
        # 【物理边界】工具列表为空！
        # 即使模型产生幻觉想去搜索，代码层面也无路可走。
        # 这就是“Code-level Guardrails”
        self.tools = []

    def run(self, context: ResearchContext) -> str:
        print(f"[{self.role}] 基于 {len(context.raw_materials)} 条素材进行闭卷写作...")
        # 模拟：纯推理过程
        # article = llm.predict(self.system_prompt, context.raw_materials)
        return "深度分析报告：基于Q3增长率..."

# === 4. 编排层 (Orchestration) ===
# 将两个“窄任务”串联成一个“宽能力”
def deep_research_flow(topic: str):
    # Phase 1: 扩充信息熵 (Research)
    researcher = ResearchAgent()
    context = researcher.run(topic)

    # Phase 2: 压缩信息熵 (Write)
    # 显式交接：将上游产出作为下游的唯一输入
    writer = WriterAgent()
    article = writer.run(context)

    return article

```

### 参考文献

* **Eric Evans**, *Domain-Driven Design: Tackling Complexity in the Heart of Software* — `https://book.douban.com/subject/26819666/`
* **Andrew Ng**, *Agentic Reasoning and the Future of AI Development*  — `https://www.youtube.com/watch?v=sal78ACtGTc`
* **Anthropic**, *Model Context Protocol (MCP) Specification* — `https://modelcontextprotocol.io`
* **LangChain**, *Deep Agents: The architecture of agentic systems* — `https://blog.langchain.com/deep-agents/`
* **Anthropic**, *Claude 3.5 Sonnet System Card (Coding & Agentic Capabilities)* — `https://www.anthropic.com/research/claude-3-5-sonnet-research`
* **OpenAI**, *Introducing deep research* — `https://openai.com/index/introducing-deep-research/`
* **Yao et al.**, *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023) — `https://arxiv.org/abs/2210.03629`
* **Chase (LangChain)**, *Agents: It's all about the boundaries* — `https://blog.langchain.com/how-to-think-about-agent-frameworks/`
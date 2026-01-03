---
title: 《Effective AI Agent》条目 4：把 Agent 模块化为Planner/Executor/Memory，否则迟早写成意大利面条
author: xushun
date: 2026-01-03
categories: [Agent]
tags: [Agent, Effective AI Agent, Plan, Memory]
render_with_liquid: false
---

## 条目 4：把 Agent 模块化为Planner/Executor/Memory，否则迟早写成意大利面条

### 背景动机

很多团队做 Agent，最先崩掉的不是模型能力，而是架构形态：一个“万能循环”里既要规划步骤、又要挑工具、还要记住上下文，最后 Prompt、工具调用、状态更新全缠在一起，形成典型的意大利面条系统。你想换一种规划策略、想把执行放进沙箱、想加长期记忆，都会变成“牵一发动全身”的大手术。

更糟的是，这种耦合会直接毁掉可观测性与可治理性：出了问题你没法明确归因——到底是规划错了、工具不稳定、还是记忆污染？而在真实互联网工程里，**不可归因就不可迭代**：你每次只能“再调一版 prompt”，调到最后谁也说不清到底改对了什么。Anthropic 在复盘大量落地经验时，把成功做法归结为一句很朴素的话：最有效的系统往往不是更复杂的框架，而是更简单、可组合的模式。

---

### 原理分析

把 Agent 当作软件架构来设计，最小可用的主干就是三件套：**Planner 负责“想清楚怎么做”，Executor 负责“把事做掉”，Memory 负责“该记的记住”**。它们分开不是为了好看，而是为了满足软件工程里最硬的两条：**单一职责**与**可替换性**——你能独立替换 Planner（规划策略/模型/提示词）、独立替换 Executor（本地/CI/沙箱/只读）、独立替换 Memory（短期摘要/长期检索/可审计账本），而不会把系统拧成一坨。

Planner/Executor 的分离，本质上就是“把高层意图和低层动作拆开”。Plan-and-Execute 之所以更稳，是因为它承认规划与执行是两类工作负载：规划可以慢、可以谨慎，执行要便宜、要确定；失败时也更容易归因是“计划质量问题”还是“执行稳定性问题”。更关键的是，这让你能把计划当成 PRD/设计稿一样先审一遍：影响面、风险点、回滚路径先摆出来，再允许执行层动手。这不是纸上谈兵：Claude Code 直接把 Plan Mode 做成只读分析阶段，用“阶段边界”来降低误操作风险；Codex 也用 read-only/approval modes 把“先计划、后执行”变成权限闸门。

Executor 这边，最关键的一点是：它接收的最好不是“请帮我执行”的自然语言，而是一个稳定的 **Task/工单对象**。Task 就像架构里的“窄腰协议”：Planner 怎么拆 step 是上游自由，Executor 只认 Task（目标、工具、参数、验收标准、执行上下文）。你可以把 Task 理解成执行层的 DTO/IR：Planner 像“编译器”把意图编译成 IR，Executor 像“运行时”消费 IR——这样两边才能各自演进而不互相拖死。这其实很像 Ports & Adapters（Hexagonal）在说的那件事：业务核心不该被外部设备/接口绑死，边界要靠“端口契约”来稳定。

Memory 是第三个最容易“糊在一起”的模块。LangChain 对 memory 的提醒很直白：记忆不是模型的天赋，而是一套系统设计选择，并且要按产品体验与风险偏好来取舍。工程上你要的是“系统记忆”，不是“模型回忆”：可审计、可截断、可过期、可追踪污染来源。把 Memory 当“账本”，其实就是在做可追责的状态管理：出了事故你能回放链路，而不是猜模型当时在想啥。

最后补一句避免误解：这三件套是**最小主干**，不是全部。生产落地还需要编排与治理（超时/重试/并发/权限/审计/追踪），但**主干先拆清楚**，后面加什么都不会返工。

---

### 工程实践

真正落地模块化，抓住一个顺序就够了：**先定 Task 契约，再围绕 Task 演进 Planner / Executor / Memory**。

第一，把 Planner 的产出从“给 Executor 的指令文本”，升级为“可审的计划工件 + 可编译的 Tasklist”。Augment 的 Tasklist 实践很值得抄：它把多步工作从聊天气泡里搬出来，做成结构化、可编辑、可跟踪的任务对象，用状态流转（TODO/DOING/DONE）去建立信任，而不是赌模型每次都自觉不跑偏。这一步做对了，你的系统天然就更像互联网工程：可 review、可回放、可度量进度。

第二，让 Executor 像“运行时”而不是“回复器”。它要做的不是聪明，而是确定：工具白名单、权限校验、超时/重试、幂等、证据链落盘。SWE-agent 的结论非常工程：**接口/执行环境（ACI）会显著影响 agent 的行为和成功率**，也就是说，你把执行接口设计得越像 IDE/终端的真实工作台，agent 越像工程师；你把它设计成“随便调用几个函数”，agent 就更像玩具。

第三，Memory 要“收口”：只允许通过 Memory 接口写入，把写入策略做成配置（哪些能记、记多久、是否需要来源验证）。把 Memory 当“账本”，你才能在故障复盘时回答两个问题：**它为什么这么想？它从哪里记来的？**

---

### 示例代码

下面这段伪代码体现一个“可运营”的最小闭环：Executor 只消费 Task；Memory 作为账本收口；Orchestrator 负责循环、治理与触发 re-plan。

```python
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Protocol
import uuid
import time
import logging

# 配置日志：模拟生产环境的可观测性
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger("System")

# ==========================================
# 1. Core Contracts (核心契约)
# 定义组件间通信的接口，确保模块解耦
# ==========================================

@dataclass(frozen=True)
class Task:
    """
    Executor 只关注“做什么”，不关注“为什么”。
    这是一个不可变的工单。
    """
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str  # 留存给人类审计或 Memory 使用，Executor 不执行此字段

@dataclass(frozen=True)
class TaskResult:
    """
    执行结果的标准封装。
    包含结构化数据(output)和非结构化证据(evidence/logs)。
    """
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # 如耗时、消耗token数

class Memory(Protocol):
    """Memory 是系统的'账本'，负责维护上下文窗口和历史记录"""
    def add_result(self, result: TaskResult) -> None: ...
    def get_history(self) -> List[Dict]: ...

class Planner(Protocol):
    """
    Planner 是'大脑'。
    输入：目标 + 历史记忆
    输出：下一步的任务列表 (如果没有任务，说明目标达成)
    """
    def plan(self, goal: str, memory: Memory) -> List[Task]: ...

class Executor(Protocol):
    """
    Executor 是'肌肉'。
    输入：工单 (Task)
    输出：结果 (Result)
    特性：无状态、原子性
    """
    def execute(self, task: Task) -> TaskResult: ...

# ==========================================
# 2. Orchestrator (编排与治理)
# 这一层负责 Loop、错误处理和熔断，是系统稳定性的关键
# ==========================================

class AgentLoop:
    def __init__(self, planner: Planner, executor: Executor, memory: Memory, max_steps: int = 10):
        self.planner = planner
        self.executor = executor
        self.memory = memory
        self.max_steps = max_steps

    def run(self, goal: str):
        trace_id = uuid.uuid4().hex[:10]
        logger.info(f"trace={trace_id} Start Agent Goal: {goal}")

        for step in range(self.max_steps):
            # --- Phase 1: Planning (观测与规划) ---
            # Planner 根据最新的 Memory 决定下一步，这里体现了架构的“动态性”
            tasks = self.planner.plan(goal, self.memory)

            if not tasks:
                logger.info(f"trace={trace_id} Goal Achieved (Planner returned no tasks).")
                return

            logger.info(f"trace={trace_id} Step {step+1}: Planner generated {len(tasks)} tasks.")

            # --- Phase 2: Execution (执行与治理) ---
            for task in tasks:
                logger.info(f"trace={trace_id}   -> Executing: {task.tool_name} (ID: {task.id})")

                start = time.time()
                result = self.executor.execute(task)
                cost_ms = int((time.time() - start) * 1000)

                # 写入记忆 (Memory 收口)
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["elapsed_ms"] = cost_ms
                self.memory.add_result(result)

                # --- Governance Logic (治理策略) ---
                # 策略：Fail-Fast。如果某个任务失败，这批次剩余任务可能已无效（依赖链断裂）。
                # 动作：立即停止本轮循环，将错误结果暴露给 Planner，让它在下一轮 decide how to fix。
                if not result.success:
                    logger.warning(f"trace={trace_id} Task Failed: {result.error}. Triggering Re-plan.")
                    break  # Break inner loop, go back to Phase 1
                else:
                    logger.info(f"trace={trace_id} Success.")

        logger.error(f"trace={trace_id} Max steps reached without completion.")

# ==========================================
# 3. Mock Implementations (模拟实现)
# 仅用于演示各模块职责
# ==========================================

class InMemoryMemory:
    def __init__(self):
        self._history = []

    def add_result(self, result: TaskResult):
        # 真实场景：这里会处理 Token 截断、向量化存储等
        self._history.append(asdict(result))

    def get_history(self) -> List[Dict]:
        return self._history

class MockToolExecutor:
    def execute(self, task: Task) -> TaskResult:
        # 模拟：如果参数明确要求触发错误，则模拟失败
        if task.arguments.get("query") == "trigger_fail":
            return TaskResult(task.id, False, None, error="ConnectionTimeout: 500 Server Error")

        return TaskResult(task.id, True, output=f"Executed {task.tool_name} with {task.arguments}")

class MockLLMPlanner:
    """
    模拟一个具备 Re-planning 能力的大模型。
    它会检查 Memory，如果发现上一步失败了，会生成修复计划。
    """
    def plan(self, goal: str, memory: Memory) -> List[Task]:
        history = memory.get_history()

        # 场景 1: 没有任何历史 -> 第一步计划
        if not history:
            return [
                Task(id="t1", tool_name="search_docs", arguments={"query": "how to fix bug"}, reasoning="Locate info"),
                # 这里故意制造一个会失败的任务来演示 Re-plan
                Task(id="t2", tool_name="api_call", arguments={"query": "trigger_fail"}, reasoning="Attempt fix"),
            ]

        # 场景 2: 检查历史，发现上一步失败了 -> 生成修复计划 (Re-plan)
        last_result = history[-1]
        if not last_result["success"]:
            logger.info("    (Planner sees failure in memory -> Switching strategy)")
            return [
                Task(id="t3", tool_name="check_status", arguments={"service": "api"}, reasoning="Diagnose failure"),
                Task(id="t4", tool_name="retry_api", arguments={"strategy": "backoff"}, reasoning="Retry with caution")
            ]

        # 场景 3: 成功 -> 结束
        return []

# ==========================================
# 4. Entry Point
# ==========================================

if __name__ == "__main__":
    # 组装组件：体现了依赖注入和模块化
    # 任何一个组件都可以被真实的 LLM 或 RPC 服务替换，互不影响
    agent = AgentLoop(
        planner=MockLLMPlanner(),
        executor=MockToolExecutor(),
        memory=InMemoryMemory()
    )

    agent.run("Fix the production incident")
````

---

### 参考文献

* **Anthropic**, *Building effective agents* — `https://www.anthropic.com/research/building-effective-agents`
* **LangChain**, *Plan-and-Execute Agents* — `https://blog.langchain.com/planning-agents/`
* **LangChain**, *Memory for agents* — `https://blog.langchain.com/memory-for-agents/`
* **Anthropic**, *Common workflows (Plan Mode) — Claude Code Docs* — `https://code.claude.com/docs/en/common-workflows`
* **OpenAI**, *Codex Security (approval modes / read-only)* — `https://developers.openai.com/codex/security/`
* **OpenAI**, *Codex Execution Plans (ExecPlans): Using PLANS.md for multi-hour problem solving* — `https://cookbook.openai.com/articles/codex_exec_plans`
* **John Yang et al.**, *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering* — `https://arxiv.org/abs/2405.15793`
* **Augment**, *How Augment uses Tasklist* — `https://www.augmentcode.com/blog/how-augment-uses-tasklist`
* **Alistair Cockburn**, *Hexagonal Architecture* — `https://alistair.cockburn.us/hexagonal-architecture/`
* **Robert C. Martin**, *The Clean Architecture* — `https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html`
* **The Pragmatic Engineer**, *How Claude Code is built* — `https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built`
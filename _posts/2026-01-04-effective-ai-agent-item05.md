---
title: 《Effective AI Agent》条目 5：实现可回放的 Orchestrator 以支撑调试与回归
author: xushun
date: 2026-01-04
categories: [Agent]
tags: [Agent, Effective AI Agent, Orchestrator]
render_with_liquid: false
---

# 条目 5：实现可回放的 Orchestrator 以支撑调试与回归

## 背景动机

Agent 系统最折磨工程师的地方，不是它会不会“答”，而是它**怎么走到这个答案**。线上事故往往不是最终回复“看起来不对”，而是某一步工具调用抖了一下、某次检索命中了脏数据、某个路由策略突然选错了分支，最后你只看见一个结果，却找不到责任步骤。

这跟当下互联网的软件架构实践是反着来的：我们做微服务默认有 trace、有日志、有回放；出了故障能复盘，修了之后能回归验证。Agent 其实就是一种“会自我分支、会重试、会跨多工具”的工作流系统——只不过它把控制流的一部分交给了模型。Anthropic 在 2024 的工程文章里把 agentic system 明确区分为 workflow 与 agent，并强调成功落地依赖“简单、可组合的模式”，而不是把复杂性藏进黑盒。

所以这条原则很硬：**每一次任务必须可记录、可复现、可重放**。否则你无法稳定迭代，只能靠“玄学调参”。

## 原理分析

“可回放”不是一个日志开关，它是一套运行时语义：你要把一次执行变成可重建的“事件历史”。Temporal 这类工作流引擎用 Event History 记录每次执行的命令与事件，并依赖确定性约束实现一致 replay——这套机制之所以能让工程团队长期维护复杂流程，本质就在于“把执行过程变成可回放的数据”。

Agent 的麻烦在于：LLM 不确定、外部世界也不确定。因此可回放要分层：

第一层是**播放式回放**：不重新请求模型、不重打外部工具，直接按历史事件“播放”输入输出，用来复现现场、定位责任步骤（这是 Debug 的刚需）。

第二层是**半确定回放**：外部工具返回用历史快照冻结，只重跑模型或部分策略，用来做 Prompt/模型升级的回归对比（你要的是“策略变没变坏”，不是“外部世界变没变”）。

第三层才是**全量重跑**：连工具也重跑，更像演练/压测，前提是工具幂等、可关联、可对账，否则只会制造更多噪音。

这套分层之所以可落地，是因为它借了两条成熟的架构思想：一条是 Fowler 总结的 Event Sourcing（用事件重建状态、天然支持审计与回放），另一条是分布式可观测性（用 trace context 把跨组件的步骤串起来）。

## 工程实践

要实现可回放的 Orchestrator，别把它当“串工具的脚本”，要把它当一个小型工作流内核：它负责定义**运行契约、事件模型、存储与回放器**，并把这些能力接进你现有的观测与回归体系。

首先把“运行契约”钉死。每次 run 至少要固化：模型与版本、采样参数、system prompt 版本、工具 schema 版本、检索配置版本。OpenAI 在 2025 的 agents 工具发布里把“可观测（trace & inspect）”作为 agent 工程化能力的一部分提出来，本质就是在提醒你：没有这些版本维度，你连问题都描述不清，更别说回归对比。

然后把每一步变成不可变事件，并进入追加写存储。不要只存“最终答案”，要存：路由决策、工具入参/出参、模型原始输出、解析结果、重试原因、耗时、token 用量。LangChain 在谈 deep agents 调试时反复强调“你需要可视化每一步做了什么”，否则长链路里任何一次偏航都像大海捞针。

接着，工具必须“可回放”。工程上最常见的坑是：你以为模型不稳定，其实是工具不稳定；你以为回归变差，其实是外部数据漂移。最低要求是给每次工具调用一个可派生的 `call_id`（例如 `run_id:step_id`），并把它透传到下游系统，做到幂等与可对账。这里强烈建议直接对齐 OpenTelemetry 的语义：把一次 run 视为 trace，把每一步视为 span，把 `run_id` / `call_id` 作为 attributes。LangSmith 的 OpenTelemetry 支持与文档，本质上就是把“agent 轨迹”纳入成熟的分布式追踪范式。

最后，把回放变成回归。你要把历史 run 变成“回归集”，对每次 Prompt/模型/策略升级跑一遍半确定回放，比较三类指标：路径长度（步数、工具调用数、重试次数）、成本（token 与外部调用费用）、质量（结构化输出通过率、引用覆盖率、关键断言正确率）。Chip Huyen 在 agents 的工程写法里强调 failure modes 与 evaluation 的重要性——而可回放轨迹就是你做这些评估的“样本基建”。

## 示例代码（可选）

下面这段代码给的是“可回放最小骨架”：

* **RunContract** 固化版本维度
* 每一步写入 **append-only 事件日志**
* 提供 **playback**（复现现场）与 **hybrid_replay**（冻结工具结果做回归）
* 预留 `trace_id` 字段，方便你对接 OTel/W3C Trace Context（跨服务串起来）([W3C][8])

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Callable, Optional
import json, time, uuid

JSON = Dict[str, Any]


@dataclass(frozen=True)
class RunContract:
    # “这次到底跑的是什么”——必须可追溯
    model: str
    model_version: str
    temperature: float
    system_prompt_version: str
    tool_schema_version: str
    retriever_version: str


@dataclass(frozen=True)
class StepEvent:
    run_id: str
    step_id: int
    kind: str          # router/tool/llm/parse/error...
    name: str          # tool_name/model_name/router_name...
    ts_ms: int
    trace_id: str      # 便于接入 OpenTelemetry/W3C Trace Context
    input: JSON
    output: JSON
    meta: JSON         # latency, tokens, retry, etc.


class AppendOnlyLog:
    def __init__(self, path: str):
        self.path = path

    def append(self, e: StepEvent) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    def read(self, run_id: str) -> List[StepEvent]:
        out: List[StepEvent] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj["run_id"] == run_id:
                    out.append(StepEvent(**obj))
        return sorted(out, key=lambda x: x.step_id)


class ReplayableOrchestrator:
    def __init__(self, log: AppendOnlyLog, tools: Dict[str, Callable[[JSON], JSON]]):
        self.log = log
        self.tools = tools

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def execute(
        self,
        user_input: str,
        *,
        contract: RunContract,
        llm: Callable[[str], str],
    ) -> str:
        run_id = uuid.uuid4().hex
        trace_id = uuid.uuid4().hex  # 真实场景：从入口透传/生成，贯穿全链路
        step = 0

        def emit(kind: str, name: str, _in: JSON, _out: JSON, meta: JSON) -> None:
            nonlocal step
            self.log.append(StepEvent(
                run_id=run_id, step_id=step, kind=kind, name=name,
                ts_ms=self._now_ms(), trace_id=trace_id,
                input=_in, output=_out, meta=meta,
            ))
            step += 1

        emit("contract", "run_contract", {"user_input": user_input}, {"contract": asdict(contract)}, {})

        # 1) router（示例：可替换组件）
        route = "search" if "查" in user_input or "search" in user_input.lower() else "none"
        emit("router", "simple_router", {"text": user_input}, {"route": route}, {"router_version": "v1"})

        # 2) tool（要求可回放：call_id 可对账、可幂等）
        tool_snapshot: Optional[JSON] = None
        if route == "search":
            call_id = f"{run_id}:{step}"
            t0 = self._now_ms()
            tool_snapshot = self.tools["search"]({"q": user_input, "call_id": call_id})
            emit("tool", "search", {"q": user_input, "call_id": call_id}, {"result": tool_snapshot},
                 {"latency_ms": self._now_ms() - t0, "tool_schema": contract.tool_schema_version})

        # 3) llm（把“渲染后的 prompt”固化，避免模板演进导致无法回放）
        prompt = f"[sys:{contract.system_prompt_version}] Q={user_input}\nCTX={tool_snapshot}\nA="
        t0 = self._now_ms()
        raw = llm(prompt)
        emit("llm", contract.model, {"prompt": prompt}, {"raw": raw},
             {"latency_ms": self._now_ms() - t0, "model_version": contract.model_version, "temperature": contract.temperature})

        # 4) parse（结构化输出时，这一步的失败原因是排障关键）
        answer = raw.strip()
        emit("parse", "plain_parser", {"raw": raw}, {"answer": answer}, {"parser_version": "v1"})

        return answer  # 线上建议同时返回 run_id 供定位

    def playback(self, run_id: str) -> List[StepEvent]:
        # 播放式回放：完全复现场景，不发起任何外部调用
        return self.log.read(run_id)

    def hybrid_replay(self, run_id: str, *, new_llm: Callable[[str], str]) -> str:
        # 冻结工具结果，只重跑 LLM：用于回归对比
        events = self.log.read(run_id)
        llm_evt = next(e for e in events if e.kind == "llm")
        return new_llm(llm_evt.input["prompt"]).strip()
```

## 参考文献


1. Anthropic — Building effective agents - `https://www.anthropic.com/research/building-effective-agents`
2. OpenAI — New tools for building agents - `https://openai.com/index/new-tools-for-building-agents/`
3. LangChain — Debugging Deep Agents with LangSmith - `https://blog.langchain.com/debugging-deep-agents-with-langsmith/`
4. LangChain — Introducing OpenTelemetry support for LangSmith `https://blog.langchain.com/opentelemetry-langsmith/`
5. LangSmith Docs — Trace with OpenTelemetry - `https://docs.langchain.com/langsmith/trace-with-opentelemetry`
6. Chip Huyen — Agents - `https://huyenchip.com/2025/01/07/agents.html`
7. Temporal Docs — Temporal Workflow / Event History / deterministic replay - `https://docs.temporal.io/workflows`
8. W3C — Trace Context - https://www.w3.org/TR/trace-context/`
9. OpenTelemetry — Context propagation - `https://opentelemetry.io/docs/concepts/context-propagation/`
10. Martin Fowler — Event Sourcing - `https://martinfowler.com/eaaDev/EventSourcing.html`
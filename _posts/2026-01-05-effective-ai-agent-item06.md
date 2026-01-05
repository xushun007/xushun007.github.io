---
title: 《Effective AI Agent》条目 6：把 ReAct 循环实现为受控的有限状态机
author: xushun
date: 2026-01-05
categories: [Agent]
tags: [Agent, Effective AI Agent, ReAct]
render_with_liquid: false
---

## 背景动机

最危险的并不是模型会胡说，而是它会**一直胡说下去**。很多早期 Agent Demo 都把 ReAct 写成一个包着 LLM 的 `while True`：看起来像"自主智能”，本质是把控制权交给了不可预测的循环——难调试、难止损、还会把 Token 和算力吞成黑洞。

这不是模型"笨”，而是你把一个**控制系统**当成了"聊天功能”在写。互联网架构里，我们早就用**有限状态机（FSM）**驯服复杂流程：订单创建、支付、确认收货……状态机的价值从来不是优雅，而是**可控**：限制路径、预算护栏、异常降级、可观测、可回放。ReAct 同理：它只是在"思考—行动—观察”里，把行动换成了工具调用、副作用与权限。

---

## 原理分析

最常见的反面教材，是"裸奔 ReAct”：

```python
# Naive ReAct（反面教材）
history = [{"role": "user", "content": task}]
while True:
    resp = llm.predict(history)
    if "Final Answer" in resp:
        break
    action = parse_action(resp)
    obs = execute(action)
    history.append({"role": "tool", "content": obs})
```

这种实现会掉进三个混沌陷阱。第一是**无限重试**：遇到鉴权失败、网络超时这类"外部不可控错误”时，模型缺乏"我已经试过很多次”的元认知，很容易重复同一个动作直到资源耗尽。第二是**上下文漂移**：历史线性增长，关键约束被噪声淹没，Agent 逐渐忘掉目标，开始自作聪明。第三是**不可观测**：当它在第 45 步崩掉，你面对的是一坨文本流，没有"分支/状态/路径”，排障基本靠猜。

要把 ReAct 做成工程系统，你得换一个视角：**ReAct = 事件驱动的状态机 + 工具调用协议**。论文里的 *Thought → Action → Observation*，落到实现就是状态迁移：

* 模型提出工具调用 → **EXECUTE_TOOL**
* 工具返回结果/错误 → **OBSERVE**
* 将 observation 回灌 → **THINK**
* 模型给出 final → **DONE**

关键不在"循环”，而在"状态可枚举、迁移可审计”。

**Codex CLI** 的做法很典型：它围绕 `function_call / function_call_output` 这样的"可关联事件”推进回合，把"请求工具—执行—回填结果—继续推理”固化成协议驱动的闭环。

**Gemini CLI** 社区甚至有人把"当前处于何种循环阶段”做成 UI 一等公民（coherence/执行态等），这件事的信号很强：当你需要对用户解释"它现在在干嘛”，你就已经进入了状态机世界——否则你无法稳定表达系统行为。

**OpenCode** 则把"权限态/能力态”硬编码进产品：`plan` 与 `build` 两类 agent 可切换，默认能力不同、工具权限不同。这本质是在状态机里引入"模式状态”：同一套 ReAct，在不同状态下允许的 action 不一样，比只靠 prompt 约束更硬、更可控。

---

## 工程实践

把 ReAct 当 FSM，不是为了论文正确，而是为了把它做成"能上线、能运维、能审计”的系统。

第一，**状态要在代码里落地，而不是只存在于 prompt**。别写大循环里 if/else 猜模型意图；定义明确的状态枚举（如 `THINK/EXECUTE_TOOL/OBSERVE/DONE/ERROR/CANCELLED`），每次迁移都打点：`trace_id、step_id、tool、call_id、from->to、耗时`。你能复盘，系统才算可控。

第二，**预算护栏必须是状态机的一部分**。`max_steps/max_tool_calls/wall_time/token_budget` 不是成本优化，而是安全机制，再补一个实用的护栏：**卡死检测**（重复同一工具、同一参数、同一搜索词），一旦命中就强制降级或终止。

第三，**把工具调用当作外部副作用来治理**。你需要一个"审批态”或"策略态”（`PENDING_APPROVAL -> EXECUTE_TOOL`），并且把幂等做成默认。

第四，**异常也要结构化成 observation 回灌**。不要工具报错就 throw；把错误封装成可解析的 observation，让状态机走 `OBSERVE -> THINK`。同时用策略强制收敛。

第五，**把 ReAct loop 当作可观测系统，而不是黑盒对话**。真正要盯的不是"模型说了啥”，而是：每个状态耗时、工具成功率/重试率、循环是否发散、上下文增长曲线。

---

## 示例代码
```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Callable, Optional, List, Protocol
import json, time, uuid


class State(str, Enum):
    THINK = "THINK"
    EXECUTE_TOOL = "EXECUTE_TOOL"
    OBSERVE = "OBSERVE"
    DONE = "DONE"
    ERROR = "ERROR"


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    call_id: str


@dataclass
class ModelTurn:
    final_text: Optional[str] = None
    tool_call: Optional[ToolCall] = None


class ModelAdapter(Protocol):
    def next_turn(self, *, messages: List[Dict[str, Any]]) -> ModelTurn: ...


class TraceHook(Protocol):
    def on_transition(self, *, trace_id: str, step: int, frm: State, to: State, meta: Dict[str, Any]) -> None: ...
    def on_tool_result(self, *, trace_id: str, step: int, call_id: str, ok: bool, meta: Dict[str, Any]) -> None: ...


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._tools[name] = fn

    def run(self, call: ToolCall) -> Dict[str, Any]:
        fn = self._tools.get(call.name)
        if not fn:
            raise KeyError(f"unknown tool: {call.name}")
        return fn(call.arguments)


@dataclass
class Budgets:
    max_steps: int = 20
    max_tool_calls: int = 10
    wall_time_seconds: float = 60.0


class ReActFSM:
    def __init__(self, *, model: ModelAdapter, tools: ToolRegistry, hook: Optional[TraceHook] = None):
        self.model, self.tools, self.hook = model, tools, hook

    def run(self, *, user_input: str, budgets: Budgets) -> str:
        trace_id = str(uuid.uuid4())
        state: State = State.THINK
        step = 0
        tool_calls = 0
        started = time.time()

        messages: List[Dict[str, Any]] = [{"role": "user", "content": user_input}]
        last_tool_result: Optional[Dict[str, Any]] = None
        current_call: Optional[ToolCall] = None

        while True:
            if time.time() - started > budgets.wall_time_seconds:
                return f"[TIMEOUT] trace_id={trace_id}"
            if step >= budgets.max_steps:
                return f"[STEP_LIMIT] trace_id={trace_id}"

            if state == State.THINK:
                turn = self.model.next_turn(messages=messages)

                if turn.final_text is not None:
                    self._transition(trace_id, step, state, State.DONE, {"reason": "final"})
                    return turn.final_text

                if turn.tool_call is None:
                    self._transition(trace_id, step, state, State.ERROR, {"reason": "invalid_model_turn"})
                    return f"[MODEL_ERROR] trace_id={trace_id}"

                if tool_calls >= budgets.max_tool_calls:
                    return f"[TOOL_LIMIT] trace_id={trace_id}"

                current_call = turn.tool_call
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_call",
                        "name": current_call.name,
                        "arguments": current_call.arguments,
                        "call_id": current_call.call_id
                    }]
                })
                self._transition(trace_id, step, state, State.EXECUTE_TOOL,
                                 {"tool": current_call.name, "call_id": current_call.call_id})
                state = State.EXECUTE_TOOL

            elif state == State.EXECUTE_TOOL:
                assert current_call is not None
                tool_calls += 1

                ok = True
                try:
                    result = self.tools.run(current_call)
                    last_tool_result = {"ok": True, "result": result}
                except Exception as e:
                    ok = False
                    last_tool_result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

                if self.hook:
                    self.hook.on_tool_result(trace_id=trace_id, step=step, call_id=current_call.call_id,
                                             ok=ok, meta={"tool": current_call.name})

                self._transition(trace_id, step, state, State.OBSERVE,
                                 {"tool": current_call.name, "call_id": current_call.call_id, "ok": ok})
                state = State.OBSERVE

            elif state == State.OBSERVE:
                assert current_call is not None and last_tool_result is not None
                messages.append({
                    "role": "tool",
                    "content": [{
                        "type": "tool_result",
                        "call_id": current_call.call_id,
                        "payload": json.dumps(last_tool_result, ensure_ascii=False)
                    }]
                })
                self._transition(trace_id, step, state, State.THINK, {"reason": "observe->think"})
                state = State.THINK
                step += 1

            else:
                return f"[END] trace_id={trace_id}"

    def _transition(self, trace_id: str, step: int, frm: State, to: State, meta: Dict[str, Any]) -> None:
        if self.hook:
            self.hook.on_transition(trace_id=trace_id, step=step, frm=frm, to=to, meta=meta)
```

---

## 参考文献
* Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" — `https://arxiv.org/abs/2210.03629`
* Phil Schmid, "OpenAI Codex CLI, how does it work?" — `https://www.philschmid.de/openai-codex-cli`
* google-gemini/gemini-cli Issue #6058, "Coherence Monitor" — `https://github.com/google-gemini/gemini-cli/issues/6058`
* Medium (Google Cloud), "Advanced Gemini CLI: Part 2— Decoding the Context" — `https://medium.com/google-cloud/advanced-gemini-cli-part-2-decoding-the-context-edc9e815b548`
* OpenCode， "sst/opencode" — `https://github.com/sst/opencode`
* CEF Boud, "How Coding Agents Actually Work: Inside OpenCode" — `https://cefboud.com/posts/coding-agents-internals-opencode-deepdive/`
* LlamaIndex, "Managing State" — `https://developers.llamaindex.ai/python/llamaagents/workflows/managing_state/`

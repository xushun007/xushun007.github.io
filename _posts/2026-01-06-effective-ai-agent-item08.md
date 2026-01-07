---
title: 《Effective AI Agent》条目 8：为错误进行分类建模，实现差异化重试
author: xushun
date: 2026-01-07
categories: [Agent]
tags: [Agent, Effective AI Agent]
render_with_liquid: false
---

## 背景动机

在互联网架构里，“重试”从来不是一句 `retry(3)` 能解决的事。你敢对支付接口无脑重试，资损就会来；你敢对网络抖动无脑重试，体验就会烂。**重试的前提不是“失败了”，而是“失败属于哪一类”。**

把这个问题搬到 AI Agent 上，会更糟：Agent 不只是“发一次请求”，它会在 ReAct 循环里连续调用模型、读写文件、跑命令、改代码、跑测试——一次失败可能发生在任何层，还可能伴随副作用。你如果把所有失败都当成“临时波动”，Agent 会在错误方向上越跑越久，把 token、时间和信任一起烧掉。

现实里这些坑，Codex / Gemini CLI / OpenCode 都踩过：

* **Codex CLI** 曾被用户反馈：遇到 429 rate limit 直接退出，希望能自动 backoff 重试。
* **Gemini CLI** 的 issue 里出现过典型反例：明明是 *token 超限*（400 / INVALID_ARGUMENT，属于“不可重试”），却触发了 `retryWithBackoff`，导致无意义的连环重试。
* **OpenCode** 社区里则能看到统一封装的 `AI_RetryError: Failed after 4 attempts`，说明它至少有一个通用重试器，但“重试 4 次仍失败”本身并不告诉你该怎么修复（是配额？鉴权？模型方波动？）。

所以这条目要讲的不是“加重试”，而是：**先把错误分门别类，再决定重试的策略、预算和补救动作。**

---

## 原理分析

把 Agent 当作软件架构来看，你可以把失败粗暴拆成三层：**传输层 / 协议层 / 语义层**——对应到 Agent 工程，就是“能不能重试、怎么重试、重试前要不要先修复输入”。

1. **传输层**：网络抖动、超时、5xx、短期拥塞。
   这类失败本质是“同样的请求换个时间大概率会成功”。典型策略就是指数退避 + 抖动（jitter），并且尊重服务端的 `Retry-After`。OpenAI 的 rate limit 指南与示例明确建议用随机指数退避来处理 429。

2. **协议层**：429 配额、401/403 鉴权、被策略拒绝。它们含义完全不同：

* **429**：有些是“每分钟限流”，等一等就好；有些是“账号配额不足”，你等一天也没用。
* **401/403**：通常不是重试能解决，而是要换凭证 / 权限。
  这层的关键是：**把“可等待恢复”和“需要人工介入”的 429 分开**。

3. **语义层**：输入 token 超限、参数非法、工具命令不存在、测试必然失败。
   这类失败的特征是：**不改变输入，重试 100 次也一样**。Gemini CLI 的“token 超限却 backoff 重试”就是典型症状：把语义错误误判成了传输错误。
   对语义层，正确姿势不是 retry，而是 **repair**：裁剪上下文、换更小的 diff、拆分任务、降级到只读分析等。

把这三层想清楚，你就能得到一个工程上很实用的结论：

> **重试策略不是“次数”，而是“分类 → 动作（retry / repair / fail-fast）→ 预算”。**

预算非常关键：Agent 天生爱循环。你要像做 RPC 熔断一样，为每一类错误设上限、设冷却时间、设全局 token/time budget，否则它会在“我再试一次”里把系统拖死。

---

## 工程实践

下面给一套能直接落地的做法，按“架构接口”的方式组织，而不是堆规则清单。

**第一步：在编排层定义统一错误模型（Error Model），不要让异常散落在工具与 SDK 里。**
让 orchestrator 把底层异常统一映射成少数几类 `ErrorKind`。。

**第二步：为每类错误绑定差异化策略：retry / repair / fallback / fail-fast。**
这里最容易犯的错，是“所有错误都 backoff 重试”。Gemini CLI 那个 issue 已经展示了后果：token 超限也重试，只会把用户时间磨没。
更合理的策略是：
* **Transient（超时/5xx）**：指数退避重试；
* **Rate limit（429）**：优先读 `Retry-After`；短期限流等待，长期配额直接 fail-fast 并提示升级/换 key；
* **Token 超限 / 参数非法（400）**：不重试，先 repair（裁剪上下文、分片任务）；
* **工具副作用风险**：只有在 *idempotent* 或有事务边界时才允许重试；否则要让 Agent 输出“恢复建议”而不是自动再跑一次。

**第三步：把“重试”做成可观测、可审计、可回放的系统行为。**
你需要把这些变成 trace/log，记录每次失败记录元数据信息，关注每次回合的预算。

---

## 示例代码

下面这段 参考codex 错误定义机制。

```rust
// https://www.agent-io.com/posts/Agent-Analysis_Codex
// Codex 的错误类型分为三大类：可恢复的瞬时错误（自动重试）、需要用户决策的错误（发送审批请求）、不可恢复的致命错误（终止任务）。
// codex-rs/core/src/error.rs (主要错误类型)
pub enum CodexErr {
    // 可恢复的瞬时错误（run_turn 自动重试）
    Stream(String, Option<Duration>),  // 流断开，带可选的重试延迟
    
    // 任务级错误（Task 层处理）
    TurnAborted { dangling_artifacts: Vec<ProcessedResponseItem> },  // Turn 被用户中断
    Interrupted,                    // Ctrl-C 中断
    ContextWindowExceeded,          // Token 超出上下文窗口
    
    // 资源限制错误
    UsageLimitReached(UsageLimitReachedError),  // API 使用限额达到
    
    // 沙箱相关错误（工具层处理）
    Sandbox(SandboxErr),            // 沙箱拒绝、超时、被信号杀死
    
    // 系统级错误
    InternalAgentDied,              // Agent 循环异常退出
    Fatal(String),                  // 致命错误，无法恢复
    
    // 网络错误
    UnexpectedStatus(UnexpectedResponseError),
    ConnectionFailed(ConnectionFailedError),
    RetryLimit(RetryLimitReachedError),
    
    // 外部错误自动转换
    Io(io::Error),
    Json(serde_json::Error),
}

// Codex 在不同层次实施不同的错误处理策略，形成纵深防御。
// 1. Turn 层：自动重试瞬时错误

// codex-rs/core/src/codex.rs:1901-1964 (run_turn 内部)
loop {
    match try_run_turn(...).await {
        Ok(output) => return Ok(output),
        
        // 网络流断开：自动重试
        Err(e @ CodexErr::Stream(..)) => {
            if retries < max_retries {
                retries += 1;
                let delay = backoff(retries);  // 指数退避
                sess.notify_stream_error(&turn_context, format!("Re-connecting... {}/{}", retries, max_retries)).await;
                tokio::time::sleep(delay).await;
            } else {
                return Err(e);  // 超出重试次数
            }
        }
        
        // 不可重试错误：直接返回
        Err(e @ CodexErr::Interrupted) => return Err(e),
        Err(e @ CodexErr::TurnAborted { .. }) => return Err(e),
        Err(e @ CodexErr::ContextWindowExceeded) => return Err(e),
    }
}

// 2. Task 层：处理 Token 超限和任务中断
// 3. 工具层：沙箱失败降级

```

---

## 参考文献

* OpenAI — *Introducing Codex*
   `https://openai.com/index/introducing-codex/`
* OpenAI — *Custom instructions with AGENTS.md*
   `https://developers.openai.com/codex/guides/agents-md/`
* openai/codex — *Add automatic retry with backoff for rate limit errors*
   `https://github.com/openai/codex/issues/231`
* Google Cloud — *Gemini CLI*
   `https://docs.cloud.google.com/gemini/docs/codeassist/gemini-cli`
* google-gemini/gemini-cli — *Token limit exceeded triggers retryWithBackoff*
   `https://github.com/google-gemini/gemini-cli/issues/5807`
* sst/opencode — *AI_RetryError: Failed after 4 attempts. Last error: Too Many Requests*
   `https://github.com/sst/opencode/issues/2398`
* OpenAI Cookbook — *How to handle rate limits*
   `https://cookbook.openai.com/examples/how_to_handle_rate_limits`
* Anthropic — *Building effective agents*
   `https://www.anthropic.com/research/building-effective-agents`
* AWS — *Retry behavior - AWS SDKs and Tools*
   `https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html`

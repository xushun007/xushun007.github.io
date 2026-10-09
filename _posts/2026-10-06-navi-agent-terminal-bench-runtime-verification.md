---
title: 从“运行成功”到“任务完成”：一次 Coding Agent Runtime 的评测复盘
author: xushun
date: 2026-10-06
categories: [Agent]
tags: [Agent, Coding Agent, Evaluation, BFCL, Terminal-Bench]
render_with_liquid: false
---

最近我用个人构建的 Navi-agent 在 Modal 云端 sandbox 中运行 Terminal-Bench 2.1，并把结果与此前的 BFCL 工具调用评测放在一起复盘。一个评测观察工具调用是否正确，另一个观察 Agent 是否能完成真实环境中的代码任务。

这个过程有价值的结论，不仅仅是Navi-agent benchmark 的分数，而是我们重新认识评测一个经常被忽略的问题：

> Agent 返回了最终文本，不代表任务完成；测试命令返回 0，也不一定代表交付完成。

## 一个看似漂亮、实际不完整的结果

截至这次复盘，Navi-agent 已在 Modal 中实际运行了 20 个不同的 Terminal-Bench 2.1 任务（软件工程相关任务）：Harbor verifier 通过 13 个，任务正确率 65%；Navi runtime 成功返回 20/20。这个结果只是小规模、非官方的子集结果，不能与完整排行榜直接比较。Terminal-Bench 2.1 官方数据集包含 89 个任务，公开研究中的 frontier agent 在相近的 Terminal-Bench 版本上通常也低于 65%，说明这类任务本身具有较高难度；但 Navi 的 20 个样本仍不足以形成正式排名结论。

在这 20 个任务中，有 7 个 Harbor 失败样本被单独重跑，用来验证 runtime 修复：

| 指标 | 结果 |
| --- | ---: |
| Harbor verifier | 3/7（42.9%） |
| Navi runtime success | 7/7（100%） |

表面上看，runtime 达到了 100%。但这只说明 7 个 session 都正常返回了最终响应，并不说明 7 个任务都完成了。

例如：

- `compile-compcert` 最终通过了 Harbor，但 Agent 跑到 51 轮后触发了 iteration limit；
- `build-cython-ext` 的 runtime 记录为 verified convergence，但 Harbor 发现 8 个功能测试失败；
- `polyglot-c-py` 和 `qemu-startup` 的主要问题是 apt 锁、仓库 404 和依赖没有安装；
- `large-scale-text-editing` 只差一个 `:wq`，模型却在总结中宣称“Everything verified”。

这些结果说明，至少要区分两件事：

1. runtime 是否能安全结束；
2. 任务是否有足够证据证明已经完成。

## 第一个问题：Agent 为什么会一直运行

最初的 runtime 只有最大迭代次数。它能防止无限循环，却无法判断“什么时候应该结束”。于是会出现两类问题：

- Agent 明明已经完成了修改，却继续搜索、测试和探索；
- Agent 没有完成任务，却在达到上限后直接失败。

我们首先加入了 iteration-limit summary：达到上限时，runtime 再给 Agent 一个不带工具的总结机会。这解决了第二个问题的一部分——session 可以有一个可读的最终响应——但它没有让 Agent 更快收敛，也不能证明任务已经完成。

因此，`iteration_limit_summary` 只能表示：

```text
runtime 正常收尾，但没有完成验证
```

它不能被统计为 verified completion。

## 从 prompt 提醒到 runtime 收敛策略

仅仅在 system prompt 中告诉模型“测试通过后立即结束”，效果有限。模型可以遵守，也可能继续探索；更重要的是，runtime 不能把最终责任交给模型自己的描述。

后续加入的 convergence policy 做了更明确的事情：

1. 记录文件修改；
2. 识别测试命令及其结果；
3. 在修改后重新验证；
4. 满足条件后撤掉工具 schema，只允许 Agent 输出最终响应。

最后一步很重要。与其反复告诉模型“不要再调用工具”，不如在 runtime 层真正关闭工具调用能力。

但这里也出现了一个新的边界：

> “发现一个测试命令返回 0”不能自动等价于“任务完成”。

`build-cython-ext` 就是例子。Agent 执行了测试，部分基础检查通过，于是 runtime 认为已经收敛；但 Harbor 的功能检查发现 `pyknotid` 根本没有安装，多个扩展模块无法导入。这个结果不是 convergence loop 的问题，而是 acceptance evidence 质量不足。

## 证据不能只来自模型

一个 Coding Agent 通常会产生三种不同的信息：

### 模型声明

```text
The task is complete.
```

它反映的是模型的判断，应该保留在最终响应和 trace 中，但不能作为事实来源。

### 工具证据

例如：

- 命令退出码为 0；
- 测试输出包含 `11 passed`；
- 目标文件存在；
- 产物可以被 import 或执行；
- 服务端口能够连接。

这些证据比自然语言更可靠，但仍然要看它们是否真正对应任务验收条件。一个“仓库测试通过”可能没有覆盖“安装到全局 Python 环境”；一个“QEMU 端口可连接”也可能没有覆盖完整依赖初始化。

### 外部 verifier

独立的 Harbor verifier 不依赖 Agent 的总结，也不依赖 Navi 对测试含义的猜测。它应该拥有最高的任务正确性权重。

因此，我们没有继续增加大量状态，而是保留三个简单字段：

```text
runtime_status
completion_verified
completion_reason
```

示例：

```text
runtime_status=success
completion_verified=false
completion_reason=iteration_limit_summary
```

表示 runtime 正常返回，但没有证明任务完成。

```text
runtime_status=success
completion_verified=true
completion_reason=tests_passed_without_subsequent_mutation
```

表示 runtime 找到了有效的测试证据，并且之后没有新的文件修改。

这里的 `completion_verified` 不是模型自己设置的，而是由 runtime 根据工具证据或外部 verifier 设置。模型可以提出结论，不能单独宣布结论为事实。

## 第二个问题：旧证据会被新修改污染

假设 Agent 在第 10 轮运行测试并得到通过：

```text
iteration 10: tests passed
```

然后它在第 11 轮又修改了文件：

```text
iteration 11: write_file
```

第 10 轮的测试结果已经不能证明第 11 轮的代码仍然正确。如果 runtime 只看“历史上曾经通过”，就会错误收敛。

因此，验证证据必须绑定到最近一次 mutation。新的 patch 或 write 操作会使之前的测试证据失效，Agent 必须重新验证。

这是一个很小的机制，却比增加更多 prompt 更可靠：它把“证据是否仍然有效”从模型记忆中拿回了 runtime。

## 另外几个失败案例说明了什么

### `large-scale-text-editing`：模型声明与实际结果不一致

生成的 Vim 脚本里写的是 `wq`，测试要求的是 `:wq` 或 `:x`。模型最后说已经完成，但 verifier 只差一个明确的语法要求。

这个 case 不是 runtime 失控，而是模型没有认真读取失败信息并重新验证。runtime 应该保留测试失败事实，不应因为模型的总结而标记为 verified。

### `polyglot-c-py`：环境初始化没有完成

日志显示 apt 被另一个进程锁住，随后 `curl`、`uvx` 和环境脚本都不存在。Agent 可以继续写代码，但它不能把一个未初始化的环境描述成已验证完成。

这类错误不需要在 Navi 核心里加入大量 benchmark 特判。runtime 只需要保留工具返回的失败事实，并让 eval 层能够区分“任务实现失败”和“环境没有准备好”。

### `qemu-startup`：外部依赖漂移

Bullseye 安全仓库中的包版本已经返回 404。Agent 成功启动了 QEMU 和 relay，但后续验收依赖的 curl 没有安装，完整 verifier 因此失败。

这类问题很难靠模型推理解决。它要求评测环境固定依赖、更新镜像，或者让环境初始化步骤具备可重试能力。Agent runtime 不应该把外部依赖问题伪装成代码修复失败。

### `build-cython-ext`：局部测试通过不等于交付目标满足

这是最值得重视的案例。runtime 认为测试证据足够，但 Harbor 发现核心包没有安装。这说明 convergence policy 需要关注“测试是否与任务目标相关”，而不能只看退出码。

短期内不必建立复杂的 verifier agent。更简单的做法是让 TaskSpec 或 eval adapter 提供明确的 acceptance command，并把它与普通探索性测试区分开来。

## 这次改造真正解决了什么

这次 PR 没有把 Terminal-Bench 的任务正确率从 42.9% 直接提升到更高，也没有解决所有模型能力和环境依赖问题。它解决的是另一个同样关键的问题：

- iteration limit 不再必然导致 runtime 没有最终响应；
- 达到上限的安全总结不会冒充 verified completion；
- 新修改会使旧测试证据失效；
- eval 结果能区分 runtime success 和任务完成证明。

换句话说，系统从：

```text
success / failure
```

走向了：

```text
runtime 是否结束
任务是否被证据证明完成
```

这是评测系统从“能不能跑”走向“结果是否可信”的一步。

## 下一步

优先改进验收证据，而不是单纯增加迭代次数：

- 明确 acceptance command，并绑定最近一次代码修改；
- 保留环境错误原文，区分环境失败和实现失败；
- 将模型总结视为声明，用工具证据和外部 verifier 确认完成。

不需要引入复杂的 planner 或 verifier agent，最小闭环仍然是：

```text
修改 → 验证 → 判断证据是否仍有效 → 收敛 → 最终响应
```

成熟的 Agent 不只是返回结果，还要能区分：

```text
我已经返回结果。
我找到了部分验证证据。
任务已经被独立验收通过。
```

这三句话，应该在 runtime 和评测系统里拥有不同的含义。

## 工具调用与代码交付：先确认测量，再分析能力

Terminal-Bench 关注代码修改和环境验收，BFCL（Berkeley Function-Calling Leaderboard）关注工具选择与参数结构。两者共同回答一个问题：Agent 的动作是否满足任务约束？因此要先确认 scorer、schema 和验收条件准确，再分析模型能力。

最初的 BFCL 是一个很小的十条样本集，Navi 的工具调用正确率为 9/10，runtime success 为 10/10。修正 scorer、schema 并扩大到分层 100 条后，工具调用正确率为 91/100（91%）；进一步运行 500 条后，工具调用正确率为 441/500（88.2%），runtime success 仍为 100%。这些都是 Navi 的子集评测，不等同于官方完整 BFCL 排名。

早期唯一失败的样本表面上像是模型参数错误，实际是模型传入了 `x^2`，而 ground truth 要求的是可执行表达式 `x**2`。

这说明 runtime 发出调用不代表语义正确；scorer 不理解 schema 或等价表达式，也会把评测器错误归因给模型。

因此 BFCL 先修正评测闭环，再扩大覆盖：

- 让 scorer 读取第一轮真实 tool call，而不是只看后续对话状态；
- 统一 tuple schema 和工具名称，适配不同模型 API 的参数表示；
- 支持 unconstrained schema，避免评测器错误拒绝合法工具调用；
- 将样本从十条扩展到分层的 100 条，再扩展到更大的 500 条集合；
- 让 simple、multiple、parallel、irrelevance 等类别进入早期批次。

需要区分：

```text
修 scorer / 修 schema  → 让测量更准确
扩大样本 / 覆盖类别   → 让结论更可信
优化 runtime / prompt  → 让 Agent 真正变强
```

评测器不准确，分数就没有解释力；样本太少，分数就没有泛化性；只有 runtime 或模型改动才是在改善 Agent。

## 用同一个循环连接工具调用与代码交付

Terminal-Bench 和 BFCL 看起来完全不同：前者修改真实工作区，后者输出结构化 tool call。但它们最终都遵循同一个工程循环，而且每一轮都能给下一轮提供反馈：

```text
发现问题
    ↓
从 trace、工具输出和 verifier 中定位事实
    ↓
判断是模型、runtime、评测器还是环境
    ↓
做最小、可解释的改动
    ↓
用原失败样本和新增样本验证
    ↓
记录结果，继续下一轮
```

例如 BFCL 的 `x^2` 问题，第一反应可以是修改 prompt，要求模型使用 `**`。但进一步检查后发现，首先需要确认 scorer 的规范化和 ground truth 语义是否正确。于是先修评测器，再判断模型是否真的需要改进。这和 Terminal-Bench 中不能把“测试命令返回 0”直接等价为“任务完成”是同一个原则：先确认观测是否真的对应验收目标。

而 Terminal-Bench 的 `compile-compcert` 则相反：Harbor 已经通过，问题集中在 runtime 达到迭代上限后没有安全完成。这里应该修 completion fallback，而不是修改任务代码或误判模型失败。

`build-cython-ext` 又是第三种情况：runtime 认为证据足够，但 Harbor 失败。它说明 convergence policy 的证据质量不够，而不是简单提高迭代次数。

这套循环的价值在于，它强制每次改动回答四个问题：

- 我观察到的失败事实是什么？
- 失败属于模型、runtime、环境还是评测器？
- 这次改动改变了哪一个机制？
- 下一次验证能否证明改动真的有效？

如果一个 PR 只能让某个样本变绿，却不能解释为什么、在哪些类别有效，就不应该把它称为 Agent 能力提升。

## 把目标、验收和约束放回 runtime

在这些评测反馈之后，Navi 又加入了轻量的 `TaskSpec`：用 `objective` 描述目标，用 `acceptance` 描述验收条件，用 `constraints` 记录边界。交互式会话没有引入复杂的 goal 命令，而是让任务规格随 session 初始化、持久化并进入 runtime 上下文。

这一步把前面的两个问题连接起来：

- BFCL 的工具调用必须满足结构化契约；
- Terminal-Bench 的代码修改必须满足可验证的验收条件；
- runtime 只负责根据任务规格和证据决定是否可以收敛。

因此，`TaskSpec` 不是另一个规划系统，而是把“要完成什么、如何验收、不能违反什么”从临时 prompt 提炼成最小的共享事实。它让 task、verify、constraints 与 trace/eval 形成闭环，同时保持 Navi-agent 的核心概念数量可控。

## 评测结果应该成为工程反馈，而不是排行榜数字

BFCL 和 Terminal-Bench 放在一起后，可以看到评测系统和 runtime 其实是同一个反馈回路的两端：BFCL 检查 Agent 发出的动作是否符合结构化契约，Terminal-Bench 检查这些动作能否在真实环境中形成可验收的结果。评测系统本身是产品的一部分，runtime 的完成语义也是产品的一部分。一个有意义的报告至少应该同时给出：

```text
任务正确性
runtime 是否正常结束
是否有有效完成证据
失败发生在哪一层
修改后是否在原样本和新样本上复现
```

这样得到的不是“模型得了多少分”，而是一张可以指导下一轮工程工作的反馈地图。

## 参考

- [Navi-agent](https://github.com/xushun007/navi-agent)
- [Terminal-Bench](https://www.tbench.ai/)
- [Terminal-Bench 2.1 官方说明](https://github.com/harbor-framework/terminal-bench-docs/blob/main/content/blog/terminal-bench-2-1.mdx)
- [Terminal-Bench 论文与基准结果](https://arxiv.org/abs/2601.11868)
- [Inspect AI evaluation logs](https://inspect.aisi.org.uk/eval-logs.html)

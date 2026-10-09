---
title: Navi-agent Terminal-Bench 2.1 全量评测记录：89 个可验证终端任务
author: xushun
date: 2026-10-06
categories: [Agent]
tags: [Agent, Coding Agent, Evaluation, Terminal-Bench, Modal]
render_with_liquid: false
published: false
---

> 本文记录 Navi-agent 分批覆盖 Terminal-Bench 2.1 全部任务后的汇总评测结果。它不是官方排行榜提交，也不把 benchmark 分数等同于生产成功率；目标是保留可复查的任务结果、运行时行为、失败轨迹和工程取舍。

## 结论先行

本汇总覆盖 Terminal-Bench 2.1 的全部 89 个任务。任务分批在 Modal sandbox 中执行，模型为 `deepseek-flash`，并由 Harbor verifier 独立判定交付物是否正确；每个任务取其纳入汇总的最后一次结果。

| 指标 | 结果 | 含义 |
| --- | ---: | --- |
| Harbor verifier pass | **67 / 89（75.3%）** | 任务交付物满足独立 verifier |
| Harbor verifier fail | 22 / 89（24.7%） | 工作区或行为未满足验收要求 |
| Runtime completion | **86 / 89（96.6%）** | Navi 返回非空 final response |
| Runtime incomplete | 3 / 89（3.4%） | session 有运行记录，但未形成有效最终答复 |

```text
Harbor verifier    67/89  ███████████████░░░░░ 75.3%
Runtime completion 86/89  ███████████████████░ 96.6%
```

最重要的发现不是“75.3%”这个数字，而是两条指标之间的差距：**Agent 能正常结束，不等于任务真的完成。** 因此本文始终以 Harbor verifier 为正确性事实来源；runtime completion 只衡量会话是否能收尾。

## 评测设计

| 维度 | 设置 |
| --- | --- |
| Dataset | Terminal-Bench 2.1，89 tasks |
| Agent | Navi-agent completion-aware runtime |
| Model | `deepseek-flash` |
| Sandbox | Modal cloud sandbox |
| Runner | Inspect AI + inspect-harbor |
| Correctness | Harbor verifier |
| Execution | 分批运行，单批 `max_samples=4`；每批最多 4 个并发 sandbox |
| Iteration budget | 50；到达上限时允许无工具 summary fallback |

评测时，Navi 的工具调用直接进入每个任务独立的 sandbox；文件、网络、编译结果和测试输出均留在该 sandbox。Harbor verifier 在 Agent 停止后检查最终工作区，而不是相信模型的 final response。

## 为什么同时记录 completion 和 verification

一次 coding agent 运行至少有三层含义：

```text
model says “done”
        ↓
runtime has a final response
        ↓
external verifier accepts the delivered workspace
```

只有第三层是任务完成。本次 22 个 Harbor failure 中，10 个达到 iteration limit 后才生成 summary，3 个没有有效 final response；其余 9 个虽然正常结束，但交付物仍不满足 verifier。

| Harbor failure 的运行时形态 | 数量 | 解读 |
| --- | ---: | --- |
| `iteration_limit_summary` | 10 | 模型持续工具调用到预算上限；summary 不是完成证据 |
| 无有效 final response | 3 | runtime 状态或输出交接不完整 |
| 正常 final response，但 verifier fail | 9 | 自我判断或局部测试不足以代表验收通过 |

这也是 Navi 迭代 `TaskSpec`、acceptance、verified convergence、`completion_reason` 的原因：它们不负责替模型“判断正确”，而是把“模型声明”“运行时收尾”“外部证据”拆开记录。

## 官方分类：16 个 task.toml category，而不是主观归类

Terminal-Bench 2.1 的每个任务包都带有官方 `task.toml`，其中 `metadata.category` 与 `metadata.difficulty` 是随任务发布的元数据。本次按这份**评测版本实际携带的分类**聚合；它共有 16 个 category，且这一版本没有填写 `subcategory`。这比事后根据任务名称人为归类更可复查。

| Official category | Tasks | Pass | Pass rate |
| --- | ---: | ---: | ---: |
| data-processing | 4 | 4 | **100.0%** |
| data-querying | 1 | 1 | 100.0% |
| data-science | 8 | 7 | **87.5%** |
| debugging | 5 | 3 | 60.0% |
| file-operations | 5 | 2 | **40.0%** |
| games | 1 | 1 | 100.0% |
| machine-learning | 3 | 2 | 66.7% |
| mathematics | 4 | 4 | **100.0%** |
| model-training | 4 | 2 | 50.0% |
| optimization | 1 | 1 | 100.0% |
| personal-assistant | 1 | 1 | 100.0% |
| scientific-computing | 8 | 6 | 75.0% |
| security | 8 | 7 | **87.5%** |
| software-engineering | 26 | 19 | 73.1% |
| system-administration | 9 | 6 | 66.7% |
| video-processing | 1 | 1 | 100.0% |

分类样本很小时不能把 100% 解读为能力结论：只有 1 个任务的分类只说明这一次试验没有失败。更有解释力的是中等以上样本量的切面：`security` 7/8、`data-science` 7/8，`software-engineering` 19/26；`file-operations` 2/5 是当前最明显的薄弱组。难度维度同样呈现梯度：easy **4/4**、medium **43/55（78.2%）**、hard **20/30（66.7%）**。

官方仓库后续的 taxonomy 文档将任务组织为更高层的领域视图；本文不将两种口径混用，而以本次实际运行的 89 个 `task.toml` 为准。参考：[Terminal-Bench taxonomy](https://github.com/harbor-framework/terminal-bench/blob/main/docs/TAXONOMY.md)。

## 运行效率、Token 与成本：全量 89 条 trace

这里的统计范围是全部 89 条任务的 Navi trace。`duration` 是 Agent runtime 从开始到 final response 的时长；它不等于任一批次的日历墙钟时间，也不包含 Harbor verifier 的所有后处理。分批并发时，墙钟时间会低于所有任务 duration 的总和。

![89 tasks resource distribution](/assets/img/202610/navi-agent-terminal-bench-2-1-resource-distribution.svg)

| Per task metric | Total | Mean | Median | P90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Iterations | 2,456 | 27.6 | 22 | 51 | 51 |
| Runtime duration | 9h 44m 18s | 6m 34s | 4m 29s | 14m 47s | 40m 59s |
| Input tokens | 78.79M | 885K | 559K | 2.47M | 3.52M |
| Output tokens | 3.26M | 36.6K | 28.2K | 97.0K | 152.7K |

P90 比平均数更能揭示 harness 的长尾：10% 的任务至少消耗 **51 iterations**、**14 分 47 秒**或 **2.47M input tokens**。这也是为什么仅报告 resolution rate 不够。Terminal-Bench leaderboard 通常并列展示 resolution rate、tokens 与 cost；本文沿用这种质量—资源并列的方式，并额外给出 median/P90，让单个极重任务不会被均值掩盖。

### 每任务分布图

![Per-task iterations](/assets/img/202610/navi-agent-terminal-bench-2-1-task-iterations.svg)

![Per-task agent-loop duration](/assets/img/202610/navi-agent-terminal-bench-2-1-task-duration.svg)

![Per-task input tokens](/assets/img/202610/navi-agent-terminal-bench-2-1-task-tokens.svg)

三张图都以 89 个任务为样本，展示 P10、P25、median、P75、P90 与 maximum，而不是只展示均值。它们对应三个不同的工程问题：iteration tail 是收敛与终止问题；duration tail 是并发和 sandbox 容量问题；token tail 是上下文、工具表面和账单效率问题。

### 同一数据的每任务点图视图

![Ranked per-task dot plot](/assets/img/202610/navi-agent-terminal-bench-2-1-ranked-task-dots.png)

这里每个点代表一个任务，并按该指标自身的数值排序。它比百分位柱图更直观地展示了尾部从何处开始抬升：约 rank 70–80 后，iterations、时间和 input token 都出现明显陡升。两种图不是替代关系：**百分位柱图更适合快速汇报；点图更适合解释长尾形状与容量规划。** 先同时保留，发布前再根据文章篇幅选其一。

| Per-task metric | P25 | Median | P75 | P90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Iterations | 15 | 22 | 44 | 51 | 51 |
| Agent-loop duration | 2m 13s | 4m 29s | 9m 10s | 14m 47s | 40m 59s |
| Input tokens | 166K | 559K | 1.47M | 2.47M | 3.52M |
| Output tokens | 11.3K | 28.2K | 48.6K | 97.0K | 152.7K |

表格与点图使用相同的 89 条任务、相同的“每任务最后一次结果”口径；它不使用 provider 账单窗口的总 token。

![Trace metrics and billing window](/assets/img/202610/navi-agent-terminal-bench-2-1-estimated-cost.svg)

成本必须以账单系统为准。DeepSeek 控制台在 **2026-09-27 至 2026-10-07**、API Key `macmini, navi-agent-eval` 的实际统计为：**¥31.17、7,792 API requests、134,415,797 tokens**。这比 runtime trace 的 82.05M input + output tokens 高 1.64 倍，说明 trace 的聚合字段不能替代 provider 的计费口径（例如缓存、重试、compaction 或同 Key 的其他评测调用都可能造成差额）。

该账单窗口包含同一 eval Key 下的多次运行，因而本文不把 ¥31.17 除以 89 后声称为 Terminal-Bench 的精确单任务成本。它是这轮工程评测环境的**实际模型账单上界**，而不是严格归因后的 TB-only cost。下一轮应在 provider request metadata 中写入 `benchmark` 与 `run_id`，才能同时给出：每 task、每 verified pass、每 benchmark 的真实成本。

Modal 的费用是 sandbox CPU/内存按实际秒数计费，不能从 runtime trace 反推出精确账单；本报告只报告可复核的 Agent duration，云资源价格应以 [Modal pricing](https://modal.com/pricing) 和实际 usage 为准。这样的分离与 Augment 对 harness 的公开复盘一致：在保持质量的前提下，同时看 pass rate、wall time、input/output token 和每个完成任务成本，才能判断 harness 是否真的更有效率。[Auggie CLI harness rebuild](https://www.augmentcode.com/blog/auggie-cli-harness-rebuild-53-percent-cheaper)

## 失败不是同一种失败

### 交付遗漏：已经接近答案，但没有完成验收产物

`winning-avg-corewars` 找到了满足胜率要求的候选 warrior，并写入临时目录，却没有在预算耗尽前复制到 verifier 所要求的位置。这个问题不是“不会解题”，而是从探索到可提交产物的最后一公里失败。

`large-scale-text-editing` 也类似：Vim macro 主体正确，但遗漏 `:wq`，最终文件没有成为有效交付。

### 局部验证替代了真实验收

`build-cython-ext` 被 runtime 标记为发生过测试通过后的收敛，但 Harbor 发现多个功能测试失败。 `filter-js-from-html` 则暴露了安全任务更尖锐的问题：手写 sanitizer 的局部检查通过，并不能证明它抵抗真实 XSS payload。

因此，Navi 不应把“某条命令 exit code 为 0”升级为通用完成事实。测试证据必须与任务 acceptance 对应；Harbor verifier 的位置正是提供独立验收。

### 预算耗尽是诊断信号，不是成功

下列失败走了 `iteration_limit_summary`：`gcode-to-text`、`make-mips-interpreter`、`winning-avg-corewars`、`gpt2-codegolf`、`qemu-alpine-ssh`、`install-windows-3.11`、`mteb-leaderboard`、`extract-moves-from-video`、`make-doom-for-mips`、`train-fasttext`。

它们的共同点不是单一模型缺陷，而是长链路任务中存在大范围探索、外部依赖、构建链路或复杂交付物。Navi 保留 summary，是为了让用户和 trace 有一个可诊断的结束点；它不会把这类结束算作 verified completion。

### 环境异常需要与实现失败分开

评测中见到了 apt 锁、包仓库漂移、二进制输出导致 sandbox adapter 解码异常等情况。这些都不能简单归因为 Agent “能力差”。报告中仍保留 verifier 结果，但后续失败分析会将环境阻塞、命令使用错误、实现错误、验证不足分开处理。

## Navi runtime 的设计取舍

这次没有通过堆叠 planner、critic、verifier agent 或 benchmark 特判来提高结果。核心仍然保持为：

```text
TaskSpec(objective, acceptance, constraints)
        ↓
Runtime session + tool loop
        ↓
Sandbox execution
        ↓
Trace / tool evidence
        ↓
External verifier
```

几个有意识的边界：

- runtime 不认识 Terminal-Bench、Harbor、pytest 或特定目标路径；
- eval adapter 提供任务环境和 verifier，核心只处理通用任务、工具与完成语义；
- trace 记录过程，不作为“任务完成”的事实来源；
- 模型最终文本是声明，不是验收证据；
- 接近 iteration budget 时不注入“尽快完成”的压力提示，避免复杂任务过早放弃。

最后一点来自真实取舍：某些失败确实是交付遗漏，但对所有任务提示“马上结束”会将探索型任务推向更早失败。与其制造虚假的低 iteration，不如保留失败 trajectory，再从证据和验收设计中改进。

## 结果总表

以下表格采用每个任务的最后一次结果。 `C` 表示 runtime 有非空 final response，`I` 表示没有有效 final response；Harbor 列才是正确性判定。首列是阅读辅助的 task focus，**不是**上节的官方 `metadata.category`；官方分类以聚合表为准。早期 smoke eval 的归档日志已重新读取，因此 89 条任务的 iteration 均已补齐。

| Domain | Task | Harbor | Iterations | Runtime | Completion reason |
| --- | --- | --- | ---: | --- | --- |
| Systems | `write-compressor` | PASS | 44 | C | early smoke run |
| ML systems | `torch-tensor-parallelism` | PASS | 37 | C | early smoke run |
| Language runtime | `schemelike-metacircular-eval` | PASS | 30 | C | success |
| Distributed systems | `kv-store-grpc` | PASS | 12 | C | early smoke run |
| Packaging | `pypi-server` | PASS | 16 | C | early smoke run |
| Async programming | `cancel-async-tasks` | PASS | 13 | C | success |
| Debugging | `custom-memory-heap-crash` | PASS | 20 | C | success |
| Database forensics | `db-wal-recovery` | PASS | 27 | C | success |
| Binary analysis | `extract-elf` | PASS | 21 | C | success |
| Git workflow | `fix-git` | PASS | 13 | C | success |
| Web operations | `nginx-request-logging` | PASS | 14 | C | success |
| Polyglot build | `polyglot-rust-c` | PASS | 17 | C | success |
| Security / Git | `sanitize-git-repo` | PASS | 24 | C | success |
| Python build | `build-cython-ext` | FAIL | 44 | C | tests passed without subsequent mutation |
| Compiler build | `compile-compcert` | PASS | 51 | C | iteration limit summary |
| Web operations | `configure-git-webserver` | PASS | 20 | C | success |
| Git workflow | `git-multibranch` | PASS | 22 | C | success |
| Text editing | `large-scale-text-editing` | FAIL | 19 | C | success |
| Polyglot build | `polyglot-c-py` | FAIL | 18 | C | success |
| Virtualization | `qemu-startup` | FAIL | 37 | C | success |
| Security | `break-filter-js-from-html` | PASS | 11 | C | success |
| Scheduling | `constraints-scheduling` | PASS | 6 | C | success |
| Security | `filter-js-from-html` | FAIL | 31 | C | success |
| Security | `fix-code-vulnerability` | PASS | 11 | C | success |
| Security / Git | `git-leak-recovery` | PASS | 13 | C | success |
| Terminal UX | `headless-terminal` | PASS | 15 | C | success |
| Log processing | `log-summary-date-ranges` | PASS | 7 | C | success |
| TLS / security | `openssl-selfsigned-cert` | PASS | 7 | C | success |
| Digital forensics | `password-recovery` | PASS | 21 | C | success |
| SQL | `query-optimize` | PASS | 35 | C | success |
| Database forensics | `sqlite-db-truncate` | PASS | 10 | C | success |
| Binary security | `vulnerable-secret` | PASS | 10 | C | success |
| Statistics | `adaptive-rejection-sampler` | FAIL | 12 | I | success |
| Chess | `chess-best-move` | PASS | 50 | C | success |
| Legacy modernization | `cobol-modernization` | PASS | 43 | C | success |
| Data processing | `count-dataset-tokens` | PASS | 22 | C | success |
| Password cracking | `crack-7z-hash` | PASS | 16 | C | success |
| G-code | `gcode-to-text` | FAIL | 51 | C | iteration limit summary |
| Emulator | `make-mips-interpreter` | FAIL | 51 | C | iteration limit summary |
| Data transformation | `merge-diff-arc-agi-task` | FAIL | 26 | C | success |
| Scientific Python | `modernize-scientific-stack` | PASS | 6 | C | success |
| Data processing | `multi-source-data-merger` | PASS | 11 | C | success |
| Typesetting | `overfull-hbox` | PASS | 29 | C | success |
| Log processing | `regex-log` | PASS | 18 | C | success |
| SPARQL | `sparql-university` | PASS | 19 | C | success |
| Robotics | `tune-mjcf` | PASS | 42 | C | success |
| Core War | `winning-avg-corewars` | FAIL | 51 | C | iteration limit summary |
| Legacy build | `build-pov-ray` | PASS | 42 | C | success |
| Circuit design | `circuit-fibsqrt` | FAIL | 2 | I | success |
| Bioinformatics | `dna-assembly` | FAIL | 32 | C | success |
| Bioinformatics | `dna-insert` | PASS | 28 | C | success |
| Document processing | `financial-document-processor` | PASS | 18 | C | success |
| Code golf | `gpt2-codegolf` | FAIL | 51 | C | iteration limit summary |
| Numerical computing | `largest-eigenval` | PASS | 51 | C | iteration limit summary |
| Model extraction | `model-extraction-relu-logits` | PASS | 19 | C | success |
| Formal methods | `prove-plus-comm` | PASS | 10 | C | success |
| Virtualization | `qemu-alpine-ssh` | FAIL | 51 | C | iteration limit summary |
| Scientific computing | `raman-fitting` | PASS | 46 | C | success |
| Chess / regex | `regex-chess` | FAIL | 3 | I | success |
| Coverage tooling | `sqlite-with-gcov` | PASS | 16 | C | success |
| ML systems | `torch-pipeline-parallelism` | PASS | 36 | C | tests passed without subsequent mutation |
| Video processing | `video-processing` | PASS | 50 | C | success |
| Statistics | `bn-fit-modify` | PASS | 19 | C | success |
| Core War | `build-pmars` | PASS | 26 | C | success |
| ML training | `caffe-cifar-10` | PASS | 47 | C | success |
| Cryptanalysis | `feal-linear-cryptanalysis` | PASS | 8 | C | success |
| Model inference | `hf-model-inference` | PASS | 12 | C | success |
| Legacy systems | `install-windows-3.11` | FAIL | 51 | C | iteration limit summary |
| LLM systems | `llm-inference-batching-scheduler` | FAIL | 36 | C | success |
| Mail systems | `mailman` | PASS | 51 | C | iteration limit summary |
| Information retrieval | `mteb-leaderboard` | FAIL | 51 | C | iteration limit summary |
| Information retrieval | `mteb-retrieve` | PASS | 49 | C | success |
| Optimization | `portfolio-optimization` | PASS | 19 | C | success |
| Data infrastructure | `reshard-c4-data` | PASS | 18 | C | success |
| Vision / OCR | `code-from-image` | PASS | 24 | C | success |
| Search | `distribution-search` | PASS | 10 | C | success |
| Video analysis | `extract-moves-from-video` | FAIL | 51 | C | iteration limit summary |
| Cryptanalysis | `feal-differential-cryptanalysis` | PASS | 8 | C | success |
| Runtime / GC | `fix-ocaml-gc` | PASS | 51 | C | iteration limit summary |
| Emulator | `make-doom-for-mips` | FAIL | 51 | C | iteration limit summary |
| Bayesian statistics | `mcmc-sampling-stan` | PASS | 17 | C | success |
| Rendering | `path-tracing` | PASS | 22 | C | success |
| Rendering / inverse | `path-tracing-reverse` | PASS | 25 | C | success |
| Bioinformatics | `protein-assembly` | PASS | 29 | C | success |
| ML tooling | `pytorch-model-cli` | FAIL | 22 | C | success |
| Model recovery | `pytorch-model-recovery` | PASS | 28 | C | success |
| Statistical migration | `rstan-to-pystan` | PASS | 51 | C | iteration limit summary |
| Computer vision | `sam-cell-seg` | PASS | 51 | C | iteration limit summary |
| ML training | `train-fasttext` | FAIL | 51 | C | iteration limit summary |

## 如何阅读这个结果

Terminal-Bench 的公开 leaderboard 用不同 agent、模型、prompt、token budget、hardware 与运行次数形成结果。因而 75.3% 不是与 Codex、Claude Code 或其他提交可以一一等价比较的排名；它是 Navi-agent 在这一固定运行设置下的全量经验数据。

![Terminal-Bench 2.1 leaderboard snapshot](/assets/img/202610/terminal-bench-2-1-leaderboard-2026-10-07.png)

上图是 2026-10-07 保存的 Terminal-Bench 2.1 官方榜单截图。它的列顺序本身就是本文的报告模板：**resolution rate、tokens、cost**。榜单前排的 75%–87% 来自不同模型、harness 与大量试验的正式提交；Navi 的 67/89 是按本文聚合规则得到的分批运行汇总，能说明“系统在这组任务上的实际行为”，不能声称“官方 rank”。

![DeepSeek billing window](/assets/img/202610/deepseek-eval-billing-window-2026-10-07.png)

上图保存的是同一 eval API Key 的 DeepSeek 控制台账单窗口，作为上一节实际成本口径的原始证据。它与 trace 的差异正是后续要解决的可观测性问题：让 provider billing、run、task 三者可关联。

这份数据更适合回答以下问题：

- 轻量 runtime 是否能稳定地把 coding agent 接到云端 sandbox 和独立 verifier？可以。
- runtime 正常结束是否足够？不够，必须继续看验收证据。
- 失败应先归因于 runtime 吗？不能。22 个失败中既有实现/推理失败，也有交付遗漏、环境依赖和预算长尾。
- 下一步应该先把 50 轮改成 100 轮吗？不应该。应先用失败 trajectory 改善 acceptance evidence、环境诊断和任务交付闭环。

## 可复查材料

Inspect eval logs 保存在 Mac mini：

```text
~/.navi-agent/evals/inspect/
2026-10-05T09-38-49-00-00_navi-terminal-bench-2-1_MQxUuQkhRTggUks77zZZoP.eval
2026-10-05T14-52-00-00-00_navi-terminal-bench-2-1_NyWz3AtbpvHswVNfFN6GQH.eval
2026-10-06T00-31-41-00-00_navi-terminal-bench-2-1_ACvG6G7rKGyeBatnD82t5u.eval
2026-10-06T07-06-57-00-00_navi-terminal-bench-2-1_F5ZtrLdaUuL2XamsmwjBbu.eval
2026-10-06T08-26-23-00-00_navi-terminal-bench-2-1_GauYdNPK4H96sxXig6AujE.eval
2026-10-06T11-05-00-00-00_navi-terminal-bench-2-1_7GsnezeQLY4kE74gUSouNc.eval
2026-10-06T13-57-33-00-00_navi-terminal-bench-2-1_5KwyywWPypFYLWsSeU53V5.eval
2026-10-06T14-06-34-00-00_navi-terminal-bench-2-1_CPdKtt4Z2gdrLGY3A6ARAs.eval
```

![Inspect sample: query-optimize](/assets/img/202610/inspect-query-optimize-harbor-pass-2026-10-07.png)

上图是 `terminal-bench/query-optimize` 的 Inspect sample 页面。它是**代表性单样本证据**：页面同时显示任务输入、`harbor_scorer = PASS / 1` 和 `navi_runtime = C`，用于展示“runtime 完成”和“独立 verifier 通过”在同一运行中如何对应。它不参与 89 条任务的聚合统计；总表和 eval logs 才是汇总结果的事实来源。

后续文章会单独解释 Terminal-Bench 的任务分类与 leaderboard；本文聚焦 Navi-agent 的实际运行记录与运行时评估方法。

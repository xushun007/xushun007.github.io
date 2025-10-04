---
title: 开源Agent架构的设计与实现之：OpenCode
author: xushun
date: 2025-10-03
categories: [Agent]
tags: [Agent, OpenCode]
render_with_liquid: false
---

**OpenCode 是一个专为终端设计的开源 AI 编码 Agent 框架**。它提供了完整的 AI 辅助编程能力，支持多种 LLM 提供商，以终端界面（TUI）为第一交互界面。其核心目标是解决一个很实际的问题：**如何让 AI 编程助手真正好用**。

本文基于OpenCode v0.14.1 版本分析撰写，分析其系统架构与实现，以学习其设计。

## 一、应用场景

在实际的软件开发和维护任务中，我们可畅想以下几种场景，AI 编码工具能为我们做什么？

- 场景一：深度重构遗留代码

你接手了一个 5 年前的 Java 项目，代码行超过10万，代码结构混乱，文档缺失。传统做法是花几天时间阅读代码，但用 OpenCode：

```bash
cd legacy-project && opencode

"帮我分析这个项目的架构，找出主要的技术债务，并制定重构计划，然后按模块进行重构，并验证它的正确性。"

OpenCode 会：
- 用 `grep` 和 `read` 工具扫描整个项目
- 分析依赖关系、代码结构
- 生成重构建议和具体步骤
- 在子会话中逐步执行重构，每步都可以回滚
- 编写单元测试验证逻辑的正确性
```

- 场景二：多语言项目的一致性维护
你维护着一个包含前端（React）、后端（Java）、移动端（Flutter）的项目。需要在三端同步一个 API 变更。用 OpenCode处理...

- 场景三：调试线上问题：凌晨 2 点，线上服务出问题了。你 SSH 到服务器，在终端环境，通过opencode 分析最近 1 小时的错误日志，找出根因并给出修复方案。

- 场景四：开源项目的贡献

你想给一个大型开源项目贡献代码，但项目很复杂，不知道从哪下手，你可以给opencode指令：`我想给这个项目添加 XXX 功能，帮我：1. 理解现有的架构和代码风格；2. 写出符合项目规范的代码；3. 生成测试和文档。`

注：此类场景不局限于OpenCode。Claude Code，Codex和Gemini CLI 等都有不同的优异表现。

---

## 二、核心设计理念

OpenCode 的架构设计体现了以下核心思想：

### 2.1 C/S 架构模式

OpenCode 采用 **TypeScript 服务端 + 多客户端** 的架构：

<img src="assets/img/202510/20251003_1.png" alt="agent" width="80%" >
*（OpenCode C/S架构）*



这种设计带来的优势：
- **前端多样化**：TUI、CLI、IDE 插件可共享同一后端
- **状态管理集中**：会话、文件状态、工具执行都在服务端统一管理
- **远程协作友好**：服务端可运行在远程机器，客户端轻量连接


### 2.2 ReAct 主循环

 OpenCode 和主流的ReAct Agent设计思路类似，它的核心解决方案也是通过ReAct 主循环（推理+行动+观察）进行处理，其包含丰富的工具集合，消息管理和异常处理机制，使得Agent 具备足够的健壮性和扩展性。

 设计思路：
- Tool抽象，Agent 的能力边界清晰可控
- 通过配置工具集即可定制 Agent 行为
- 工具可独立测试、复用和组合

 某种程度讲，Tool 是Agent 能触达的能力边界，OpenCode 主要包含的Tool 分类：任务规划、文件操作、代码搜索、命令执行(bash)和网络访问和任务管理。


### 2.3 事件驱动架构

模块间通信通过 **Bus 事件总线** 实现：

- 松耦合：模块之间不直接依赖，通过事件通信
- 可观测：所有关键状态变化都发布事件
- 实时同步：客户端通过 SSE 订阅事件流，实现实时更新


### 2.4 会话即上下文

OpenCode 的核心抽象之一是 **Session**：

- 每个 Session 独立管理消息历史、工具调用记录和文件状态
- 支持父子会话（Parent-Child Session）用于任务分解
- 会话可以被分享、回滚、压缩

### 2.5 灵活可定制的Agent 配置

OpenCode 的 Agent 的技术概念本质上是**配置模板**，而非真正的多 Agent 系统，其内部定义了build, plan和general 三个Agent。每个 Agent包含：

- **工具权限**：哪些工具可用（`tools: { bash: true, edit: false }`）
- **执行权限**：文件编辑、命令执行的权限级别（`allow`/`deny`/`ask`）
- **系统提示**：针对特定任务优化的 prompt
- **模型配置**：可选的特定模型和参数

这种设计的优势是**简单可控**：
- 用户可以快速在不同权限模式间切换
- 通过配置文件轻松定制 Agent 行为
- 避免了复杂的多 Agent 协调问题

---

## 三、架构深度解析

### 3.1 整体架构

<img src="assets/img/202510/20251003_2.png" alt="agent" width="100%" >
*（OpenCode 整体架构）*

**架构说明**：

上图展示了 OpenCode 的整体架构，分为两层：

**Client Layer（客户端层）**：
- **CLI**：命令行接口
- **TUI**：终端用户界面（Go 实现）
- **IDE Ext**：IDE 扩展（如 VSCode）
- **SDK**：提供 Go 和 TypeScript 两种语言的 SDK

**Server Layer（服务端层）**：
- **Server (REST API + SSE)**：基于 Hono 的 HTTP 服务器，提供 REST API 和 Server-Sent Events
- **三大核心模块**：
  - **Agent**：内置和可自定义的Agent 模版
  - **Session**：多层次的会话和消息管理，ReAct 循环
  - **Tool**：解决编程问题所依赖的工具体系
- **Event Bus**：事件驱动的模块间通信
- **基础设施层**：
  - **Storage**：持久化存储，支持Session, Message和Project的JSON数据存储
  - **LLM Provider**：多LLM 提供商，支持OpenAI、Anthropic、Google、Amazon和OpenAI 兼容厂商。
  - **Instance Context**：运行时上下文隔离


**端到端核心调用链**：
```
Client → SDK → REST API → SessionPrompt → Tools + Messages 上下文准备
                                                        ↓
                返回结果 <-  Tool.execute()  <-   LLM (streamText)
                                          ↓
                             Event Bus → SSE → Client
```

**存储物理结构**：
```
~/.local/share/opencode/storage/
  ├── session/{projectID}/{sessionID}.json   
  ├── message/{sessionID}/{messageID}.json   
  ├── part/{messageID}/{partID}.json         
  ├── project/{projectID}.json               
  └── share/{sessionID}.json                
```

### 3.2 核心模块详解

#### 3.2.1 Agent 配置模块

**定义**：Agent 是一组配置的集合，定义了 LLM 的行为、可用工具和权限边界。

```typescript
// agent/agent.ts Agent 的核心结构（已简化，省略了 Zod 验证细节和部分字段）
interface Agent {
  name: string              // Agent 标识符
  description?: string      // 描述其用途
  mode: "primary" | "subagent" | "all"  // 使用场景
  model?: {                 // 可选：指定特定模型
    providerID: string
    modelID: string
  }
  prompt?: string          // 自定义 system prompt
  tools: Record<string, boolean>  // 可用工具清单
  permission: {            // 权限配置
    edit: "allow" | "deny" | "ask"
    bash: Record<string, Permission>
    webfetch: Permission
  }
  temperature?: number
  topP?: number
}
```

**特点**：
1. 声明式Agent：从配置文件读取用户自定义 Agent，核心包括自定义模型，系统提示词和工具列表，无需编写代码
2. 内置 Agent（build、general、plan）
- **build**：完整权限，适合实际开发工作
- **general**：搜索优化，适合代码分析和研究（通过 `task` 工具调用）
- **plan**：受限权限，只能分析不能修改


#### 3.2.2 ReAct 循环

**核心循环代码**（简化版）：

- 上下文准备，包括系统提示、可用工具集和模型等
- 主循环：
  - 推理：构建上下文，调用LLM
  - 行动：执行工具
  - 观察：拼接结果，判断是否完成任务

```typescript
// session/prompt.ts - SessionPrompt.prompt() 核心流程
export async function prompt(input: PromptInput): Promise<MessageV2.WithParts> {
  // === 准备阶段 ===
  const session = await Session.get(input.sessionID)
  const userMsg = await createUserMessage(input)

  // 解析配置
  const agent = await Agent.get(input.agent ?? "build")
  const model = await resolveModel({ agent, model: input.model })
  const system = await resolveSystemPrompt({ agent, ... })
  const processor = await createProcessor({ sessionID, model, agent, ... })
  const tools = await resolveTools({ agent, sessionID, modelID, providerID, ... })
    
  // === ReAct 主循环 ===
  while (true) {
    // 1. Reason (推理阶段)
    const msgs = await getMessages({ sessionID, model, providerID })
    
    await processor.next()
    const stream = streamText({
      messages: [...system, ...MessageV2.toModelMessage(msgs)],
      tools,
      model: model.language,
    })
    
    // 2. Act (行动阶段)
    const result = await processor.process(stream)
    await processor.end()
    
    // 3. Decide (决策阶段)
    const queued = state().queued.get(sessionID) ?? []
    
    if (!result.blocked && !result.info.error) {
      if ((await stream.finishReason) === "tool-calls") {
        continue  // LLM 调用了工具，继续循环观察结果
      }
      
      const unprocessed = queued.filter((x) => x.messageID > result.info.id)
      if (unprocessed.length) {
        continue  // 有未处理的消息，继续循环
      }
    }
    
    // 所有条件满足，退出循环
    for (const item of queued) item.callback(result)
    state().queued.delete(sessionID)
    return result
  }
}
```

**循环退出条件**：
- LLM 完成推理（`finishReason !== "tool-calls"`）
- 没有权限阻塞（`!result.blocked`）
- 没有错误（`!result.info.error`）
- 队列为空（`unprocessed.length === 0`） 

#### 3.2.3 会话管理

**核心说明**：

OpenCode 的会话管理由两个命名空间组成：

- **Session namespace** (`session/index.ts`)：提供会话 CRUD、消息管理、分享等功能
- **SessionPrompt namespace** (`session/prompt.ts`)：核心ReAct编排者，负责 LLM 推理和工具调用


##### 会话管理 API

| 端点 | 方法 | 描述 | 输入 | 输出 |
|------|------|------|------|------|
| `/session` | POST | 创建新会话 | parentID?, title? | Session.Info |
| `/session/:id` | GET | 获取会话详情 | id (param) | Session.Info |
| `/session/:id` | PATCH | 更新会话属性 | id, title? | Session.Info |
| `/session/:id` | DELETE | 删除会话及其数据 | id | boolean |
| `/session/:id/init` | POST | 初始化项目（生成 AGENTS.md） | id, messageID, providerID, modelID | boolean |
| `/session/:id/summarize` | POST | 总结会话历史 | id, providerID, modelID | boolean |
| `/session/:id/revert` | POST | 回滚消息 | id, messageID | Session.Info |

##### 消息管理 API

| 端点 | 方法 | 描述 | 输入 | 输出 |
|------|------|------|------|------|
| `/session/:id/message` | GET | 获取会话的所有消息 | id | MessageV2.WithParts[] |
| `/session/:id/message/:messageID` | GET | 获取单条消息 | id, messageID | { info, parts } |
| `/session/:id/message` | POST | 发送新消息（触发 LLM 推理）| id, parts[], agent?, providerID?, modelID? | { info, parts } |



```typescript
// Session namespace - 会话数据管理
export namespace Session {
  export async function create() { ... }
  export async function get() { ... }
  export async function messages() { ... }
  export async function share() { ... }
}

```

#### 3.2.4 工具系统

OpenCode 的 Tool 机制是整个系统的核心功能，它允许 AI Agent 通过定义好的工具与文件系统、构建工具、LSP 等进行交互。Tool 系统采用了模块化设计，支持内置工具、自定义工具和插件工具。

**核心文件结构**
```
packages/opencode/src/tool/
├── tool.ts              # Tool 核心定义
├── registry.ts          # Tool 注册管理
├── [tool-name].ts       # 各种 tool 实现
├── [tool-name].txt      # Tool 描述文本
└── invalid.ts           # 无效工具处理
```
**核心关系说明**：

Agent、Session、LLM和Tool 几者的关系：

- **Agent 是配置模板**，不是执行主体
- **SessionPrompt 是编排者**，负责整个推理流程
- **LLM 是决策者**，决定调用哪些工具
- **Tool 是能力提供者**，定义具体执行逻辑

**关键代码**：

```typescript

// 工具定义 tool/tool.ts
export namespace Tool {
  export interface Info<Parameters extends z.ZodType = z.ZodType, M extends Metadata = Metadata> {
    id: string
    init: () => Promise<{
      description: string
      parameters: Parameters
      execute(args: z.infer<Parameters>,ctx: Context,
      ): Promise<{
        title: string
        metadata: M
        output: string
      }>
    }>
  }
...
}

// TodoWrite Tool 定义 tool/todo.ts
export const TodoWriteTool = Tool.define("todowrite", {
  description: DESCRIPTION_WRITE,
  parameters: z.object({
    todos: z.array(TodoInfo).describe("The updated todo list"),
  }),
  async execute(params, opts) {
    const todos = state()
    todos[opts.sessionID] = params.todos
    return {
      title: `${params.todos.filter((x) => x.status !== "completed").length} todos`,
      output: JSON.stringify(params.todos, null, 2),
      metadata: {
        todos: params.todos,
      },
    }
  },
})

// 工具注册 tool/registry.js
  export async function register(tool: Tool.Info) {
    const { custom } = await state()
    const idx = custom.findIndex((t) => t.id === tool.id)
    if (idx >= 0) {
      custom.splice(idx, 1, tool)
      return
    }
    custom.push(tool)
  }
```

**内置工具清单**：

| 工具 | 功能 | 典型用途 |
|-----|------|---------|
| `read` | 读取文件内容 | 查看代码、配置文件 |
| `write` | 创建或覆盖文件 | 生成新文件 |
| `edit` | 精确编辑文件的某个区域 | 修改现有代码 |
| `patch` | 应用 diff patch | 批量修改 |
| `bash` | 执行 shell 命令 | 运行测试、构建、安装依赖 |
| `grep` | 文本搜索（ripgrep） | 搜索代码片段 |
| `glob` | 文件名匹配 | 查找文件 |
| `ls` | 列出目录内容 | 浏览项目结构 |
| `webfetch` | 获取网页内容 | 查阅文档 |
| `todo` | 任务管理 | 多步任务分解 |
| `task` | 子任务委托 | 子任务执行单元 |


**工具注册与执行流程**：

```
1. ToolRegistry.register() ─► 注册工具到全局注册表                    
2. Agent 配置中启用工具 ─► tools: { bash: true, edit: false }                     
3. SessionPrompt.prompt() ─► 构建 AI SDK 的 tools 对象                         
4. LLM 返回工具调用请求 ─► { tool: "read", args: {...} }                         
5. 权限检查 ─► Permission.check()                         
6. 执行工具 ─► Tool.execute()                        
7. 结果返回给 LLM ─► 继续推理或结束
```

**扩展机制**：

- **插件系统**：通过 `@opencode-ai/plugin` 包定义自定义工具
- **本地工具目录**：在项目目录下创建 `tool/` 文件夹，自动加载 `.ts` 或 `.js` 工具
- **MCP 集成**：支持 Model Context Protocol 工具

#### 3.2.5 LLM Provider

OpenCode 支持以下 LLM 提供商：

- **Anthropic**（Claude 3.7 Sonnet、Claude 4.0 Sonnet 等）
- **OpenAI**（GPT-4、GPT-4o 等）
- **Google**（Gemini Pro、Gemini Flash 等）
- **Amazon Bedrock**
- **本地模型**（通过 OpenAI 兼容接口）


**统一调用**：使用 Vercel AI SDK 的 `streamText` / `generateText` API，屏蔽不同提供商的差异。

#### 3.2.6 事件总线 (Event Bus)

Event Bus 使用**发布-订阅模式**（Pub/Sub）实现。

<img src="assets/img/202510/20251003_3.png" alt="agent" width="80%" >


**关键设计原则**

1. **项目隔离**: 使用 `Instance.state()` 确保多项目安全
2. **异步解耦**: 发布者、订阅者链路解耦
3. **实时推送**: SSE 订阅所有事件并推送给客户端

核心代码结构：

```typescript

// bus/index.ts
export namespace Bus {
  // 使用 Instance.state 实现多项目隔离
  const state = Instance.state(() => {
    const subscriptions = new Map<any, Subscription[]>()
    return { subscriptions }
  })

  // 事件注册表（全局）
  const registry = new Map<string, EventDefinition>()
}
```

会话/消息/权限/工具执行事件 以及其他类事件

**模块**: `packages/opencode/src/session/index.ts`

| 事件类型 | 触发时机 | 数据结构 |
|---------|---------|---------|
| `session.updated` | 会话创建/更新时 | `{ info: Session.Info }` |
| `session.deleted` | 会话删除时 | `{ info: Session.Info }` |
| `session.error` | 会话处理出错时 | `{ sessionID?, error: NamedError }` |
| `message.updated` | 消息创建/更新时 | `{ info: MessageV2.Info }` |
| `message.removed` | 消息删除时 | `{ sessionID, messageID }` |
| `message.part.updated` | 消息片段更新（工具调用、流式响应） | `{ part: MessageV2.Part }` |
| `message.part.removed` | 消息片段删除时 | `{ sessionID, messageID, partID }` |
| `permission.updated` | 权限请求创建时 | `Permission.Info` |
| `permission.replied` | 用户响应权限请求 | `{ sessionID, permissionID, response }` |


因篇幅有限，还有不少有趣的点，如上下文隔离


## 四、实践上手

### 4.1 安装 OpenCode

```bash
curl -fsSL https://opencode.ai/install | bash

```

### 4.2 任务

```
设计并实现一个微博系统的解决方案来让用户快速将他所发布的微博信息推送给所有的关注者，使用Java实现。
```

### 4.3 结果

OpenCode 先进行了系统的整体设计，产出了设计文档，然后按模块逐步构建系统，最终对结果进行验证。

中间过程中，出现过几次因网络错误，但因整体的上下文都能通过storage模块保存，因此能很容易恢复。
在项目验证过程中，为了系统能够快速运行，Agent自主的对设计文档进行两处修改：一是将MySQL 替换成内存数据库H2；二是将Redis 替换成内存实现。

人工的干预：将java11 降级到java8；通过`继续`命令触发连续执行；

总体上来讲，虽然没有 Claude Code 的使用流畅，但使用 Grok 模型的 OpenCode 仍令人满意。

<img src="assets/img/202510/20251003_4.png" alt="agent" width="80%" >
*(最终执行结果)*

<img src="assets/img/202510/20251003_5.png" alt="agent" width="80%" >
*(会话/消息持久化数据)*


---

## 五、总结

从一位工程师的视角看OpenCode。

毫无疑问，OpenCode 是一个**设计理念先进但仍在打磨细节**的工具。

优点：

- 多LLM无缝切换：不绑定LLM 提供商；同一项目可随时切换模型，利用各家所长，尤其LLM快速发展情况下。
- 100% 开源：完全开源透明，OpenCode 的设计也参考了Claude Code，Gemini和QWen的思路，尤其在提示词最为明显。
- 会话持久化+可分享：出错可回滚，遇到问题可分享完整上下文
- 事件驱动：逻辑执行和终端展示进行了深度解耦。
- 工具可扩展：工具丰富，且可用 TS 自定义工具，通过丰富的工具集赋予 Agent 强大能力。
- 完备的Agent解决方案：其实现对设计一个泛化的Agent 系统具有现实的参考意义。尤其是工具体系和存储体系。

不足：

- 缺乏显式的沙箱机制：缺乏进程级沙箱隔离（如容器化），虽然有完善的权限询问机制，但恶意代码仍可能在用户批准后执行。
- 多模态支持不完备：主要处理文本和代码，但缺乏对音频、视频等非图像媒体的深度集成。
- 代码可读性不足：在核心的ReAct 循环设计上，一是命名上，`SessionPrompt`作为载体明显不合适；二是其核心设计过于冗长。
- JSON存储性能瓶颈：当session，message的数量达到上万，因缺乏索引机制，会明显拖慢响应速度，建议采用SQLite或建立消息索引。
- TUI 中文显示问题：在 macOS 终端上，中英文混排时列对齐错乱，长文本偶尔不显示。



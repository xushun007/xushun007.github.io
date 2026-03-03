---
title: 《Effective AI Agent》条目 11: 为工具调用构建“零信任”的防御性校验
author: xushun
date: 2026-03-03
categories: [Agent]
tags: [Agent, Effective AI Agent]
render_with_liquid: false
---

# 条目 11: 为工具调用构建“零信任”的防御性校验

## 背景动机

Gemini CLI 曾出现一个典型故障：`WebSearchTool` 遇到带未转义引号的 query，触发 JSON 解析异常，直接导致 CLI 崩掉。根因很简单：**缺少输入校验与清洗**。

在 Agent 系统里，这类问题会被放大。LLM 生成的 tool args 本质上就是**外部输入**。不经校验就进入 Shell、支付，结果就不只是报错，而是故障、甚至资损。

## 原理分析

系统稳不稳，取决于你如何看待 tool args：

* 当作**内部对象**，就会默认它完整、正确、可信；
* 当作**外部请求**，才会去做结构校验、语义校验、权限校验和审计。

Gemini CLI 的思路很清晰：

* 用 schema 约束参数结构
* 用 validator 校验业务规则
* 用 policy 决定是否允许执行
* 用固定协议约束工具输入输出边界

## 示例代码

Gemini CLI 当前实现了完整的参数校验体系，值得 Agent 开发者借鉴：

### 1. **JSON Schema 验证（结构层）**

使用 AJV (Another JSON Schema Validator) 进行强制类型检查，包括参数类型检查、必填字段检查和数据格式验证。

```typescript
// packages/core/src/utils/schemaValidator.ts
export class SchemaValidator {
  static validate(schema: unknown | undefined, data: unknown): string | null {
    if (!schema) return null;
    if (typeof data !== 'object' || data === null) {
      return 'Value of params must be an object';
    }
    
    const validate = ajValidator.compile(schema);
    const valid = validate(data);
    
    if (!valid && validate.errors) {
      return ajValidator.errorsText(validate.errors, { dataVar: 'params' });
    }
    return null;
  }
}
```

### 2. **业务规则验证（语义层）**

每个工具通过 `validateToolParamValues()` 实现自定义校验逻辑，包括安全边界、业务约束、资源权限和风控规则。

```typescript
// ReadFileTool 的参数验证示例
protected override validateToolParamValues(
  params: ReadFileToolParams
): string | null {
  // 1. 非空检查
  if (params.file_path.trim() === '') {
    return "The 'file_path' parameter must be non-empty.";
  }
  
  // 2. 路径安全检查（防止目录遍历攻击）
  const resolvedPath = path.resolve(this.config.getTargetDir(), params.file_path);
  if (!workspaceContext.isPathWithinWorkspace(resolvedPath)) {
    return `File path must be within workspace directories`;
  }
  
  // 3. 数值范围校验
  if (params.offset !== undefined && params.offset < 0) {
    return 'Offset must be a non-negative number';
  }
  if (params.limit !== undefined && params.limit <= 0) {
    return 'Limit must be a positive number';
  }
  
  // 4. 文件过滤规则检查（.gitignore/.geminiignore）
  if (fileService.shouldIgnoreFile(resolvedPath, fileFilteringOptions)) {
    return `File path is ignored by configured patterns`;
  }
  
  return null;
}
```



### 3. **策略引擎验证（执行层）**

通过 MessageBus + Policy Engine 实现动态策略控制，策略：自动放行、明确拒绝和权限请求：

```typescript
// BaseToolInvocation.shouldConfirmExecute()
async shouldConfirmExecute(abortSignal: AbortSignal): Promise<ToolCallConfirmationDetails | false> {
  // 查询策略引擎决策
  const decision = await this.getMessageBusDecision(abortSignal);
  
  if (decision === 'ALLOW') {
    return false; // 自动放行
  }
  
  if (decision === 'DENY') {
    throw new Error(`Tool execution denied by policy`);
  }
  
  if (decision === 'ASK_USER') {
    // 返回确认详情，等待用户交互
    return this.getConfirmationDetails(abortSignal);
  }
}
```


## 工程实践

1. **分层校验**：结构、语义、策略，缺一不可。
2. **Fail Closed**：校验失败就拒绝执行。
3. **高危工具加护栏**：Shell、SQL、文件、支付必须做代码级限制。
4. **错误结构化**：区分参数错误、策略拒绝、执行失败。
5. **把工具当 API**：有 schema、有协议、有日志、有审计。


## 参考文献

* **Gemini CLI Issue #4277**, *Unhandled Exception in WebSearchTool Due to Unescaped Quotation Marks in Query Input #4277* - `https://github.com/google-gemini/gemini-cli/issues/4277`
* **Gemini CLI**, *Gemini CLI core: Tools API* - `https://geminicli.com/docs/core/tools-api/`
* **Gemini CLI**, *Shell tool (`run_shell_command`)* - `https://geminicli.com/docs/tools/shell/`
* **OpenAI**, *Introducing Structured Outputs in the API* - `https://openai.com/index/introducing-structured-outputs-in-the-api/`
* **Anthropic**, *Building effective agents* - `https://www.anthropic.com/engineering/building-effective-agents`
* **Google Gemini**, *Gemini CLI Repository* - `https://github.com/google-gemini/gemini-cli`
---
title: Vibe Coding：新乐园还是潘多拉魔盒？记一次MacOS APP 开发
author: xushun
date: 2025-04-20 23:00:00 +0800
categories: [Agent]
tags: [Agent, Vibe Coding]
render_with_liquid: false
---

近期，软件开发界掀起了一股名为“Vibe Coding”的新浪潮，引发了广泛的讨论甚至争议。它的核心理念在于利用大模型（LLM）根据自然语言描述来生成代码，从而极大地改变了开发者的角色。

## 解码Vibe Coding：起源与核心理念

“Vibe Coding”这一术语的广泛传播始于Andrej Karpathy在2025年2月发布的一条社交媒体帖子。他将其描述为一种“全新的编码方式”，特点是“完全沉浸于感觉（vibes），甚至忘记代码的存在” 。这与他早先提出的“最热门的新编程语言是英语”的观点一脉相承，即LLM的进步使得人类无需学习特定的编程语言也能指挥计算机。

<img src="assets/img/202504/kpath.png" alt="Karpathy" width="80%" >


Karpathy最初将这种方式定位为适用于“一次性的周末项目”，承认其存在高度依赖AI、纯自然语言交互、注重“感觉”的特性和局限性，例如AI有时无法修复bug，需要反复尝试修改。

## Vibe Coding实践：iRelax项目

iRelax 是一款简洁高效的 macOS 桌面应用程序，旨在帮助用户在工作期间定时休息，保护视力健康，并缓解久坐带来的身体不适。

在 Vibe Coding 理念的指导下，本人完成了这款应用的开发。尽管此前对 macOS 应用开发毫无经验，甚至从未编写过 Swift 代码，但在 Cursor 智能编程助手的支持下，成功实现了定时休息提醒功能，整个开发过程颇具趣味性。

关于 Vibe Coding，个人认为其在原型开发阶段表现优异，能够快速验证想法并产出初步成果。然而，若应用于生产级项目，尤其是在开发者尚未深入掌握的领域，仍需谨慎评估其适用性。

主要功能：

- 定时休息提醒：根据设定的工作时间，自动提醒您休息
- 灵活的时间设置：可自定义工作时间和休息时间
- 休息提示：休息时自动弹出提示，防止忽略休息提醒


<img src="assets/img/202504/zhuanzhu.png" alt="专注" width="40%" style="height:auto;">
<img src="assets/img/202504/xiuxi.png" alt="休息" width="40%" style="height:auto;">

本人大概花费了4 个小时开发和处理错误。Vibe Coding在项目构建的前期，能快速的将主要功能实现，但在一些bug 修复上可能存在反反复复的提示和修改，如休息的倒计时不能精确展示，花费了不少时间，在此过程中不断切换sonnet 3.7和 gemini 2.5 验证LLM 的效果。

项目代码：[https://github.com/xushun007/vibe-coding-iRelax](https://github.com/xushun007/vibe-coding-iRelax)

## 行业“Vibe”检查：现状与实践

尽管Vibe Coding的概念相对较新，但它已经在软件开发领域激起了涟漪，并在特定场景下得到了应用。

应用场景：
- 个人项目与原型设计：Vibe Coding最常被提及的应用场景是个人爱好项目、快速原型验证和“一次性周末项目”。它允许开发者或爱好者快速将想法变为现实，而不必过多纠缠于底层细节。
- 初创公司与MVP：对于需要快速迭代和验证市场想法的初创公司而言，Vibe Coding展现出巨大吸引力。据报道，Y Combinator 2025年冬季孵化项目中，有25%的初创公司主要使用AI生成的代码，甚至有些公司95%的代码库由AI完成。
- 赋能非开发者：Vibe Coding显著降低了软件开发的门槛，使得设计师、产品经理、领域专家甚至完全没有编程背景的人也能创建满足特定需求的工具或应用。
- 大型企业探索：一些大型企业也在探索AI辅助编程带来的效率提升，例如摩根大通报告生产力提高20%，亚马逊称其30%的生产代码由AI生成。不过，这些数据可能混合了严格审查的AI辅助编程和纯粹的Vibe Coding。

## Vibe被扼杀？挑战与劣势评估
Vibe Coding在行业内引发了截然不同的反应：兴奋与期待，质疑与担忧，营销驱动异或开发者的未来。

Vibe Coding的光鲜外表之下，潜藏着一系列不容忽视的挑战和风险：
- 代码质量、可维护性与技术债：AI生成的代码往往缺乏良好的结构，可能杂乱无章（被戏称为“意大利面条怪物”），难以理解和维护。
- 安全漏洞与可靠性：在没有经过严格审查的情况下部署AI生成的代码，会带来严重的安全风险。AI可能不了解或忽视安全编码的最佳实践，从而引入漏洞。一项研究甚至发现AI生成的代码安全缺陷数量是人类编写代码的两倍。
- 理解赤字与技能退化：最大的风险之一是开发者部署了自己并不真正理解的代码，这可能导致无法预料的后果。
- AI自身局限性：当前的LLM并非完美。它们会产生“幻觉”（生成不正确或无意义的代码），知识库可能过时（使用旧版本的库或框架），并且受到上下文窗口大小的限制，难以处理大型复杂项目或在多个文件间保持一致性。

这些风险，特别是代码质量、安全性和可维护性方面的风险，很大程度上源于Vibe Coding的核心特征——接受不完全理解的代码。它其实与成熟的软件工程实践是存在矛盾的。

## 找到你自己的“Vibe”：结论与未来展望
开发者和技术爱好者们应以开放的心态去尝试和体验AI，但务必保持批判性思维，区分炒作与实际价值。归根结底，AI是增强人类能力的强大工具，但它并不能替代（尤其是在复杂和关键领域）经验丰富、思维缜密的软件工程师所带来的价值。

## 参考

- [https://x.com/karpathy/status/1886192184808149383](https://x.com/karpathy/status/1886192184808149383)
- [https://en.wikipedia.org/wiki/Vibe_coding](https://en.wikipedia.org/wiki/Vibe_coding)
- [https://github.com/xushun007/vibe-coding-iRelax](https://github.com/xushun007/vibe-coding-iRelax)
- [https://www.ibm.com/think/topics/vibe-coding](https://www.ibm.com/think/topics/vibe-coding)
- [https://www.nucamp.co/blog/vibe-coding-vibe-coding-101-how-ai-vibes-are-ushering-in-a-new-era-of-programming](https://www.nucamp.co/blog/vibe-coding-vibe-coding-101-how-ai-vibes-are-ushering-in-a-new-era-of-programming)
- [https://www.vibecodecareers.com/blog/vibe-coding-vs-traditional-coding](https://www.vibecodecareers.com/blog/vibe-coding-vs-traditional-coding)
- [https://blog.replit.com/what-is-vibe-coding](https://blog.replit.com/what-is-vibe-coding)
- [https://simonwillison.net/2025/Mar/19/vibe-coding/](https://simonwillison.net/2025/Mar/19/vibe-coding/)
- [https://news.ycombinator.com/item?id=43687767](https://news.ycombinator.com/item?id=43687767)

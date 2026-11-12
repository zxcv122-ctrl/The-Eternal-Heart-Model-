# 战略沙盘反推系统使用说明书 (Strategic Sandbox Engine Manual)

**版本**：v1.0 ｜ **配套代码文件**：`Strategic_Sandbox_Engine.py` (V7.6.3)

## 一、这是什么？
这是一套基于“一二三法则”的**目标导向逆向推演系统**。
通常的算法是“顺推”（看现状算结果），而这个系统是：**给定一个你渴望达成的目标（之卦），系统帮你倒推出现实中需要补齐的条件。**

它提供三条路径：
*   🅰️ **路径 A**：调认知/包装（W_cog）—— 提升名气、做好营销。
*   🅱️ **路径 B**：调硬实力（W_phys）—— 死磕技术、补足资源。
*   🇨 **路径 C**：换赛道/换底座（X）—— 当环境彻底没救时，换一个新环境重新开局。

> **重要定位**：这是帮你“拆解问题”的扳手，不是帮你“定吉凶”的罗盘。它提供策略选项，不替代你的现实决策。

## 二、如何运行？
1. 仅需 Python 3 环境，无任何第三方依赖。
2. 终端运行：`python Strategic_Sandbox_Engine.py` （会先自动跑8个测试用例，然后演示案例）
3. 代码内调用：直接导入 `strategy_sandbox` 或 `solve` 函数。

## 三、结果怎么看？（核心黑话指南）
*   **统一决策评分**：分数越低（越接近0），代表这条路综合成本越低，越优。
*   **稳定窗口**：系统推荐的安全区间。现实操作中，只要落在这个区间内都能达成目标，系统会自动取中点（留有余地最稳）。
*   **脆弱解/边界解**：极其精确的单点（手抖就失败），或卡在 0/1 边缘的极限状态，系统会标 `⚠️ 风险`。
*   **相变断点**：你的动爻数量发生了变化，意味着执行中会经历动荡，建议分阶段推进，不要一把梭哈。

## 四、给开发者的 API 接口说明
直接调用 `solve()`，会返回一个结构化的字典（JSON 格式）。
*   `recommend`：最终推荐路径（"A", "B", "C", "HOLD", 或 None）。
*   `A_windows` / `B_windows`：A/B 路径下所有可行的“稳定窗口”列表。
*   `C`：换底座的推荐 X 值及其综合评分。

## 五、免责声明
1. 本工具输出的所有路径、分数、窗口，均为模型内部的数学推演结果。
2. 不代表现实世界中必然成功，不构成任何财务、医疗或法律建议。
3. 涉及重大决策，请结合现实情况与专业人士意见，**风险自负**。

---
---

# Strategic Sandbox Engine - User Manual

**Version**: v1.0 | **Companion Code**: `Strategic_Sandbox_Engine.py` (V7.6.3)

## 1. What is this?
This is a **Goal-Oriented Reverse-Trace Engine** based on the "One-Two-Three" evolution model. 

While traditional algorithms are "Forward-Tracing" (calculating results from current states), this system does the opposite: **Given a desired target (Target Hexagram), it reverse-engineers the necessary conditions to manifest it.**

It provides three strategic paths:
*   🅰️ **Path A**: Adjust `W_cog` (Cognition/Packaging) — Improve branding, marketing, or public perception.
*   🅱️ **Path B**: Adjust `W_phys` (Hard Capability) — Enhance skills, resources, and actual strength.
*   🇨 **Path C**: Shift `X` (Base/Track) — When the current environment is unsalvageable, change the underlying track and restart.

> **Positioning**: This is a "wrench to dismantle problems," not a "compass to dictate destiny." It offers strategic options, not absolute reality.

---

## 2. How to Run?

### 2.1 Environment
Only requires Python 3. No third-party dependencies.

### 2.2 Run Self-Tests & Demo
Run in your terminal:
```bash
python Strategic_Sandbox_Engine.py

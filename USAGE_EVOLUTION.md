# 永心·一二三递归演化引擎 白皮书与使用说明
# Yongxin Recursive Evolution Engine - Whitepaper & Manual

**Version**: V2.1 | **Companion Code**: `recursive_evolution_engine_v21.py`

---

## 一、这是什么？ (What is this?)
This is a **Goal-Oriented Complex System Simulator** based on the ancient Eastern philosophy of "One-Two-Three" (Source, Differentiation, Emergence). 

这是一个基于“一二三法则”的**复杂系统演化沙盒**。它将“一为本源，二为阴阳分化，三为交合发生”的哲学思想，转化为可运行、可量化、可递归的 Python 算法。

⚠️ **核心定位 (Positioning)**: 本引擎不是预测未来的玄学工具，而是一个**用于战略推演、风险评估和复杂系统模拟的算法沙盒 (Algorithmic Sandbox)**。

---

## 二、它能带来什么价值？ (What Value Does It Bring?)

无论是在商业、科研还是个人决策中，我们常常面临“无法预知一个决定在未来会引发怎样连锁反应”的痛点。本引擎提供了一种**低成本、高效率的试错模型**。

### 🏢 1. 对企业与组织 (For Enterprises & Organizations)
*   **战略沙盒推演 (Strategic Sandbox)**: 将公司当前的资源作为“本源 (Origin)”，通过模拟不同的“阴阳分化（比如投入研发 vs 投入营销）”，推演未来 5 年的多条发展路径。
*   **创新孵化模拟 (Innovation Simulation)**: 模拟新业务或新子公司的裂变过程。系统会自动计算子代是否能“自然发生”出有效结果，帮助决策者看清哪些业务线会自然停止 (`natural_stop`)。
*   **资源防爆控制 (Risk Management)**: 内置的 `max_nodes`（节点预算）完美模拟了企业的资金链。当盲目扩张导致系统资源耗尽时，引擎会触发截断，预警风险。

### 🎓 2. 对学者与研究人员 (For Researchers & Academics)
*   **复杂系统动力学研究 (Complex Systems Dynamics)**: 本引擎实现了极其严密的“自底向上反馈机制 (Bottom-up Feedback)”和“阴阳守恒律 (Conservation Law)”，为研究生态演化、社会传播、甚至多智能体协同（Multi-Agent）提供了一个极简的代码基座。
*   **涌现现象可视化 (Emergence Visualization)**: 直观的树状图输出，帮助研究人员观察从“简单规则”到“复杂结构”的涌现全过程。

### 💡 3. 对个人与投资者 (For Individuals & Investors)
*   **人生路径推演 (Life Path Simulation)**: 将个人的精力、时间、初始资金作为输入，测算不同人生选择（如：创业 vs 打工、深耕 vs 跨界）在不同层级下会演化出怎样的结果，辅助找到最优的“反馈回路”。
*   **投资组合压力测试 (Portfolio Stress Testing)**: 测试不同资产配置在受到外部“缺口 (open_gap)”冲击时，系统的抗风险和自愈能力。

---

## 三、核心机制与哲学映射 (Core Mechanics & Philosophy)

*   **一 (Origin)**: 系统的初始本源、原始资金或核心资源。
*   **二 (Yin-Yang Split)**: 引擎严格遵循**阴阳守恒律 (Conservation Law)**。每一次分化，阴阳之和必须绝对等于本源，确保逻辑严谨。
*   **三 (Emergence)**: 阴阳交合生成新值，它将成为下一个层级的“新本源”。
*   **留白 (Open Gap)**: 引入随机扰动参数，保留系统未闭合的空间，模拟现实中的“未知变量”和“创新机会”。
*   **动态反馈 (Feedback)**: 子节点的演化结果会逆向传导给父节点，模拟“现实对战略的反哺”。

---

## 四、如何运行？ (How to Run)

仅需 Python 3，无需任何第三方依赖。
Only requires Python 3, no third-party dependencies.

```bash
python recursive_evolution_engine_v21.py

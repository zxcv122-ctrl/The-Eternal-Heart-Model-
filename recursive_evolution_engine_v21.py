# -*- coding: utf-8 -*-
"""
永心·一二三递归嵌套演化引擎 V2.1
YONGXIN ONE-TWO-THREE RECURSIVE EVOLUTION ENGINE

核心：本源、阴阳、交合、递归、反馈

V2.1 相对 V2.0 的主要优化：
1. 演化改为【逐层展开 + 自底向上反馈】的迭代实现，不再依赖 Python 递归，
   深度再大也不会触发 RecursionError
2. 节点预算按层公平分配（V2.0 深度优先，预算会被最左分支耗尽）
3. yin_ratio 成为真正的阴阳均值（V2.0 中阳恒大于阴），新增 split_variation
4. 守恒检验真实计数；用异常代替 assert（python -O 下 assert 会失效）
5. 反馈逐层向上传导（V2.0 只看直接子代的原始新生值）
6. origin 保持原始值不被覆盖，反馈后的状态放入 adjusted_origin
7. 根节点必定展开，不会 10% 概率一开始就停止
8. 配置自动校验；ANSI 颜色自动检测终端，可关闭
9. 打印、统计、导出全部为迭代实现，新增扁平导出 export_flat
10. 命令行参数，大树可导出到文件而不是刷屏
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


# ==================================================
# 一、颜色系统（不依赖第三方库）
# ==================================================

class Colors:

    GREEN = "\033[92m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def _auto_color() -> bool:
    """仅在真实终端且未设置 NO_COLOR 时启用颜色。"""
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


# ==================================================
# 二、演化参数
# ==================================================

@dataclass
class EvolutionConfig:

    # 最大递归深度
    max_depth: int = 5

    # 全局最大节点数量
    max_total_nodes: int = 10000

    # 每个节点生成的子节点数量
    min_children: int = 1
    max_children: int = 2

    # 阴所占本源的平均比例（阳 = 1 - 阴）
    yin_ratio: float = 0.5

    # 阴阳分化的随机波动幅度（比例在 yin_ratio ± split_variation 内）
    split_variation: float = 0.4

    # 阴阳交互强度
    interaction_strength: float = 0.7

    # 缺口保留比例
    open_gap: float = 0.2

    # 双向反馈强度
    feedback_strength: float = 0.3

    # 自然停止概率（根节点不会自然停止）
    stop_probability: float = 0.1

    # 守恒误差容许值
    conservation_tolerance: float = 1e-9

    # 随机种子（None 表示每次不同）
    random_seed: Optional[int] = 42

    def __post_init__(self):
        self.validate()

    def validate(self):

        def require(condition: bool, message: str):
            if not condition:
                raise ValueError(f"配置错误：{message}")

        require(0 <= self.max_depth <= 500, "max_depth 须在 0~500")
        require(self.max_total_nodes >= 1, "max_total_nodes 须 >= 1")
        require(self.min_children >= 1, "min_children 须 >= 1")
        require(
            self.max_children >= self.min_children,
            "max_children 须 >= min_children"
        )
        require(0 <= self.yin_ratio <= 1, "yin_ratio 须在 0~1")
        require(0 <= self.split_variation <= 1, "split_variation 须在 0~1")
        require(
            0 <= self.interaction_strength <= 1,
            "interaction_strength 须在 0~1"
        )
        require(0 <= self.open_gap <= 1, "open_gap 须在 0~1")
        require(
            0 <= self.feedback_strength <= 1,
            "feedback_strength 须在 0~1"
        )
        require(
            0 <= self.stop_probability <= 1,
            "stop_probability 须在 0~1"
        )
        require(
            self.conservation_tolerance > 0,
            "conservation_tolerance 须 > 0"
        )


# ==================================================
# 三、太极节点
# ==================================================

@dataclass
class TaijiNode:

    node_id: str

    label: str

    depth: int

    # 一：原始本源（演化完成后保持不变）
    origin: float

    parent_id: Optional[str] = None

    # 分化时的本源快照
    split_origin: Optional[float] = None

    # 二：阴阳分化
    yin: Optional[float] = None
    yang: Optional[float] = None

    # 三：交合生发（原始值）
    emergence: Optional[float] = None

    # 父子反馈量
    feedback: float = 0.0

    # 反馈后的本源（= split_origin + feedback；叶子等于 origin）
    adjusted_origin: Optional[float] = None

    # 反馈后的新生值（向上传导给父节点的值）
    effective_emergence: Optional[float] = None

    # 缺口
    open_gap: float = 0.0

    # 停止状态
    stopped: bool = False

    # 停止原因：max_depth / natural_stop / node_budget
    stop_reason: Optional[str] = None

    # 是否因预算限制而未能完整展开
    truncated: bool = False

    # 子系统
    children: List["TaijiNode"] = field(default_factory=list)


# ==================================================
# 四、核心演化引擎
# ==================================================

class OneTwoThreeEngine:

    def __init__(self, config: Optional[EvolutionConfig] = None):

        self.config = config or EvolutionConfig()
        self.config.validate()

        self.rng = random.Random(self.config.random_seed)

        # 按创建顺序（即逐层顺序）保存所有节点
        self.nodes: List[TaijiNode] = []

        self.conservation_checks = 0
        self.conservation_failures = 0

    # ------------------------------------------------
    # 【一】本源初始化
    # ------------------------------------------------

    def initialize(self, origin: float = 1.0, label: str = "宇宙") -> TaijiNode:

        self.nodes.clear()

        self.conservation_checks = 0
        self.conservation_failures = 0

        return TaijiNode(
            node_id="ROOT",
            label=label,
            depth=0,
            origin=origin,
            open_gap=self.config.open_gap
        )

    # ------------------------------------------------
    # 【二】阴阳分化：严格守恒
    # ------------------------------------------------

    def split(self, origin: float):

        cfg = self.config

        yin_fraction = _clamp(
            cfg.yin_ratio
            + self.rng.uniform(-cfg.split_variation, cfg.split_variation)
        )

        yin = origin * yin_fraction

        # 强制守恒
        yang = origin - yin

        # 守恒验证（真实计数，失败抛异常）
        self.conservation_checks += 1

        if not math.isclose(
            yin + yang,
            origin,
            rel_tol=cfg.conservation_tolerance,
            abs_tol=cfg.conservation_tolerance
        ):
            self.conservation_failures += 1
            raise ArithmeticError("阴阳守恒验证失败")

        return yin, yang

    # ------------------------------------------------
    # 【三】阴阳交合：产生新实例
    # ------------------------------------------------

    def merge(self, yin: float, yang: float, gap: float) -> float:

        strength = self.config.interaction_strength

        interaction = yin * (1 - strength) + yang * strength

        # 缺口提供开放的演化空间
        openness = gap * self.rng.uniform(0, 1)

        return interaction * (1 + openness)

    # ------------------------------------------------
    # 自然停止判断：返回停止原因，不停止返回 None
    # ------------------------------------------------

    def should_stop(self, node: TaijiNode) -> Optional[str]:

        if node.depth >= self.config.max_depth:
            return "max_depth"

        # 根节点必须展开，否则整个演化没有意义
        if node.depth > 0 and self.rng.random() < self.config.stop_probability:
            return "natural_stop"

        return None

    # ------------------------------------------------
    # 语义标签生成
    # ------------------------------------------------

    @staticmethod
    def make_label(parent: TaijiNode, index: int, label_map: Dict[str, List[str]]) -> str:

        labels = label_map.get(parent.label)

        if labels and index - 1 < len(labels):
            return labels[index - 1]

        return f"{parent.label}-子系统{index}"

    # ------------------------------------------------
    # 逐层展开（迭代，预算按层公平分配）
    # ------------------------------------------------

    def _expand(self, root: TaijiNode, label_map: Dict[str, List[str]]):

        cfg = self.config

        self.nodes.append(root)

        queue = deque([root])

        while queue:

            node = queue.popleft()

            # 自然停止 / 深度停止
            reason = self.should_stop(node)

            if reason:
                node.stopped = True
                node.stop_reason = reason
                node.emergence = node.origin
                continue

            # 一：本源
            node.split_origin = node.origin

            # 二：阴阳分化
            node.yin, node.yang = self.split(node.origin)

            # 三：交合生发
            node.emergence = self.merge(node.yin, node.yang, node.open_gap)

            # 新生实例
            child_count = self.rng.randint(cfg.min_children, cfg.max_children)

            for i in range(child_count):

                if len(self.nodes) >= cfg.max_total_nodes:
                    node.truncated = True
                    break

                child = TaijiNode(
                    node_id=f"{node.node_id}.{i + 1}",
                    label=self.make_label(node, i + 1, label_map),
                    depth=node.depth + 1,
                    origin=node.emergence,      # 新生实例成为新的【一】
                    parent_id=node.node_id,
                    open_gap=node.open_gap
                )

                node.children.append(child)
                self.nodes.append(child)
                queue.append(child)

            # 一个子节点都没能生成：视为被预算截停的叶子
            if node.truncated and not node.children:
                node.stopped = True
                node.stop_reason = "node_budget"

    # ------------------------------------------------
    # 双向反馈（自底向上，逐层传导）
    # ------------------------------------------------

    def _feedback(self):

        strength = self.config.feedback_strength

        # 逐层创建顺序的逆序：子节点一定先于父节点处理
        for node in reversed(self.nodes):

            node.adjusted_origin = node.origin
            node.effective_emergence = node.emergence

            if not node.children:
                continue

            child_mean = (
                sum(c.effective_emergence for c in node.children)
                / len(node.children)
            )

            node.feedback = (child_mean - node.emergence) * strength
            node.effective_emergence = node.emergence + node.feedback
            node.adjusted_origin = node.split_origin + node.feedback

    # ------------------------------------------------
    # 启动演化
    # ------------------------------------------------

    def run(
        self,
        origin: float = 1.0,
        label: str = "宇宙",
        label_map: Optional[Dict[str, List[str]]] = None
    ) -> TaijiNode:

        root = self.initialize(origin=origin, label=label)

        self._expand(root, label_map or {})
        self._feedback()

        return root

    # ==================================================
    # 五、彩色演化树（迭代）
    # ==================================================

    def render_tree(self, root: TaijiNode, use_color: bool = True) -> List[str]:

        def paint(text: str, color: str) -> str:
            return f"{color}{text}{Colors.RESET}" if use_color else text

        lines: List[str] = []
        stack = [(root, "")]

        while stack:

            node, prefix = stack.pop()

            if node.stopped:
                color = Colors.GRAY
            elif node.feedback > 0:
                color = Colors.YELLOW
            elif node.feedback < 0:
                color = Colors.PURPLE
            else:
                color = Colors.CYAN

            lines.append(paint(
                f"{prefix}[{node.node_id}] {node.label} "
                f"层级={node.depth} "
                f"原始本源={node.origin:.5f} "
                f"新生={node.emergence:.5f}",
                color
            ))

            if node.yin is not None:
                lines.append(
                    f"{prefix}  "
                    + paint(f"阴={node.yin:.5f}", Colors.BLUE)
                    + " | "
                    + paint(f"阳={node.yang:.5f}", Colors.GREEN)
                )

            if node.feedback != 0:
                lines.append(
                    f"{prefix}  反馈={node.feedback:+.5f} "
                    f"修正后本源={node.adjusted_origin:.5f}"
                )

            if node.stop_reason:
                lines.append(paint(f"{prefix}  状态={node.stop_reason}", Colors.GRAY))
            elif node.truncated:
                lines.append(paint(f"{prefix}  状态=部分截断（节点预算）", Colors.GRAY))

            # 逆序入栈，保证输出顺序与子节点顺序一致
            for child in reversed(node.children):
                stack.append((child, prefix + "    "))

        return lines

    def print_tree(self, root: TaijiNode, use_color: Optional[bool] = None):

        if use_color is None:
            use_color = _auto_color()

        print("\n".join(self.render_tree(root, use_color)))

    # ==================================================
    # 六、统计系统
    # ==================================================

    def statistics(self, root: TaijiNode) -> dict:

        levels: Counter = Counter()
        stop_reasons: Counter = Counter()

        stopped = truncated = leaves = 0
        total_yin = total_yang = 0.0

        for node in self.nodes:

            levels[node.depth] += 1

            if node.stopped:
                stopped += 1
                stop_reasons[node.stop_reason] += 1

            if node.truncated:
                truncated += 1

            if not node.children:
                leaves += 1

            if node.yin is not None:
                total_yin += node.yin
                total_yang += node.yang

        return {

            "total_nodes": len(self.nodes),

            "max_total_nodes": self.config.max_total_nodes,

            "max_depth_reached": max(levels) if levels else 0,

            "nodes_per_level": dict(sorted(levels.items())),

            "leaf_nodes": leaves,

            "stopped_nodes": stopped,

            "stop_reasons": dict(stop_reasons),

            "truncated_nodes": truncated,

            "budget_exhausted": truncated > 0,

            "total_yin": total_yin,

            "total_yang": total_yang,

            "conservation_checks": self.conservation_checks,

            "conservation_failures": self.conservation_failures,

            "root_origin": root.origin,

            "root_adjusted_origin": root.adjusted_origin,

            "root_feedback": root.feedback
        }

    # ==================================================
    # 七、完整数据导出
    # ==================================================

    @staticmethod
    def _node_dict(node: TaijiNode) -> dict:

        return {
            "id": node.node_id,
            "parent_id": node.parent_id,
            "label": node.label,
            "depth": node.depth,
            "origin": node.origin,
            "split_origin": node.split_origin,
            "yin": node.yin,
            "yang": node.yang,
            "emergence": node.emergence,
            "feedback": node.feedback,
            "adjusted_origin": node.adjusted_origin,
            "effective_emergence": node.effective_emergence,
            "open_gap": node.open_gap,
            "stopped": node.stopped,
            "stop_reason": node.stop_reason,
            "truncated": node.truncated
        }

    def export_flat(self) -> List[dict]:
        """扁平导出（含 parent_id），任意深度都可安全序列化。"""
        return [self._node_dict(n) for n in self.nodes]

    def export_tree(self, root: TaijiNode) -> dict:
        """嵌套导出。深度超过约 300 时 json 序列化可能触发递归上限，
        此时请改用 export_flat。"""
        mapping = {id(n): self._node_dict(n) for n in self.nodes}

        for n in self.nodes:
            mapping[id(n)]["children"] = [mapping[id(c)] for c in n.children]

        return mapping[id(root)]


# ==================================================
# 八、运行入口
# ==================================================

DEFAULT_LABEL_MAP = {
    "宇宙": ["物质", "能量"],
    "物质": ["天体", "生命"],
    "能量": ["运动", "场"],
    "天体": ["恒星", "行星"],
    "生命": ["植物", "动物"]
}


def main(argv=None):

    parser = argparse.ArgumentParser(description="永心·一二三递归嵌套演化引擎 V2.1")
    parser.add_argument("--depth", type=int, default=5, help="最大深度")
    parser.add_argument("--max-nodes", type=int, default=10000, help="节点上限")
    parser.add_argument("--min-children", type=int, default=1)
    parser.add_argument("--max-children", type=int, default=2)
    parser.add_argument("--stop-prob", type=float, default=0.1, help="自然停止概率")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    parser.add_argument("--no-tree", action="store_true", help="不打印演化树（大树推荐）")
    parser.add_argument("--export", metavar="PATH", help="将配置、统计与全部节点导出为 JSON 文件")
    args = parser.parse_args(argv)

    config = EvolutionConfig(
        max_depth=args.depth,
        max_total_nodes=args.max_nodes,
        min_children=args.min_children,
        max_children=args.max_children,
        stop_probability=args.stop_prob,
        random_seed=args.seed
    )

    engine = OneTwoThreeEngine(config)

    root = engine.run(origin=1.0, label="宇宙", label_map=DEFAULT_LABEL_MAP)

    if not args.no_tree:
        print("\n========== 一二三递归演化树 ==========\n")
        engine.print_tree(root, use_color=False if args.no_color else None)

    stats = engine.statistics(root)

    print("\n========== 演化统计 ==========\n")
    print(json.dumps(stats, ensure_ascii=False, indent=4))

    if args.export:
        payload = {
            "config": asdict(config),
            "statistics": stats,
            "nodes": engine.export_flat()
        }
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n完整演化数据已导出：{args.export}")

    print("\n========== 系统运行完成 ==========\n")
    print(
        f"阴阳守恒检查：{stats['conservation_checks']} 次，"
        f"失败 {stats['conservation_failures']} 次"
    )
    print("节点预算：" + ("已耗尽（部分分支被截断）" if stats["budget_exhausted"] else "未耗尽"))


if __name__ == "__main__":
    main()


# -*- coding: utf-8 -*-
"""
五行自检（一二三演化模型 · 打分制 V1.4）
====================================================

【功能】
一、强弱：识别五行相对偏强、偏弱的方面
二、相生链：分析薄弱环节的生扶来源
三、演化推演：按照设定的生克规则进行30轮数学模拟
四、整体总结：综合分析结构关系和行动方向

【五行编号】
木=0 火=1 土=2 金=3 水=4

【核心规则】
相生：木生火、火生土、土生金、金生水、水生木
相克：木克土、土克水、水克火、火克金、金克木

【强弱判断】
相对均值偏离达到±1分，作为强弱参考阈值。
当最大分差达到2分时，增加极端分值辅助判断。

【演化参数】
模拟轮数：30
相生系数：0.05
相克系数：0.002
趋势阈值：±1.5个百分点

以上参数属于模型实验设定，并非经过实证验证的自然规律。

【重要说明】
本工具用于梳理主观评分和观察规则下的数学演化情景。
模拟结果不代表现实中的五行能量变化，也不构成现实预测。
====================================================
"""

import math


# ====================================================
# 一、基础配置
# ====================================================

NAMES = ["木", "火", "土", "金", "水"]

# 谁生谁
SHENG = {
    0: 1,  # 木生火
    1: 2,  # 火生土
    2: 3,  # 土生金
    3: 4,  # 金生水
    4: 0,  # 水生木
}

# 谁克谁
KE = {
    0: 2,  # 木克土
    2: 4,  # 土克水
    4: 1,  # 水克火
    1: 3,  # 火克金
    3: 0,  # 金克木
}

# 谁生我
SHENG_FROM = {
    v: k for k, v in SHENG.items()
}

# 谁克我
KE_FROM = {
    v: k for k, v in KE.items()
}

# 默认测试分数
DEFAULT_SCORES = [2, 1, 4, 5, 1]

# 强弱判断参数
STRENGTH_THRESHOLD = 1.0
SPREAD_THRESHOLD = 2.0
EXTREME_HIGH = 4.5
EXTREME_LOW = 1.5

# 演化模拟参数
SIMULATION_ROUNDS = 30
SHENG_RATE = 0.05
KE_RATE = 0.002

# 趋势判断阈值
TREND_THRESHOLD = 1.5


# ====================================================
# 二、评分问题
# ====================================================

QUESTIONS = [
    "木｜启动与成长：想法多不多？有没有在开始新东西、持续往前长？",
    "火｜热度与表达：有多少人看到、关注、有反应？你自己的热情够不够？",
    "土｜根基与耐心：底子稳不稳？有没有积累、资源和不急躁的定力？",
    "金｜规则与打磨：有没有取舍、整理，把质量和细节做好的执行力？",
    "水｜储备与流动：学习、休息、现金和时间的余量够不够？信息通不通？",
]


# ====================================================
# 三、建议文字
# ====================================================

WEAK_TIP = [
    "木偏弱：新的尝试和成长点不足。可以先做一个小的新动作，不求大。",
    "火偏弱：曝光和热情不足。可以多表达、多让别人看到你在做的事。",
    "土偏弱：根基不稳。先别扩张，补积累、补资源、放慢节奏。",
    "金偏弱：缺整理和打磨。可以做减法，定标准，把现有的东西做精。",
    "水偏弱：余量不足。留出休息、学习和资金的缓冲，别把自己耗干。",
]

STRONG_TIP = [
    "木偏强：想法和冲劲多，注意别铺得太开，容易压到土（根基）。",
    "火偏强：热度高，注意别烧过头，容易压住金（打磨）。",
    "土偏强：很稳，但可能过于保守，容易压住水（流动与学习）。",
    "金偏强：标准很高、很严，注意别压住木（新的萌芽）。",
    "水偏强：思考与储备多，注意别压住火（行动与表达）。",
]


# ====================================================
# 四、基础工具
# ====================================================

def clamp_score(s):
    """限制分数在1~5，并拒绝非有限数值。"""

    try:
        value = float(s)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("分数必须是有效数字。")

    if not math.isfinite(value):
        raise ValueError("分数不能是 NaN 或无穷大。")

    return max(1.0, min(5.0, value))


def fmt(s):
    """去掉无用的小数位。"""

    value = float(s)

    if value.is_integer():
        return int(value)

    return round(value, 2)


# ====================================================
# 五、输入解析
# ====================================================

def parse_input(raw_text):
    """
    支持：
    2 1 4 5 1
    2,1,4,5,1
    2，1，4，5，1
    2、1、4、5、1
    2|1|4|5|1
    21451

    空输入使用默认分数。
    超出1~5的分数自动修正。
    """

    text = raw_text.strip()

    if not text:
        return list(DEFAULT_SCORES)

    for ch in [",", "，", "、", "|"]:
        text = text.replace(ch, " ")

    parts = text.split()

    if len(parts) == 5:
        try:
            raw_scores = [float(x) for x in parts]
        except (ValueError, OverflowError):
            raise ValueError("请确保输入的都是有效数字。")

    else:
        compact = text.replace(" ", "")

        if len(compact) != 5 or not compact.isdigit():
            raise ValueError(
                "请输入5个分数，例如：2 1 4 5 1，或直接输入21451。"
            )

        raw_scores = [float(ch) for ch in compact]

    scores = []
    changed = []

    for i, raw in enumerate(raw_scores):

        value = clamp_score(raw)
        scores.append(value)

        if raw != value:
            changed.append(
                f"{NAMES[i]}：{fmt(raw)}→{fmt(value)}"
            )

    if changed:
        print(
            "提示：部分分数超出1~5范围，已自动修正："
            + "；".join(changed)
        )

    return scores


# ====================================================
# 六、强弱判断
# ====================================================

def analyze_strength(scores):
    """
    以五项平均分为基准判断相对强弱。

    相对均值偏离：
    >= +1：偏强
    <= -1：偏弱

    极端分差辅助判断：
    当最大分差>=2时：
    >=4.5：辅助判强
    <=1.5：辅助判弱
    """

    mean = sum(scores) / 5
    spread = max(scores) - min(scores)

    relative = [
        score - mean
        for score in scores
    ]

    strong = []
    weak = []

    for i in range(5):

        is_strong = (
            relative[i] >= STRENGTH_THRESHOLD
            or (
                spread >= SPREAD_THRESHOLD
                and scores[i] >= EXTREME_HIGH
            )
        )

        is_weak = (
            relative[i] <= -STRENGTH_THRESHOLD
            or (
                spread >= SPREAD_THRESHOLD
                and scores[i] <= EXTREME_LOW
            )
        )

        if is_strong:
            strong.append(i)

        if is_weak:
            weak.append(i)

    return mean, spread, strong, weak


# ====================================================
# 七、相生相克演化模拟
# ====================================================

def simulate_short_term(
    scores,
    rounds=SIMULATION_ROUNDS,
    sheng=SHENG_RATE,
    ke=KE_RATE
):
    """
    规则驱动的数学情景模拟。

    初始值归一化为100。

    相生：
    每轮按当前各行的5%转移给其所生之行。

    相克：
    每轮按克制双方当前数值的乘积乘以0.002计算转移量。
    转移量不超过被克一方当前数值的50%。

    所有转移均采用固定顺序：
    先执行相生，再执行相克。

    每轮进行总量归一化，减少浮点误差。

    注意：
    这是模型内部的数学演算，不是现实预测。
    """

    if len(scores) != 5:
        raise ValueError("模拟需要5个分数。")

    if rounds < 0:
        raise ValueError("模拟轮数不能为负数。")

    if sheng < 0 or ke < 0:
        raise ValueError("演化系数不能为负数。")

    if not all(math.isfinite(float(x)) for x in scores):
        raise ValueError("模拟数据包含无效数值。")

    total = sum(scores)

    if total <= 0:
        raise ValueError("分数总和必须大于0。")

    # 初始归一化
    e = [
        value * 100.0 / total
        for value in scores
    ]

    start = e[:]

    for _ in range(rounds):

        new = e[:]

        # ----------------------------
        # 第一步：相生转移
        # ----------------------------

        for i in range(5):

            target = SHENG[i]

            transfer = sheng * e[i]

            new[i] -= transfer
            new[target] += transfer

        # ----------------------------
        # 第二步：相克转移
        # ----------------------------

        for i in range(5):

            target = KE[i]

            transfer = ke * e[i] * e[target]

            # 防止单次转移过大
            transfer = min(
                transfer,
                new[target] * 0.5
            )

            transfer = max(0.0, transfer)

            new[target] -= transfer
            new[i] += transfer

        # ----------------------------
        # 第三步：总量归一化
        # ----------------------------

        total_e = sum(new)

        if total_e <= 0 or not math.isfinite(total_e):
            raise ArithmeticError("模拟过程中出现异常数值。")

        e = [
            max(0.0, x * 100.0 / total_e)
            for x in new
        ]

    return start, e


# ====================================================
# 八、整体总结
# ====================================================

def get_summary_text(
    scores,
    weak,
    strong,
    up_names,
    down_names
):

    out = [
        "\n【四、整体总结】"
    ]

    # ----------------------------
    # 当前强弱结构
    # ----------------------------

    if weak and strong:

        weak_n = "、".join(
            NAMES[i] for i in weak
        )

        strong_n = "、".join(
            NAMES[i] for i in strong
        )

        out.append(
            f"目前相对突出的是{strong_n}，"
            f"相对偏弱的是{weak_n}。"
        )

        for s in strong:

            for w in weak:

                if KE[s] == w:

                    out.append(
                        f"关系提示：「{NAMES[s]}」偏强，"
                        f"按照相克关系，可能对「{NAMES[w]}」"
                        f"形成结构性压力。"
                    )

    elif strong:

        out.append(
            "目前"
            + "、".join(NAMES[i] for i in strong)
            + "相对突出，但单项突出不代表整体均衡。"
        )

    elif weak:

        out.append(
            "当前主要薄弱环节是"
            + "、".join(NAMES[i] for i in weak)
            + "，可以优先关注这些方面。"
        )

    else:

        out.append(
            "目前五项没有明显的相对强弱，"
            "整体评分结构相对均衡。"
        )

    # ----------------------------
    # 模拟变化方向
    # ----------------------------

    if up_names and down_names:

        out.append(
            "按照当前设定的演化规则："
            + "、".join(up_names)
            + "在模拟中上升，"
            + "、".join(down_names)
            + "在模拟中下降。"
        )

    elif up_names:

        out.append(
            "按照当前设定的演化规则："
            + "、".join(up_names)
            + "在模拟中呈上升趋势。"
        )

    elif down_names:

        out.append(
            "按照当前设定的演化规则："
            + "、".join(down_names)
            + "在模拟中呈下降趋势。"
        )

    else:

        out.append(
            "按照当前设定的演化规则，"
            "各项变化均未达到趋势判断阈值。"
        )

    # ----------------------------
    # 行动方向
    # ----------------------------

    if weak:

        lowest = min(
            weak,
            key=lambda i: scores[i]
        )

        out.append(
            f"行动方向：优先关注最弱的「{NAMES[lowest]}」，"
            "从一个可执行的小动作开始，"
            "逐步改善当前薄弱环节。"
        )

    else:

        out.append(
            "行动方向：保持现有结构，"
            "继续观察各方面的发展，"
            "不必为了追求变化而刻意改变。"
        )

    return "\n".join(out)


# ====================================================
# 九、核心诊断
# ====================================================

def diagnose(scores):

    if len(scores) != 5:
        raise ValueError(
            "需要5个分数，顺序为：木、火、土、金、水。"
        )

    scores = [
        clamp_score(s)
        for s in scores
    ]

    shown_scores = [
        fmt(s)
        for s in scores
    ]

    mean, spread, strong, weak = analyze_strength(scores)

    lines = []

    # ----------------------------
    # 基础评分
    # ----------------------------

    lines.append(
        "【你的打分】 "
        + "  ".join(
            f"{NAMES[i]}{shown_scores[i]}"
            for i in range(5)
        )
    )

    lines.append(
        f"平均分：{mean:.2f}｜最大分差：{spread:.2f}"
    )

    # ----------------------------
    # 一、强弱分析
    # ----------------------------

    lines.append("\n【一、强弱】")

    if not strong and not weak:

        lines.append(
            "五行比较均衡，没有明显偏强或偏弱的一行。"
        )

    for i in weak:

        lines.append(
            "· " + WEAK_TIP[i]
        )

    for i in strong:

        lines.append(
            "· " + STRONG_TIP[i]
        )

    # ----------------------------
    # 二、相生链分析
    # ----------------------------

    lines.append(
        "\n【二、相生链：从哪里补】"
    )

    if not weak:

        lines.append(
            "没有明显偏弱的一行，暂时不需要重点补弱。"
        )

    for i in weak:

        p = SHENG_FROM[i]
        k = KE_FROM[i]

        # 统一采用强弱分析结果判断来源
        if p not in weak:

            lines.append(
                f"· {NAMES[i]}偏弱：生它的"
                f"「{NAMES[p]}」目前不属于偏弱项"
                f"（评分{shown_scores[p]}），"
                f"可优先观察这一生扶来源。"
            )

        else:

            lines.append(
                f"· {NAMES[i]}偏弱：生它的"
                f"「{NAMES[p]}」也偏弱"
                f"（评分{shown_scores[p]}），"
                f"建议先关注源头「{NAMES[p]}」。"
            )

        if k in strong:

            lines.append(
                f"  另外，克制「{NAMES[i]}」的"
                f"「{NAMES[k]}」相对偏强，"
                f"需要留意两者之间的结构关系。"
            )

    # ----------------------------
    # 三、演化推演
    # ----------------------------

    start, end = simulate_short_term(scores)

    changes = [
        end[i] - start[i]
        for i in range(5)
    ]

    up = [
        i for i in range(5)
        if changes[i] >= TREND_THRESHOLD
    ]

    down = [
        i for i in range(5)
        if changes[i] <= -TREND_THRESHOLD
    ]

    lines.append(
        "\n【三、演化推演"
        f"（规则模拟{SIMULATION_ROUNDS}轮）】"
    )

    lines.append(
        "以下数值为模型内部归一化比例，不代表现实能量。"
    )

    if not up and not down:

        lines.append(
            "变化不大，各项变化均未达到设定的趋势阈值。"
        )

    for i in up:

        lines.append(
            f"· {NAMES[i]}在模拟中上升"
            f"（{start[i]:.2f}% → {end[i]:.2f}%）"
        )

    for i in down:

        lines.append(
            f"· {NAMES[i]}在模拟中下降"
            f"（{start[i]:.2f}% → {end[i]:.2f}%）"
        )

    # ----------------------------
    # 四、整体总结
    # ----------------------------

    lines.append(
        get_summary_text(
            scores,
            weak,
            strong,
            [NAMES[i] for i in up],
            [NAMES[i] for i in down]
        )
    )

    # ----------------------------
    # 免责声明
    # ----------------------------

    lines.append(
        "\n【使用说明】"
        "\n本工具根据用户主观评分和预设五行生克规则进行结构分析。"
        "\n模拟结果仅用于观察模型内部的数学变化，"
        "不代表现实发展趋势，也不构成科学预测。"
        "\n强弱阈值、趋势阈值及演化参数均为经验性实验设定，"
        "尚未经实证验证。"
        "\n评分不同，分析结果也会相应变化。"
    )

    return "\n".join(lines)


# ====================================================
# 十、程序入口
# ====================================================

def main():

    print("=" * 52)
    print("五行自检（一二三演化模型 · 打分制 V1.4）")
    print("=" * 52)

    print(
        "\n请给下面五个方面分别打1~5分："
        "\n1=很弱，2=较弱，3=一般，4=较强，5=很强。\n"
    )

    for q in QUESTIONS:

        print("  " + q)

    print(
        "\n评分顺序：木、火、土、金、水"
        "\n输入示例：2 1 4 5 1"
        "\n也可以直接输入：21451"
        "\n直接回车：使用默认示例分数。"
    )

    while True:

        try:

            raw = input(
                "\n请输入五项分数："
            ).strip()

            scores = parse_input(raw)

            break

        except EOFError:

            scores = list(DEFAULT_SCORES)
            break

        except ValueError as err:

            print(
                f"\n输入有误：{err}"
            )

    print("\n" + "=" * 52)
    print(diagnose(scores))
    print("=" * 52)


# ====================================================
# 十一、启动
# ====================================================

if __name__ == "__main__":

    main()

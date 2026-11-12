
# -*- coding: utf-8 -*-
"""
永心模型 V7.6.3
战略沙盘反推系统（全路径修复版）
============================================================

基于 V7.6.2 保守修复迭代。

【V7.6.3 修复日志】

1. A/B 扫描网格修复
   - 不再使用 round(1 / step) 改变用户步长。
   - 采用用户指定步长扫描，并确保终点 1.0 被覆盖。
   - 支持 0.3、0.07 等不能整除 1 的步长。
   - 窗口宽度使用真实参数坐标计算。

2. C 路径完整搜索修复
   - 移除提前停止条件。
   - 扫描范围内完整搜索。
   - 按本卦去重。
   - 全部候选完成后再进行综合排序。

3. A/B/C 统一推荐
   - 三条路径全部进入推荐比较。
   - 新增 decision_cost 统一启发式决策评分。
   - 原 cost 字段保留，兼容旧版本。
   - 统一评分不代表现实成本已经得到实证标定。

4. 数值安全修复
   - 检查 NaN、Infinity。
   - 检查 X、step、x_step、x_scan_range。
   - 检查 W_phys、W_cog 的合法范围。
   - 防止非法参数进入计算。

5. 脆弱解识别修复
   - 区分扫描网格单点命中与真正的数学孤立解。
   - fragile 表示当前扫描分辨率下的单点命中。
   - 不再把扫描结果直接解释为连续数学意义上的孤立解。

6. 输出增强
   - 输出 A/B 全部可行窗口。
   - 输出每条路径的统一决策评分。
   - 输出最优路径及推荐依据。
   - 保留原有主要字段。

【模型定位】
结构化自省与策略分析工具，不是预测模型。

内部算法一致性不等于现实预测能力。
外部预测力仍需独立样本、盲测及随机基线验证。

核心提醒：
当「拆问题的扳手」用，
不要当「定答案的罗盘」用。
============================================================
"""

import math

PI = math.pi

# ============================================================
# 一、可配置常量
# ============================================================

KW_NUM_RAW = (
    "1,43,14,34,9,5,26,11,"
    "10,58,38,54,61,60,41,19,"
    "13,49,30,55,37,63,22,36,"
    "25,17,21,51,42,3,27,24,"
    "44,28,50,32,57,48,18,46,"
    "6,47,64,40,59,29,4,7,"
    "33,31,56,62,53,39,52,15,"
    "12,45,35,16,20,8,23,2"
)

_flat = KW_NUM_RAW.split(",")

KW_NUM = [
    list(map(int, _flat[i * 8:(i + 1) * 8]))
    for i in range(8)
]

# 原有 A/B 成本惩罚
CROSS_PENALTY = 0.3
FRAGILE_PENALTY = 0.2
BOUNDARY_PENALTY = 0.15

# 统一决策评分权重
# 三项权重合计为 1.0
DECISION_WEIGHT_DISTANCE = 0.65
DECISION_WEIGHT_STRUCTURE = 0.20
DECISION_WEIGHT_RISK = 0.15

# C 路径风险未知时使用中性风险值
C_UNKNOWN_RISK = 0.5

# 防止扫描数量异常膨胀
MAX_SCAN_POINTS = 2_000_000


# ============================================================
# 二、八卦及六十四卦映射
# ============================================================

TRI = {
    "111": "乾",
    "110": "兑",
    "101": "离",
    "100": "震",
    "011": "巽",
    "010": "坎",
    "001": "艮",
    "000": "坤"
}

ORDER = [
    "乾", "兑", "离", "震",
    "巽", "坎", "艮", "坤"
]

GUA_64_NAME = [
    "", "乾", "坤", "屯", "蒙", "需", "讼", "师",
    "比", "小畜", "履", "泰", "否", "同人", "大有",
    "谦", "豫", "随", "蛊", "临", "观", "噬嗑",
    "贲", "剥", "复", "无妄", "大畜", "颐", "大过",
    "坎", "离", "咸", "恒", "遁", "大壮", "晋",
    "明夷", "家人", "睽", "蹇", "解", "损", "益",
    "夬", "姤", "萃", "升", "困", "井", "革",
    "鼎", "震", "艮", "渐", "归妹", "丰", "旅",
    "巽", "兑", "涣", "节", "中孚", "小过",
    "既济", "未济"
]

GUA_KEYWORD = {
    "乾": "健行不息",
    "坤": "厚德载物",
    "屯": "初生艰难",
    "蒙": "启蒙待教",
    "需": "等待时机",
    "讼": "争讼分歧",
    "师": "聚众用兵",
    "比": "亲附合作",
    "小畜": "小蓄待发",
    "履": "履险如夷",
    "泰": "通达和合",
    "否": "闭塞不通",
    "同人": "同心协力",
    "大有": "丰盛拥有",
    "谦": "谦卑受益",
    "豫": "预备安乐",
    "随": "顺势而为",
    "蛊": "整治腐败",
    "临": "居高临下",
    "观": "观察审视",
    "噬嗑": "破除障碍",
    "贲": "文饰美化",
    "剥": "剥落衰退",
    "复": "回归重启",
    "无妄": "真实无妄",
    "大畜": "大蓄其德",
    "颐": "颐养身心",
    "大过": "过度承压",
    "坎": "险陷重重",
    "离": "光明依附",
    "咸": "感应相通",
    "恒": "恒久不变",
    "遁": "退避保全",
    "大壮": "声势壮大",
    "晋": "上升显达",
    "明夷": "韬光养晦",
    "家人": "家内有序",
    "睽": "背离分歧",
    "蹇": "艰难受阻",
    "解": "解除困境",
    "损": "减损修德",
    "益": "增益助成",
    "夬": "决断清除",
    "姤": "不期而遇",
    "萃": "聚集汇合",
    "升": "逐步上升",
    "困": "困顿受困",
    "井": "滋养不竭",
    "革": "变革更新",
    "鼎": "鼎新立制",
    "震": "震动惊醒",
    "艮": "止而定静",
    "渐": "循序渐进",
    "归妹": "名分未定",
    "丰": "丰盛圆满",
    "旅": "漂泊行旅",
    "巽": "顺入渗透",
    "兑": "喜悦沟通",
    "涣": "涣散化解",
    "节": "节制约束",
    "中孚": "诚信感通",
    "小过": "小有过越",
    "既济": "事已成局",
    "未济": "事未成局"
}


# ============================================================
# 三、完整性检查与预计算
# ============================================================

assert sorted(v for row in KW_NUM for v in row) == list(range(1, 65)), \
    "KW_NUM 必须恰好包含 1~64 且不重复"

assert len(GUA_64_NAME) == 65, \
    "GUA_64_NAME 长度必须为 65"

assert len(set(GUA_64_NAME[1:])) == 64, \
    "GUA_64_NAME 必须包含 64 个不重复卦名"


def _num_to_name_slow(num):
    lower = TRI[f"{num & 0b111:03b}"]
    upper = TRI[f"{(num >> 3) & 0b111:03b}"]

    index = (
        KW_NUM[ORDER.index(lower)]
        [ORDER.index(upper)]
    )

    return GUA_64_NAME[index]


NAME_BY_NUM = [
    _num_to_name_slow(n)
    for n in range(64)
]

NUM_BY_NAME = {
    name: n
    for n, name in enumerate(NAME_BY_NUM)
}

assert len(NUM_BY_NAME) == 64, \
    "卦序表非双射，请检查 KW_NUM"


def num_to_name(num):
    if not isinstance(num, int) or not 0 <= num < 64:
        raise ValueError("卦象编号必须是 0~63 的整数")

    return NAME_BY_NUM[num]


def _popcount(n):
    return bin(n).count("1")


# ============================================================
# 四、数值安全工具
# ============================================================

def _is_finite_number(value):
    """判断是否为有限数值，拒绝 bool。"""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _validate_number(name, value):
    if not _is_finite_number(value):
        raise ValueError(
            f"{name} 必须是有限数值，当前值：{value!r}"
        )


def _validate(
    X,
    target_gua_name,
    W_phys,
    W_cog,
    step,
    x_scan_range,
    x_step
):
    if target_gua_name not in NUM_BY_NAME:
        raise ValueError(
            f"未知卦名：{target_gua_name!r}"
        )

    _validate_number("X", X)
    _validate_number("W_phys", W_phys)
    _validate_number("W_cog", W_cog)
    _validate_number("step", step)
    _validate_number("x_scan_range", x_scan_range)
    _validate_number("x_step", x_step)

    if not 0.0 <= W_phys <= 1.0:
        raise ValueError("W_phys 必须在 [0,1]")

    if not 0.0 <= W_cog <= 1.0:
        raise ValueError("W_cog 必须在 [0,1]")

    if not 0.0 < step <= 1.0:
        raise ValueError("step 必须在 (0,1]")

    if x_scan_range < 0:
        raise ValueError("x_scan_range 不得小于 0")

    if x_step <= 0:
        raise ValueError("x_step 必须大于 0")

    estimated_points = (
        math.ceil(1.0 / step) + 1
    )

    if estimated_points > MAX_SCAN_POINTS:
        raise ValueError("A/B 扫描点数超过安全上限")

    if x_scan_range / x_step > MAX_SCAN_POINTS:
        raise ValueError("C 路径扫描点数超过安全上限")


# ============================================================
# 五、核心演化模型
# ============================================================

def get_dong_info(w_diff):
    w_diff = round(w_diff, 6)

    if w_diff > 0.6:
        return "三爻动（大变局）", 3

    elif w_diff > 0.3:
        return "二爻动（中变局）", 2

    elif w_diff > 0.1:
        return "一爻动（小变局）", 1

    else:
        return "静卦（不变）", 0


def get_ben_gua(X):
    if not _is_finite_number(X):
        raise ValueError("X 必须是有限数值")

    phase = X % (2 * PI)

    return int(
        (phase / (2 * PI)) * 64
    ) % 64


def get_zhi_gua_num(
    ben_num,
    W_phys,
    W_cog
):
    w_diff = round(
        abs(W_cog - W_phys), 6
    )

    imbalance = W_cog - W_phys

    powers = [
        (
            abs(
                math.sin(
                    W_phys * PI
                    + i * 0.618
                    + w_diff
                )
            ),
            i
        )
        for i in range(6)
    ]

    powers.sort(reverse=True)

    _, dong_count = get_dong_info(w_diff)

    zhi_num = ben_num

    for _, idx in powers[:dong_count]:
        zhi_num ^= 1 << idx

    return (
        zhi_num,
        dong_count,
        w_diff,
        imbalance
    )


def gua_desc(name):
    kw = GUA_KEYWORD.get(name, "")

    if kw:
        return f"【{name}】（{kw}）"

    return f"【{name}】"


def verify_roundtrip(
    X,
    target_gua_name,
    W_phys,
    W_cog
):
    ben_num = get_ben_gua(X)

    zhi_num, dc, wd, _ = get_zhi_gua_num(
        ben_num,
        W_phys,
        W_cog
    )

    actual = num_to_name(zhi_num)

    return (
        actual == target_gua_name,
        actual,
        wd,
        dc
    )


def describe_dong_transition(
    start_w_diff,
    end_w_diff
):
    start_desc, start_cnt = get_dong_info(
        start_w_diff
    )

    end_desc, end_cnt = get_dong_info(
        end_w_diff
    )

    cross = abs(end_cnt - start_cnt)

    if cross == 0:
        return (
            f"同档内调整（{start_desc} → "
            f"{end_desc}），连续可走，无相变断点"
        )

    return (
        f"{start_desc}（{start_cnt}爻） → "
        f"{end_desc}（{end_cnt}爻），"
        f"跨 {cross} 个相变断点"
    )


def _imbalance_tag(imb):
    if abs(imb) < 0.05:
        return "基本平衡"

    if imb > 0:
        return f"包装虚高 {imb:+.2f}"

    return f"实力过剩 {imb:+.2f}"


# ============================================================
# 六、统一决策评分
# ============================================================

def _decision_score(
    distance_norm,
    structure_norm,
    risk_norm
):
    """
    统一启发式评分。

    distance_norm：变化距离，0~1
    structure_norm：结构变化程度，0~1
    risk_norm：执行风险，0~1

    分数越低，表示在当前评分规则下越优。

    注意：
    这是策略排序工具，不是经过现实数据拟合的成本模型。
    """

    distance_norm = min(
        1.0, max(0.0, distance_norm)
    )

    structure_norm = min(
        1.0, max(0.0, structure_norm)
    )

    risk_norm = min(
        1.0, max(0.0, risk_norm)
    )

    score = (
        DECISION_WEIGHT_DISTANCE
        * distance_norm

        + DECISION_WEIGHT_STRUCTURE
        * structure_norm

        + DECISION_WEIGHT_RISK
        * risk_norm
    )

    return round(score, 6)


# ============================================================
# 七、A/B 扫描网格
# ============================================================

def _make_scan_grid(step):
    """
    按用户指定步长生成 [0,1] 网格。

    例如 step=0.3：
    [0, 0.3, 0.6, 0.9, 1.0]

    终点 1.0 强制纳入。
    """

    values = []

    i = 0

    while True:
        w = i * step

        if w >= 1.0:
            break

        values.append(round(w, 12))
        i += 1

    values.append(1.0)

    # 去重并确保严格递增
    grid = sorted(set(values))

    if grid[0] != 0.0:
        grid.insert(0, 0.0)

    if grid[-1] != 1.0:
        grid.append(1.0)

    return grid


# ============================================================
# 八、A/B 全窗口扫描
# ============================================================

def _scan_path_all_windows(
    ben_num,
    fixed_W,
    target_gua_name,
    current_w,
    vary,
    step
):
    """
    返回所有连续可行窗口。

    fragile=True：
    当前扫描网格下只有一个命中点。

    不代表连续数学意义上的孤立解。
    """

    target_num = NUM_BY_NAME[target_gua_name]

    if _popcount(
        target_num ^ ben_num
    ) > 3:
        return []

    grid = _make_scan_grid(step)

    hits = []

    for idx, w in enumerate(grid):

        if vary == "cog":
            wp, wc = fixed_W, w

        elif vary == "phys":
            wp, wc = w, fixed_W

        else:
            raise ValueError(
                f"未知扫描方向：{vary}"
            )

        result_num = get_zhi_gua_num(
            ben_num,
            wp,
            wc
        )[0]

        if result_num == target_num:
            hits.append(idx)

    if not hits:
        return []

    # 连续命中分组
    groups = []

    current_group = [hits[0]]

    for idx in hits[1:]:

        if idx == current_group[-1] + 1:
            current_group.append(idx)

        else:
            groups.append(current_group)
            current_group = [idx]

    groups.append(current_group)

    windows = []

    for group in groups:

        first_idx = group[0]
        last_idx = group[-1]

        mid_idx = group[len(group) // 2]

        w_start = grid[first_idx]
        w_end = grid[last_idx]
        w_mid = grid[mid_idx]

        win_width = w_end - w_start

        is_boundary = (
            first_idx == 0
            or last_idx == len(grid) - 1
        )

        windows.append({
            "w_mid": w_mid,
            "w_start": w_start,
            "w_end": w_end,
            "win_width": win_width,
            "idx_group": group,
            "boundary_sol": is_boundary,
            "fragile": len(group) == 1,
            "grid_points": len(group)
        })

    return windows


# ============================================================
# 九、A/B 单窗口构建
# ============================================================

def _build_single_window_result(
    X,
    target,
    cur_w_diff,
    base_w_val,
    win,
    vary
):
    w = win["w_mid"]

    if vary == "cog":
        new_wp, new_wc = base_w_val, w

    else:
        new_wp, new_wc = w, base_w_val

    ok, actual, wd, dc = verify_roundtrip(
        X,
        target,
        new_wp,
        new_wc
    )

    raw_delta = w - base_w_val

    delta = round(raw_delta, 2)

    cross = abs(
        get_dong_info(wd)[1]
        - get_dong_info(cur_w_diff)[1]
    )

    fragile = win["fragile"]

    boundary = win["boundary_sol"]

    # 保留原 V7.6.2 成本计算方式
    legacy_cost = (
        abs(raw_delta)
        + CROSS_PENALTY * cross
        + (
            FRAGILE_PENALTY
            if fragile else 0.0
        )
        + (
            BOUNDARY_PENALTY
            if boundary else 0.0
        )
    )

    # A/B 统一决策评分
    distance_norm = abs(raw_delta)

    structure_norm = cross / 3.0

    risk_norm = (
        0.5 * int(fragile)
        + 0.5 * int(boundary)
    )

    decision_cost = _decision_score(
        distance_norm,
        structure_norm,
        risk_norm
    )

    return {
        "w": w,
        "w_start": win["w_start"],
        "w_end": win["w_end"],

        "delta": delta,

        "width": win["win_width"],

        "fragile": fragile,
        "boundary_sol": boundary,

        "grid_points": win["grid_points"],

        "w_diff": wd,
        "dong_count": dc,

        "cross": cross,

        "transition": describe_dong_transition(
            cur_w_diff,
            wd
        ),

        "actual": actual,
        "ok": ok,

        # 原始成本字段，保持兼容
        "cost": round(legacy_cost, 6),

        # 新统一推荐成本
        "decision_cost": decision_cost,

        "risk_norm": risk_norm
    }


# ============================================================
# 十、C 路径扫描网格
# ============================================================

def _make_x_offsets(x_scan_range, x_step):
    """
    生成完整对称扫描偏移。

    保证：
    1. 包含 0。
    2. 包含正负方向。
    3. 即使范围不能整除步长，也包含最终边界。
    """

    offsets = [0.0]

    if x_scan_range == 0:
        return offsets

    n = int(
        math.floor(
            x_scan_range / x_step
            + 1e-12
        )
    )

    for k in range(1, n + 1):

        distance = k * x_step

        if distance > x_scan_range + 1e-12:
            break

        offsets.append(distance)
        offsets.append(-distance)

    # 强制覆盖扫描范围边界
    if not math.isclose(
        n * x_step,
        x_scan_range,
        rel_tol=1e-12,
        abs_tol=1e-12
    ):

        offsets.append(x_scan_range)
        offsets.append(-x_scan_range)

    # 去重，保留原顺序
    unique = []
    seen = set()

    for off in offsets:

        key = round(off, 12)

        if key not in seen:
            seen.add(key)
            unique.append(off)

    return unique


# ============================================================
# 十一、C 路径完整搜索
# ============================================================

def _scan_x(
    X,
    target,
    W_phys,
    W_cog,
    x_scan_range,
    x_step,
    limit=3
):
    """
    C 路径：

    1. 完整扫描指定 X 范围。
    2. 本卦去重。
    3. 保留每个本卦首次出现的最近候选。
    4. 全部扫描完成后统一排序。
    5. 返回综合代价最低的候选。

    保留旧 cost 字段。
    新增 decision_cost 字段。
    """

    target_num = NUM_BY_NAME[target]

    offsets = _make_x_offsets(
        x_scan_range,
        x_step
    )

    current_ben = get_ben_gua(X)

    seen = set()

    raw_out = []

    for off in offsets:

        tx = X + off

        b = get_ben_gua(tx)

        # 同一卦象只保留最近出现的候选
        if b in seen:
            continue

        if _popcount(
            b ^ target_num
        ) > 3:
            continue

        zhi_num = get_zhi_gua_num(
            b,
            W_phys,
            W_cog
        )[0]

        if zhi_num != target_num:
            continue

        seen.add(b)

        ok, actual, _, _ = verify_roundtrip(
            tx,
            target,
            W_phys,
            W_cog
        )

        ben_diff_bits = _popcount(
            b ^ current_ben
        )

        offset_abs = abs(off)

        # 保留旧版 C 成本
        legacy_cost = (
            offset_abs * 0.01
            + ben_diff_bits * 0.2
        )

        if x_scan_range > 0:
            distance_norm = (
                offset_abs / x_scan_range
            )
        else:
            distance_norm = 0.0

        structure_norm = (
            ben_diff_bits / 6.0
        )

        # C 路径执行风险没有直接观测值，
        # 使用中性风险，不代表 C 路径实际安全。
        risk_norm = C_UNKNOWN_RISK

        decision_cost = _decision_score(
            distance_norm,
            structure_norm,
            risk_norm
        )

        raw_out.append({
            "x": tx,
            "offset": off,

            "ben": b,

            "ben_flip_bits": ben_diff_bits,

            "actual": actual,
            "ok": ok,

            "cost": round(
                legacy_cost, 6
            ),

            "decision_cost": decision_cost,

            "risk_norm": risk_norm
        })

    # 完整搜索结束后再统一排序
    sorted_out = sorted(
        raw_out,
        key=lambda item: (
            item["decision_cost"],
            abs(item["offset"]),
            item["ben_flip_bits"]
        )
    )

    return sorted_out[:limit]


# ============================================================
# 十二、核心计算 solve()
# ============================================================

def solve(
    X,
    target_gua_name,
    current_W_phys,
    current_W_cog,
    step=0.01,
    x_scan_range=200,
    x_step=1
):
    """
    只负责计算，不打印。

    主要返回字段与 V7.6.2 保持兼容。
    """

    _validate(
        X,
        target_gua_name,
        current_W_phys,
        current_W_cog,
        step,
        x_scan_range,
        x_step
    )

    ben_num = get_ben_gua(X)

    zn, _, cur_wd, cur_imb = get_zhi_gua_num(
        ben_num,
        current_W_phys,
        current_W_cog
    )

    cur_zhi = num_to_name(zn)

    scan_grid = _make_scan_grid(step)

    res = {
        "version": "V7.6.3",

        "X": X,
        "target": target_gua_name,

        "W_phys": current_W_phys,
        "W_cog": current_W_cog,

        "current_ben": num_to_name(ben_num),

        "current_zhi": cur_zhi,

        "current_w_diff": cur_wd,

        "current_dong": get_dong_info(cur_wd)[0],

        "current_imb": cur_imb,

        "already": cur_zhi == target_gua_name,

        "A_windows": [],
        "B_windows": [],

        "A": None,
        "B": None,

        "C": [],

        "recommend": None,

        "recommend_cost": None,

        "recommend_detail": None,

        "step": step,

        "actual_scan_points": len(scan_grid),

        "actual_max_scan_gap": max(
            (
                scan_grid[i + 1] - scan_grid[i]
                for i in range(len(scan_grid) - 1)
            ),
            default=0.0
        ),

        "x_step": x_step,

        "x_scan_range": x_scan_range,

        "decision_weights": {
            "distance": DECISION_WEIGHT_DISTANCE,
            "structure": DECISION_WEIGHT_STRUCTURE,
            "risk": DECISION_WEIGHT_RISK
        }
    }

    # 当前已经命中目标
    if res["already"]:
        res["recommend"] = "HOLD"
        res["recommend_detail"] = (
            "当前状态已经命中目标，"
            "无需为了改变而改变。"
        )
        return res

    # --------------------------------------------------------
    # A 路径：只调整 W_cog
    # --------------------------------------------------------

    raw_a_win = _scan_path_all_windows(
        ben_num,
        current_W_phys,
        target_gua_name,
        current_W_cog,
        "cog",
        step
    )

    for win in raw_a_win:

        item = _build_single_window_result(
            X,
            target_gua_name,
            cur_wd,
            current_W_cog,
            win,
            "cog"
        )

        res["A_windows"].append(item)

    # A 路径按成本排序
    res["A_windows"].sort(
        key=lambda d: (
            d["decision_cost"],
            d["cost"]
        )
    )

    if res["A_windows"]:
        res["A"] = res["A_windows"][0]

    # --------------------------------------------------------
    # B 路径：只调整 W_phys
    # --------------------------------------------------------

    raw_b_win = _scan_path_all_windows(
        ben_num,
        current_W_cog,
        target_gua_name,
        current_W_phys,
        "phys",
        step
    )

    for win in raw_b_win:

        item = _build_single_window_result(
            X,
            target_gua_name,
            cur_wd,
            current_W_phys,
            win,
            "phys"
        )

        res["B_windows"].append(item)

    res["B_windows"].sort(
        key=lambda d: (
            d["decision_cost"],
            d["cost"]
        )
    )

    if res["B_windows"]:
        res["B"] = res["B_windows"][0]

    # --------------------------------------------------------
    # C 路径：调整 X
    # --------------------------------------------------------

    res["C"] = _scan_x(
        X,
        target_gua_name,
        current_W_phys,
        current_W_cog,
        x_scan_range,
        x_step
    )

    # --------------------------------------------------------
    # A/B/C 统一推荐
    # --------------------------------------------------------

    candidates = []

    if res["A"] is not None:
        candidates.append({
            "path": "A",
            "decision_cost": res["A"]["decision_cost"],
            "legacy_cost": res["A"]["cost"]
        })

    if res["B"] is not None:
        candidates.append({
            "path": "B",
            "decision_cost": res["B"]["decision_cost"],
            "legacy_cost": res["B"]["cost"]
        })

    if res["C"]:
        best_c = res["C"][0]

        candidates.append({
            "path": "C",
            "decision_cost": best_c["decision_cost"],
            "legacy_cost": best_c["cost"]
        })

    if candidates:

        candidates.sort(
            key=lambda item: (
                item["decision_cost"],
                item["legacy_cost"]
            )
        )

        best = candidates[0]

        res["recommend"] = best["path"]

        res["recommend_cost"] = (
            best["decision_cost"]
        )

        res["recommend_detail"] = best

    return res


# ============================================================
# 十三、单窗口渲染
# ============================================================

def _render_single_window(
    label,
    title_pos,
    title_neg,
    title_zero,
    field,
    p,
    is_best=False
):
    d = p["delta"]

    tag = (
        title_pos if d > 0
        else title_neg if d < 0
        else title_zero
    )

    best_mark = (
        "⭐最优 "
        if is_best
        else "🔹备选 "
    )

    print(
        f"{label} {best_mark}"
        f"【{tag}】"
        f" {field} → {p['w']:.4f}"
        f"（差 {d:+.2f}）"
        f"原始成本:{p['cost']:.3f}"
        f"统一评分:{p['decision_cost']:.3f}"
    )

    print(
        f"   📐 可行窗口："
        f"[{p['w_start']:.4f}, "
        f"{p['w_end']:.4f}]"
    )

    print(
        f"   ⚡ 档位：{p['transition']}"
    )

    print(
        f"   ✅ 闭环：代回正跑 → "
        f"【{p['actual']}】"
        f"{'命中' if p['ok'] else '异常'}"
    )

    warn_lines = []

    if p["fragile"]:
        warn_lines.append(
            "当前扫描网格下仅有一个命中点，"
            "尚不能认定为数学孤立解。"
        )

    if p["boundary_sol"]:
        warn_lines.append(
            "窗口触碰 0/1 参数边界，"
            "实际维持条件可能受限。"
        )

    if warn_lines:

        for msg in warn_lines:
            print(f"   ⚠️ 风险：{msg}")

    else:

        print(
            f"   🛡️ 扫描窗口宽度："
            f"{p['width']:.4f}"
        )

    if p["dong_count"] >= 2:
        print(
            "   ⚡ 落点动爻数 >= 2，"
            "建议分阶段推进。"
        )


# ============================================================
# 十四、主渲染函数
# ============================================================

def render(r):

    line = "=" * 64
    sub = "-" * 64

    print(line)

    print(
        f"       永心模型 {r['version']} "
        "· 战略沙盘反推系统"
    )

    print(line)

    print(
        "【一二三语义】"
        "一=底座X  二=内核W平衡  三=之卦显化"
    )

    print(
        "核心逻辑："
        "用结果（三）倒逼行动（二），"
        "用行动修正底座（一）"
    )

    print(sub)

    print(
        f"🎯 目标卦：{gua_desc(r['target'])}"
    )

    print(
        f"📍 当前：X={r['X']} "
        f"| W_phys={r['W_phys']} "
        f"| W_cog={r['W_cog']}"
    )

    print(sub)

    print(
        f"👉 当前本卦："
        f"{gua_desc(r['current_ben'])}"
    )

    print(
        f"👉 当前之卦："
        f"{gua_desc(r['current_zhi'])}"
    )

    print(
        f"   当前 w_diff="
        f"{r['current_w_diff']:.4f}"
        f"，处于【{r['current_dong']}】"
    )

    print(
        f"   失衡方向："
        f"{_imbalance_tag(r['current_imb'])}"
    )

    print(
        f"   A/B 扫描点数："
        f"{r['actual_scan_points']}"
        f" | 最大实际间隔："
        f"{r['actual_max_scan_gap']:.5f}"
    )

    print(sub)

    if r["already"]:

        print(
            "✅ 当前已经与目标重合，"
            "保持现状即可。"
        )

        print(line)

        return

    print(
        f"📊 跨度："
        f"{gua_desc(r['current_zhi'])}"
        f" → {gua_desc(r['target'])}"
    )

    print()

    print("📜 【决策卡】")

    print(sub)

    # --------------------------------------------------------
    # A 路径
    # --------------------------------------------------------

    if r["A_windows"]:

        for idx, win_data in enumerate(
            r["A_windows"]
        ):

            _render_single_window(
                "🅰️",
                "提升包装/名气",
                "收敛锋芒/降低包装",
                "包装已合适",
                "W_cog",
                win_data,
                is_best=(idx == 0)
            )

            if idx != len(r["A_windows"]) - 1:
                print("   ---")

    else:

        print(
            "🅰️ 【路径A："
            "单靠调整认知/包装未找到可行窗口】"
        )

    print(sub)

    # --------------------------------------------------------
    # B 路径
    # --------------------------------------------------------

    if r["B_windows"]:

        for idx, win_data in enumerate(
            r["B_windows"]
        ):

            _render_single_window(
                "🅱️",
                "提升硬实力",
                "收敛扩张/重新归位",
                "硬实力已合适",
                "W_phys",
                win_data,
                is_best=(idx == 0)
            )

            if idx != len(r["B_windows"]) - 1:
                print("   ---")

    else:

        print(
            "🅱️ 【路径B："
            "单靠调整硬实力未找到可行窗口】"
        )

    print(sub)

    # --------------------------------------------------------
    # C 路径
    # --------------------------------------------------------

    if r["C"]:

        print(
            "🇨 【路径C：换赛道/调整底座】"
            "（完整扫描、去重、统一评分排序）"
        )

        for c in r["C"]:

            print(
                f"   · X ≈ {c['x']:g} "
                f"（{c['offset']:+g}）"
                f"原始成本={c['cost']:.3f}"
                f"统一评分={c['decision_cost']:.3f}"
                f" 本卦翻转位数:"
                f"{c['ben_flip_bits']}"
                f" →【{c['actual']}】"
                f"{'✅' if c['ok'] else '✗'}"
            )

        print(
            f"   ℹ️ 扫描范围："
            f"X ± {r['x_scan_range']}"
        )

        print(
            f"   ℹ️ 扫描步长："
            f"{r['x_step']}"
        )

        print(
            "   ℹ️ 候选在完整扫描后统一排序，"
            "并按本卦去重。"
        )

    else:

        print(
            f"🇨 【路径C：X±"
            f"{r['x_scan_range']} "
            f"范围内未发现可行候选】"
        )

    print(sub)

    # --------------------------------------------------------
    # 最终推荐
    # --------------------------------------------------------

    print(line)

    print("🧭 【三路径综合推荐】")

    msg = {
        "A": (
            "👉 推荐 A：优先调整认知、"
            "表达、包装或市场呈现。"
        ),

        "B": (
            "👉 推荐 B：优先补充硬实力，"
            "改善现实基础。"
        ),

        "C": (
            "👉 推荐 C：考虑调整底座、"
            "环境或赛道。"
        ),

        "HOLD": (
            "👉 保持当前状态，"
            "当前结果已经命中目标。"
        ),

        None: (
            "👉 三条路径均未找到可行解，"
            "建议重新审视目标与约束条件。"
        )
    }

    print(msg[r["recommend"]])

    if r["recommend_cost"] is not None:

        print(
            f"   统一决策评分："
            f"{r['recommend_cost']:.6f}"
        )

    print()

    print(
        "📌 评分说明："
        "距离65%、结构变化20%、风险15%。"
    )

    print(
        "📌 C路径风险数据尚未直接观测，"
        "采用中性风险值，不代表实际无风险。"
    )

    print(
        "💡 定位提醒："
        "本工具是'拆问题的扳手'，"
        "不是'定答案的罗盘'。"
    )

    print(line)


# ============================================================
# 十五、统一入口
# ============================================================

def strategy_sandbox(
    X,
    target_gua_name,
    current_W_phys,
    current_W_cog,
    step=0.01,
    x_scan_range=200,
    x_step=1
):

    result = solve(
        X,
        target_gua_name,
        current_W_phys,
        current_W_cog,
        step,
        x_scan_range,
        x_step
    )

    render(result)

    return result


# ============================================================
# 十六、自动化基础测试
# ============================================================

def run_self_tests():

    print("\n开始 V7.6.3 基础测试……")

    # 1. 64 卦映射双射
    assert len(NAME_BY_NUM) == 64

    assert len(NUM_BY_NAME) == 64

    for n in range(64):

        name = num_to_name(n)

        assert NUM_BY_NAME[name] == n

    print("✅ 测试1：64卦映射双射")

    # 2. 非整除步长
    grid = _make_scan_grid(0.3)

    assert grid[0] == 0.0

    assert grid[-1] == 1.0

    assert all(
        grid[i] < grid[i + 1]
        for i in range(len(grid) - 1)
    )

    print("✅ 测试2：非整除扫描步长")

    # 3. A/B 网格终点覆盖
    grid = _make_scan_grid(0.07)

    assert grid[-1] == 1.0

    print("✅ 测试3：扫描边界覆盖")

    # 4. C 路径偏移对称性
    offsets = _make_x_offsets(10, 3)

    assert 0.0 in offsets

    assert 10.0 in offsets

    assert -10.0 in offsets

    print("✅ 测试4：C路径扫描边界")

    # 5. 数值异常拒绝
    invalid_values = [
        float("nan"),
        float("inf"),
        float("-inf")
    ]

    for value in invalid_values:

        try:

            _validate_number(
                "test",
                value
            )

            raise AssertionError(
                "非法数值未被拦截"
            )

        except ValueError:
            pass

    print("✅ 测试5：NaN/Infinity拦截")

    # 6. 统一评分范围
    score = _decision_score(
        0.5,
        0.5,
        0.5
    )

    assert 0.0 <= score <= 1.0

    print("✅ 测试6：统一评分范围")

    # 7. 正向闭环测试
    test_X = 2019
    test_wp = 0.9
    test_wc = 0.1

    ben = get_ben_gua(test_X)

    zhi = get_zhi_gua_num(
        ben,
        test_wp,
        test_wc
    )[0]

    target = num_to_name(zhi)

    ok, actual, _, _ = verify_roundtrip(
        test_X,
        target,
        test_wp,
        test_wc
    )

    assert ok

    assert actual == target

    print("✅ 测试7：正向闭环验证")

    # 8. solve 结构测试
    result = solve(
        X=test_X,
        target_gua_name=target,
        current_W_phys=test_wp,
        current_W_cog=test_wc
    )

    assert result["already"] is True

    assert result["recommend"] == "HOLD"

    assert "A_windows" in result

    assert "B_windows" in result

    assert "C" in result

    print("✅ 测试8：结构化返回")

    print("\n🎉 V7.6.3 基础测试全部通过！")

    print(
        "注意：基础测试通过不等于"
        "模型现实预测能力得到验证。"
    )

    return True


# ============================================================
# 十七、运行示例
# ============================================================

if __name__ == "__main__":

    # 先运行基础测试
    run_self_tests()

    print("\n")

    # Demo 示例
    res_out = strategy_sandbox(
        X=2019,
        target_gua_name="泰",
        current_W_phys=0.9,
        current_W_cog=0.1,
        step=0.01,
        x_scan_range=200,
        x_step=1
    )

    # 结构化结果可以直接调用
    #
    # res_out["A_windows"]
    # res_out["B_windows"]
    # res_out["C"]
    # res_out["recommend"]
    # res_out["recommend_cost"]

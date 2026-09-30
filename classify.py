#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游情报 — 共享分类与评分规则
被 collect.py（打标签）与 travel_processor.py（算分 + 原因卡）共用。
所有阈值、城市表、类型映射都集中在此，方便调参。
"""
import re

# ── 全国主要旅游城市（省/市）───────────────────────────
# 采集时按「体验类型关键词 × 这些城市」批量拉 POI。
TOUR_CITIES = [
    ("浙江", "杭州"), ("浙江", "绍兴"), ("浙江", "宁波"), ("浙江", "温州"), ("浙江", "嘉兴"),
    ("浙江", "湖州"), ("浙江", "金华"), ("浙江", "台州"), ("浙江", "舟山"), ("浙江", "丽水"),
    ("江苏", "南京"), ("江苏", "苏州"), ("江苏", "无锡"), ("江苏", "扬州"), ("江苏", "常州"),
    ("江苏", "徐州"), ("江苏", "南通"), ("江苏", "镇江"), ("江苏", "泰州"),
    ("上海", "上海"),
    ("安徽", "黄山"), ("安徽", "合肥"), ("安徽", "池州"), ("安徽", "安庆"), ("安徽", "宣城"),
    ("北京", "北京"), ("天津", "天津"),
    ("广东", "广州"), ("广东", "深圳"), ("广东", "珠海"), ("广东", "汕头"), ("广东", "湛江"),
    ("福建", "厦门"), ("福建", "福州"), ("福建", "泉州"), ("福建", "漳州"), ("福建", "武夷山"),
    ("山东", "青岛"), ("山东", "济南"), ("山东", "烟台"), ("山东", "威海"), ("山东", "泰安"),
    ("海南", "三亚"), ("海南", "海口"),
    ("四川", "成都"), ("四川", "乐山"), ("四川", "阿坝"), ("四川", "甘孜"), ("四川", "绵阳"),
    ("云南", "昆明"), ("云南", "大理"), ("云南", "丽江"), ("云南", "西双版纳"), ("云南", "香格里拉"),
    ("广西", "桂林"), ("广西", "南宁"), ("广西", "北海"), ("广西", "柳州"),
    ("湖南", "长沙"), ("湖南", "张家界"), ("湖南", "凤凰"), ("湖南", "衡阳"),
    ("湖北", "武汉"), ("湖北", "宜昌"), ("湖北", "恩施"),
    ("江西", "南昌"), ("江西", "九江"), ("江西", "景德镇"), ("江西", "上饶"),
    ("陕西", "西安"), ("陕西", "延安"), ("陕西", "宝鸡"),
    ("重庆", "重庆"),
    ("贵州", "贵阳"), ("贵州", "黔东南"), ("贵州", "安顺"), ("贵州", "遵义"),
    ("河北", "石家庄"), ("河北", "承德"), ("河北", "秦皇岛"),
    ("山西", "太原"), ("山西", "大同"), ("山西", "平遥"),
    ("河南", "郑州"), ("河南", "洛阳"), ("河南", "开封"),
    ("辽宁", "大连"), ("辽宁", "沈阳"),
    ("吉林", "长春"), ("吉林", "延边"),
    ("黑龙江", "哈尔滨"),
    ("甘肃", "兰州"), ("甘肃", "敦煌"), ("甘肃", "张掖"),
    ("青海", "西宁"), ("青海", "海东"),
    ("宁夏", "银川"),
    ("新疆", "乌鲁木齐"), ("新疆", "喀什"), ("新疆", "伊犁"), ("新疆", "吐鲁番"),
    ("西藏", "拉萨"), ("西藏", "林芝"),
    ("内蒙古", "呼和浩特"), ("内蒙古", "呼伦贝尔"), ("内蒙古", "赤峰"),
]

# ── 体验类型（用户建议：爬山/观海/地区等，按大数据现有类型推荐）──
# 顺序即匹配优先级；type 或 name 命中任一关键词即归该类。
EXPERIENCE_TYPES = [
    ("mountain", "爬山登山", ["山", "峰", "登山", "徒步", "峡谷", "森林公园", "自然风光", "雪山", "草原天路"]),
    ("sea",      "海滨观海", ["海滨", "沙滩", "海岛", "海岸", "海洋", "湾", "礁", "渔港"]),
    ("ancient",  "古城古镇", ["古镇", "古城", "古村落", "历史街区", "老街", "水乡", "寨"]),
    ("park",     "主题乐园", ["主题公园", "游乐园", "水上乐园", "动物园", "海洋馆", "度假区"]),
    ("food",     "美食街区", ["美食", "小吃", "夜市", "餐饮街", "美食街", "步行街"]),
    ("museum",   "博物馆馆", ["博物馆", "美术馆", "展览馆", "纪念馆", "文化馆", "非遗", "艺术馆"]),
    ("nature",   "自然秘境", ["湖", "湿地", "森林公园", "自然保护区", "溶洞", "瀑布", "竹海", "花海", "茶园"]),
    ("temple",   "寺庙道观", ["寺", "庙", "道观", "庵", "禅"]),
    ("view",     "城市观景", ["观景", "塔", "天台", "地标", "摩天", "大桥", "夜景"]),
]

# ── 季节适配（type 关键词 → 最佳月份集合 + 较差月份）──
SEASON_RULES = [
    (["海滨", "沙滩", "海岛", "海岸", "海洋", "湾"], [5, 6, 7, 8, 9, 10], [12, 1, 2]),
    (["山", "峰", "登山", "雪山", "峡谷"], [4, 5, 9, 10], [7, 8]),
    (["古镇", "古城", "老街", "水乡"], [3, 4, 5, 9, 10, 11], [7, 8]),
    (["主题公园", "游乐园", "水上乐园"], [4, 5, 6, 9, 10], [1, 2, 7, 8, 12]),
    (["博物馆", "美术馆", "展览馆", "纪念馆"], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], []),
    (["湖", "湿地", "花海", "竹海", "茶园", "草原"], [3, 4, 5, 6, 9, 10], [12, 1, 2]),
    (["寺", "庙", "道观"], [3, 4, 5, 9, 10, 11], [7, 8]),
]

MONTH_NAMES = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

# ── 知名度关键词（用于热度分层代理：大众/小众）──
FAME_KEYWORDS = ["国家级", "5A", "世界遗产", "世界文化", "世界自然", "知名", "著名", "老字号",
                 "西湖", "泰山", "黄山", "峨眉", "武夷", "张家界", "丽江", "大理", "鼓浪屿",
                 "外滩", "故宫", "长城", "兵马俑", "布达拉", "千岛湖", "颐和园"]

# ── 城市能级（可达性评分代理：一线城市/新一线/知名旅游城）──
TIER1 = ["北京", "上海", "广州", "深圳"]
TIER_NEW1 = ["杭州", "成都", "南京", "苏州", "重庆", "武汉", "西安", "长沙", "青岛", "厦门",
             "天津", "宁波", "无锡", "福州", "合肥", "昆明", "大连", "济南", "沈阳", "哈尔滨"]

# ── 出片率基础分（按体验类型）──
FILM_BASE = {
    "sea": 24, "mountain": 23, "nature": 23, "ancient": 21, "temple": 19,
    "view": 20, "food": 18, "museum": 17, "park": 16,
}

# ── 收费/性价比线索（type 关键词 → 是否常收费、性价比基调）──
PAID_TYPES = ["主题公园", "游乐园", "水上乐园", "海洋馆", "动物园", "5A", "国家级景点"]
FREE_TYPES = ["公园", "山", "峰", "古道", "海滩", "海岛", "湿地", "湖", "江", "河", "古道", "徒步"]


# 显式宗教语义（名字里出现即优先判寺庙，避免"径山寺"被"山"带偏成爬山）
RELIGION_TOKENS = ["寺", "庙", "庵", "禅寺", "禅院", "道观", "教堂", "礼拜堂", "清真寺"]


def infer_experience(spot_type, name):
    """返回 (key, label)，未命中回退 nature。
    判定顺序：显式宗教语义 → 体验类型表（古镇/海滨/爬山…）→ 自然秘境兜底。"""
    text = (spot_type or "") + " " + (name or "")
    if name and any(t in name for t in RELIGION_TOKENS):
        return "temple", "寺庙道观"
    for key, label, kws in EXPERIENCE_TYPES:
        if any(k in text for k in kws):
            return key, label
    return "nature", "自然秘境"


def best_season(spot_type):
    """返回 (best_months:list[int], off_months:list[int])。"""
    best, off = set(), set()
    for kws, b, o in SEASON_RULES:
        if any(k in (spot_type or "") for k in kws):
            best.update(b)
            off.update(o)
    if not best:
        best = set(range(3, 12))  # 默认 3-11 月皆宜
    return sorted(best), sorted(off)


def hot_tier(spot_type, name, rating):
    """热度分层代理：大众 / 小众。
    注：高德免费接口无'笔记数/搜索量'，这里用「评分 + 知名度标签」作代理，
    后续可接小红书/抖音笔记数 API 校准。"""
    fame = any(k in ((spot_type or "") + (name or "")) for k in FAME_KEYWORDS)
    r = rating or 0
    hot_score = 0.5 * (r / 5.0) + (0.5 if fame else 0.15)
    return "大众" if hot_score >= 0.70 else "小众"


def parse_cost(raw):
    """高德 biz_ext.cost 可能是 '[]'（无数据）或数字字符串。返回 float 或 None。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if s in ("", "[]", "null", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def score_spot(spot):
    """四维评分：景观价值30 / 性价比25 / 可达性20 / 出片率25。
    返回 (total, detail)。"""
    etype = spot.get("etype", "nature")
    rating = spot.get("rating") or 0.0
    city = spot.get("city", "")
    spot_type = spot.get("type", "")

    # 1) 景观价值（评分归一）
    scenic = min(rating / 5.0, 1.0) * 30

    # 2) 性价比（是否收费 + 人均）
    cost = spot.get("cost")
    if any(k in spot_type for k in FREE_TYPES) and not any(k in spot_type for k in PAID_TYPES):
        value = 23            # 自然/免费类，性价比高
    elif cost is not None and cost > 0:
        # 人均越高性价比越低（150 以上明显掉分）
        value = max(8, 25 - max(0, (cost - 60)) / 90.0 * 17)
    else:
        value = 16            # 收费但无人均数据，中性
    value = min(value, 25)

    # 3) 可达性（城市能级代理）
    if city in TIER1:
        access = 20
    elif city in TIER_NEW1:
        access = 17
    else:
        access = 13

    # 4) 出片率（类型基础分 + 评分加成）
    film = FILM_BASE.get(etype, 18) + min(rating / 5.0, 1.0) * 1.5
    film = min(film, 25)

    total = round(scenic + value + access + film, 1)
    return total, {
        "scenic": round(scenic, 1), "value": round(value, 1),
        "access": round(access, 1), "film": round(film, 1),
    }


def build_reasons(spot, total):
    """结构化原因卡：为什么值得去 3 条 + 避坑 2 条。"""
    name = spot.get("name", "该景点")
    etype_label = spot.get("etype_label", "景点")
    rating = spot.get("rating") or 0
    prov = spot.get("province", "")
    city = spot.get("city", "")
    best, off = best_season(spot.get("type", ""))
    cost = spot.get("cost")

    worth = []
    worth.append(f"「{name}」属{etype_label}，高德评分 {rating} 分，在同类里口碑靠前。")
    if best:
        worth.append(f"位于{prov}{city}，最佳季节 {MONTH_NAMES[best[0]-1]}–{MONTH_NAMES[best[-1]-1]}，体感最舒服。")
    # 类型亮点
    etype = spot.get("etype", "nature")
    highlight = {
        "sea": "一线海景，看日出/日落和赶海最出片。",
        "mountain": "登顶视野开阔，云海/全景是核心看点。",
        "ancient": "老建筑与市井烟火气浓，适合慢逛拍照。",
        "park": "项目集中、适合带娃，半日能玩透。",
        "food": "本地小吃密度高，边走边吃最地道。",
        "museum": " indoors 不受天气影响，展陈有看头。",
        "nature": "湖光山色视野干净，适合发呆和空镜。",
        "temple": "古建与香火气并存，氛围感强。",
        "view": "城市天际线/夜景机位，出片率高。",
    }.get(etype, "风光不错，值得专程去。")
    worth.append(highlight)

    avoid = []
    if off:
        off_names = "、".join(MONTH_NAMES[m - 1] for m in off[:3])
        reason = "天冷/人多/景观寡淡" if etype in ("sea",) else "酷暑多雨/游客爆满"
        avoid.append(f"避开 {off_names} 前往，否则{reason}。")
    if cost is not None and cost > 150:
        avoid.append(f"门票/人均约 ¥{int(cost)}，偏高，建议提前网购或找联票。")
    elif cost is None:
        avoid.append("出行前确认是否收费及预约要求，热门时段常限流。")
    else:
        avoid.append(f"人均约 ¥{int(cost)}，预算可控，但周末易排队。")
    # 保证至少 2 条避坑
    if len(avoid) < 2:
        avoid.append("导航定位常飘到景区大门外，按官方停车场走更稳。")

    return {"worth": worth[:3], "avoid": avoid[:2], "best_season": best, "off_season": off}


def tag_spot(raw):
    """把高德原始 POI 标准化 + 打标签（分类/热度/季节）。"""
    biz = raw.get("biz_ext") or {}
    rating = None
    try:
        rating = float(biz.get("rating")) if biz.get("rating") not in (None, "[]", "") else None
    except (TypeError, ValueError):
        rating = None
    cost = parse_cost(biz.get("cost"))
    etype, etype_label = infer_experience(raw.get("type", ""), raw.get("name", ""))
    best, off = best_season(raw.get("type", ""))
    spot = {
        "name": raw.get("name", ""),
        "type": raw.get("type", ""),
        "province": raw.get("pname", ""),
        "city": raw.get("cityname", ""),
        "district": raw.get("adname", ""),
        "address": raw.get("address", ""),
        "location": raw.get("location", ""),
        "rating": rating,
        "cost": cost,
        "etype": etype,
        "etype_label": etype_label,
        "hot_tier": hot_tier(raw.get("type", ""), raw.get("name", ""), rating or 0),
        "best_season": best,
        "off_season": off,
        "raw": raw,
    }
    return spot

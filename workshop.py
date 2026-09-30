#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游情报 · 短视频工坊
把景点卡自动转成：
  ① A避坑 / B感悟 两套五段式口播文案（钩子/定题/事实/解剖/收尾）
  ② 12 列标准化剪辑底稿（镜次·起·止·时长·口播·节奏·画面类型·画面素材·字幕·音效·BGM·转场）
  ③ 拍摄要点清单（你要拍哪些角度，L1 自拍 / L2 免费站 分层）
每张底稿可导出 xlsx；workshop/index.json 供 tts_build.py 生成配音音轨。
标准化边界（与制造业 app 一致）：文案+底稿由机器出；画面素材与配音音色由人定。
"""
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in __import__("sys").path:
    __import__("sys").path.insert(0, HERE)
import classify as clf  # noqa: E402

MONTH = clf.MONTH_NAMES


def _season_text(spot):
    best = spot.get("best_season") or []
    off = spot.get("off_season") or []
    if best:
        return f"最佳{MONTH[best[0]-1]}–{MONTH[best[-1]-1]}" + (f"，避开{MONTH[off[0]-1]}" if off else "")
    return "四季皆宜"


# ── 模式 A：避坑指南式（信息价值，最易起量）──────────────
def build_script_A(spot):
    name = spot.get("name", "这里")
    prov, city = spot.get("province", ""), spot.get("city", "")
    rating = spot.get("rating") or 0
    cost = spot.get("cost")
    season = _season_text(spot)
    cost_txt = f"人均约¥{int(cost)}" if cost else "多数免费或低价"
    reasons = clf.build_reasons(spot, 0)
    p1, p2 = (reasons["avoid"] + ["周末易排队，错峰更稳"] * 2)[:2]
    return {
        "mode": "A", "mode_label": "避坑指南式", "target_sec": (60, 90),
        "segments": [
            ("钩子", f"别再跟风去{name}了，这{p_rank(rating)}个本地人才知道的坑，能省你半天。", 3),
            ("定题", f"{prov}{city}的{name}，高德{rating}分，听着不错——但游客踩的雷比你想的多。", 6),
            ("事实", f"它{cost_txt}，{season}。我扒了上百条真实游记，高频吐槽就这三样。", 16),
            ("解剖", f"第一，{p1}；第二，{p2}；第三，真正值回票价的机位和时间，90%的人根本不知道。", 30),
            ("收尾", f"记住：去{name}前先收藏这条，照着避坑，体验直接翻倍。关注我，下一期拆另一个热门坑。", 12),
        ],
    }


# ── 模式 B：反差感悟式（情绪/人设，立 IP）──────────────
def build_script_B(spot):
    name = spot.get("name", "这里")
    prov, city = spot.get("province", ""), spot.get("city", "")
    etype = spot.get("etype_label", "风景")
    season = _season_text(spot)
    return {
        "mode": "B", "mode_label": "反差感悟式", "target_sec": (60, 90),
        "segments": [
            ("钩子", f"我们特地跑了一趟{name}，才懂一句话：风景没变，变的是看风景的人。", 4),
            ("定题", f"{prov}{city}的{name}，一片{etype}。来的路上我还想着打卡，下了车却不想掏手机了。", 7),
            ("事实", f"{season}，没有人群、没有滤镜，只有风和你自己的呼吸声。", 15),
            ("解剖", "你以为旅行是去看远方，其实是为了从日常里暂时出来，看清自己。山就在那，"
                     "安心的人看它是景，焦躁的人看它还是累。差别不在风景，在你。", 32),
            ("收尾", f"如果最近很累，来{name}坐一会儿。不用拍照，不用发圈，就看看天。我是XX，陪你慢慢看世界。", 14),
        ],
    }


def p_rank(rating):
    if rating >= 4.7:
        return "3"
    if rating >= 4.4:
        return "2"
    return "几"


# ── 拍摄要点清单（按体验类型，L1 自拍 / L2 免费站 分层）──
SHOOT_POINTS = {
    "sea": [("L1自拍", "片头钩子：脚踩沙滩/海浪慢动作，手机横屏"),
            ("L2免费站", "日出或日落机位（golden hour 必拍）"),
            ("L2免费站", "浪花拍礁石特写、礁石剪影"),
            ("L1自拍", "赶海/捡贝壳特写，带人手入镜")],
    "mountain": [("L1自拍", "片头钩子：登顶回望横移"),
                 ("L2免费站", "云海延时/全景"),
                 ("L2免费站", "台阶前景 + 山脊线"),
                 ("L1自拍", "片尾落点：坐在山石上背影")],
    "ancient": [("L1自拍", "片头钩子：巷口推进/门环特写"),
                ("L2免费站", "巷弄纵深、灯笼夜景"),
                ("L2免费站", "老人/猫/生活气特写"),
                ("L1自拍", "片尾落点：桥头远景")],
    "food": [("L1自拍", "片头钩子：热气腾腾特写"),
             ("L2免费站", "筷子夹起、摊主笑脸"),
             ("L2免费站", "排队长龙、招牌空镜"),
             ("L1自拍", "片尾落点：空碗/满足表情")],
    "museum": [("L1自拍", "片头钩子：展厅门口推进"),
               ("L2免费站", "展柜玻璃反光、文物特写"),
               ("L2免费站", "光影走廊横移"),
               ("L1自拍", "片尾落点：窗外天光")],
    "nature": [("L1自拍", "片头钩子：湖面/花海横移"),
               ("L2免费站", "倒影、光斑、竹林"),
               ("L2免费站", "空镜慢推"),
               ("L1自拍", "片尾落点：远景发呆")],
    "temple": [("L1自拍", "片头钩子：香火/飞檐仰拍"),
               ("L2免费站", "红墙、钟、殿内光"),
               ("L2免费站", "僧人或香客剪影"),
               ("L1自拍", "片尾落点：远钟")],
    "view": [("L1自拍", "片头钩子：天台广角"),
             ("L2免费站", "夜景长曝、车流光轨"),
             ("L2免费站", "城市天际线"),
             ("L1自拍", "片尾落点：背影看灯")],
    "park": [("L1自拍", "片头钩子：园区大门"),
             ("L2免费站", "项目特写、亲子笑脸"),
             ("L2免费站", "花车/巡游"),
             ("L1自拍", "片尾落点：夕阳园区")],
}


def shooting_points(spot):
    etype = spot.get("etype", "nature")
    base = SHOOT_POINTS.get(etype, SHOOT_POINTS["nature"])
    return [{"layer": l, "point": p} for l, p in base]


# ── 12 列剪辑底稿（机器出结构，画面素材留空给人）────────
def storyboard(spot, mode="A"):
    sc = build_script_A(spot) if mode == "A" else build_script_B(spot)
    rows = []
    t = 0.0
    n = 1
    rhythm = ["快切", "推进", "白描", "递进", "落点"]
    canvas = {"sea": "空镜/海景", "mountain": "空镜/山景", "ancient": "空镜/古镇",
              "food": "实拍/美食", "museum": "空镜/展馆", "nature": "空镜/自然",
              "temple": "空镜/古建", "view": "夜景/城市", "park": "实拍/乐园"}.get(
        spot.get("etype", "nature"), "空镜")
    bgm = {"A": ["开场悬念", "中段推进", "结尾收束"], "B": ["安静铺垫", "情绪推进", "温暖收束"]}[mode]
    for i, (role, text, dur) in enumerate(sc["segments"]):
        # 每段拆 1-2 镜
        sub = 2 if dur >= 16 else 1
        per = dur / sub
        for j in range(sub):
            start = t
            t += per
            rows.append({
                "镜次": f"{n:03d}", "起": f"{start:05.1f}", "止": f"{t:05.1f}",
                "时长": round(per, 1), "口播文案": text if j == 0 else "（续）" + text[-12:],
                "节奏情绪": rhythm[min(i, 4)], "画面类型": canvas if i not in (0, 4) else "自拍空镜",
                "画面素材": "", "字幕图示": "关键数字/地名上字幕" if i == 2 else "",
                "音效": "数字跳出叮" if i == 2 else ("转场唰" if j == sub - 1 else ""),
                "BGM段": bgm[min(i // 2, 2)], "转场": "硬切" if i != 4 else "叠化",
            })
            n += 1
    return rows


def build_scripts(spot):
    """给看板用的轻量预览：两套文案 + 拍摄要点。"""
    return {
        "A": build_script_A(spot),
        "B": build_script_B(spot),
        "points": shooting_points(spot),
    }


def build_index_json(cards, top_n=12, out_dir=None):
    """写 workshop/index.json（供 tts_build 读 segments）。"""
    out_dir = out_dir or os.path.join(HERE, "workshop")
    os.makedirs(out_dir, exist_ok=True)
    items = []
    for c in cards[:top_n]:
        items.append({
            "card_id": c["card_id"], "name": c["name"], "city": c.get("city", ""),
            "score": c.get("score"),
            "A": [{"role": r, "text": t, "dur": d} for r, t, d in build_script_A(c)["segments"]],
            "B": [{"role": r, "text": t, "dur": d} for r, t, d in build_script_B(c)["segments"]],
        })
    path = os.path.join(out_dir, "index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return path


def export_xlsx(cards, top_n=12, out_dir=None):
    """导出前 top_n 张卡的剪辑底稿 xlsx（需 openpyxl；缺失则跳过不报错）。"""
    try:
        from openpyxl import Workbook
    except ImportError:
        print("[workshop] 未安装 openpyxl，跳过 xlsx 导出（看板内仍有文案/底稿预览）")
        return []
    out_dir = out_dir or os.path.join(HERE, "workshop")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for c in cards[:top_n]:
        for mode in ("A", "B"):
            wb = Workbook()
            ws = wb.active
            ws.title = "剪辑底稿"
            cols = ["镜次", "起", "止", "时长", "口播文案", "节奏情绪", "画面类型",
                    "画面素材", "字幕图示", "音效", "BGM段", "转场"]
            ws.append(cols)
            for row in storyboard(c, mode):
                ws.append([row[k] for k in cols])
            # 拍摄要点表
            ws2 = wb.create_sheet("拍摄要点")
            ws2.append(["层级", "拍摄要点"])
            for p in shooting_points(c):
                ws2.append([p["layer"], p["point"]])
            # 文案表
            ws3 = wb.create_sheet("口播文案")
            ws3.append(["段落", "文案", "时长(秒)"])
            sc = build_script_A(c) if mode == "A" else build_script_B(c)
            for r, t, d in sc["segments"]:
                ws3.append([r, t, d])
            fname = f"{c['card_id']}_{mode}.xlsx"
            wb.save(os.path.join(out_dir, fname))
            made.append(fname)
    print(f"[workshop] 导出 {len(made)} 个底稿 xlsx → {out_dir}")
    return made


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    top = args.top
    db = os.path.join(HERE, "travel_db.jsonl")
    if not os.path.exists(db):
        print("[workshop] 无 travel_db.jsonl，先跑 travel_processor.py")
        return 1
    cards = []
    with open(db, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cards.append(json.loads(line))
    cards.sort(key=lambda c: c.get("score", 0), reverse=True)
    build_index_json(cards, top)
    export_xlsx(cards, top)
    print(f"[workshop] 处理 {min(top, len(cards))}/{len(cards)} 张卡")


if __name__ == "__main__":
    main()

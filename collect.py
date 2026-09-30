#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游情报 — 高德 POI 增量采集器（免密钥以外的依赖，仅标准库）
数据源：高德开放平台 Web 服务 POI 关键字搜索（restapi.amap.com/v3/place/text）
流程：查询矩阵(体验关键词 × 城市) → 拉取 → 分类打标签 → 与 travel_db 去重 → 只写新增
用法：
  export AMAP_KEY=你的key
  python3 collect.py --dry-run        # 先看不写
  python3 collect.py                  # 实际采集（增写 raw_YYYYMMDD.json）
  python3 collect.py --limit 10       # 只跑前 10 个查询（调试）
依赖：Python 标准库；key 从环境变量 AMAP_KEY 或同目录 .amap_key 文件读取（均不入库）。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import classify as clf  # noqa: E402

# 自动采集用城市（知名旅游城，控制每日查询量在免费额度内；全国广度靠手动/扩展）
AUTO_CITIES = [
    ("浙江", "杭州"), ("浙江", "绍兴"), ("浙江", "舟山"), ("浙江", "台州"), ("浙江", "丽水"),
    ("江苏", "南京"), ("江苏", "苏州"), ("江苏", "无锡"), ("江苏", "扬州"),
    ("上海", "上海"),
    ("安徽", "黄山"), ("安徽", "池州"),
    ("福建", "厦门"), ("福建", "福州"), ("福建", "武夷山"),
    ("山东", "青岛"), ("山东", "泰安"), ("山东", "烟台"),
    ("海南", "三亚"),
    ("四川", "成都"), ("四川", "乐山"), ("四川", "阿坝"),
    ("云南", "昆明"), ("云南", "大理"), ("云南", "丽江"),
    ("广西", "桂林"), ("广西", "北海"),
    ("湖南", "张家界"), ("湖南", "长沙"),
    ("湖北", "武汉"), ("湖北", "宜昌"), ("湖北", "恩施"),
    ("江西", "九江"), ("江西", "上饶"),
    ("陕西", "西安"),
    ("重庆", "重庆"),
    ("贵州", "黔东南"), ("贵州", "安顺"),
    ("广东", "广州"), ("广东", "深圳"), ("广东", "珠海"),
]

# 每个体验类型对应一个搜索词（高德 text 搜索的关键词）
SEARCH_KEYWORDS = {
    "mountain": "爬山登山",
    "sea": "海滨沙滩",
    "ancient": "古镇古村",
    "park": "主题乐园",
    "food": "美食街小吃",
    "museum": "博物馆",
    "nature": "自然风景区",
    "temple": "寺庙道观",
    "view": "观景台",
}

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def load_key():
    if os.environ.get("AMAP_KEY"):
        return os.environ["AMAP_KEY"].strip()
    p = os.path.join(HERE, ".amap_key")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def build_queries():
    q = []
    for key, kw in SEARCH_KEYWORDS.items():
        for prov, city in AUTO_CITIES:
            q.append((key, kw, prov, city))
    return q


def fetch_pois(keyword, city, key, page=1, offset=25):
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode({
        "keywords": keyword, "city": city, "offset": offset,
        "page": page, "extensions": "all", "key": key,
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with _OPENER.open(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def card_id(spot):
    base = f"{spot.get('name','')}|{spot.get('city','')}|{spot.get('location','')}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:10]


def scan_one(args):
    etype_key, kw, prov, city = args
    key = AMAP_KEY
    try:
        data = fetch_pois(kw, city, key)
    except Exception as e:
        return args, [], f"err:{type(e).__name__}"
    if data.get("status") != "1":
        return args, [], f"api:{data.get('info')}"
    pois = data.get("pois", []) or []
    out = []
    for raw in pois:
        raw["_query_etype"] = etype_key
        raw["_query_city"] = city
        out.append(raw)
    return args, out, "ok"


def main():
    global AMAP_KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    AMAP_KEY = load_key()
    if not AMAP_KEY:
        print("[fatal] 未找到 AMAP_KEY：请 export AMAP_KEY=... 或在 .amap_key 写入（不入库）")
        return 2

    today = datetime.date.today().isoformat()
    queries = build_queries()
    if args.limit:
        queries = queries[:args.limit]

    # 已知集合：travel_db + 今日 raw
    known = set()
    db = os.path.join(HERE, "travel_db.jsonl")
    if os.path.exists(db):
        with open(db, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        known.add(json.loads(line).get("card_id"))
                    except Exception:
                        pass
    raw_path = os.path.join(HERE, f"raw_{today.replace('-', '')}.json")
    existing = []
    if os.path.exists(raw_path):
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            for it in existing:
                known.add(it.get("card_id"))
        except Exception:
            existing = []

    scanned = kept = 0
    new_items = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for (etype_key, kw, prov, city), rows, status in ex.map(scan_one, queries):
            scanned += len(rows)
            if status != "ok":
                continue
            for raw in rows:
                spot = clf.tag_spot(raw)
                spot["card_id"] = card_id(spot)
                if spot["card_id"] in known:
                    continue
                known.add(spot["card_id"])
                kept += 1
                new_items.append(spot)

    if new_items and not args.dry_run:
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(existing + new_items, f, ensure_ascii=False, indent=2)
        action = f"写入 {os.path.basename(raw_path)}（新增 {len(new_items)}）"
    else:
        action = "dry-run" if args.dry_run else "无新增（未写文件）"

    print(f"[collect] 查询 {len(queries)} · 命中POI {scanned} · 新增 {len(new_items)} · {action}")
    for s in new_items[:12]:
        print(f"   + [{s['etype_label']}/{s['hot_tier']}] {s['province']}{s['city']} {s['name']} "
              f"评分{s['rating']} 最佳{clf.MONTH_NAMES[s['best_season'][0]-1] if s['best_season'] else '-'}")
    print("__TRAVEL_SUMMARY__ " + json.dumps(
        {"queries": len(queries), "scanned": scanned, "new": len(new_items),
         "date": today, "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

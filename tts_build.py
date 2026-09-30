#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游情报 · 一键配音（底稿 → 音轨）
复用制造业 app 定稿音色：A 云健 zh-CN-YunjianNeural（一个声音贯穿所有旅游视频）。
数据流：读 workshop/index.json（每张卡含 A/B 口播分段）→ 整段合成 → 输出 mp3 + 文案/timing。

用法（用受管 venv 的 python，系统 python 没装 edge-tts）：
  VPY=/Users/tedwong/.workbuddy/binaries/python/envs/default/bin/python
  $VPY tts_build.py --list                  # 看有哪些卡
  $VPY tts_build.py --card <id> --mode A    # 出单张 A 模式
  $VPY tts_build.py --top 3 --mode B        # 批量出前 3 张 B 模式
  $VPY tts_build.py --all                   # 全部
不传 --voice 即为定稿音色；--voice 仅供试听对比。
"""
import os
import sys
import json
import asyncio

HERE = os.path.dirname(os.path.abspath(__file__))
LOCKED_VOICE = "zh-CN-YunjianNeural"   # A 云健 · 男 · 解说腔（定稿，跨项目统一）
DEFAULT_RATE = "+15%"


def read_index():
    p = os.path.join(HERE, "workshop", "index.json")
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def full_text(card, mode):
    segs = card.get(mode, [])
    # 段间用逗号/句号衔接，保证整段合成句内语调连贯
    parts = []
    for s in segs:
        t = s.get("text", "").strip()
        if t:
            parts.append(t)
    return "。".join(parts) + "。" if parts else ""


def est_timings(card, mode, total_dur):
    """按字数比例估算每段起止（近似，非逐句实测）。"""
    segs = card.get(mode, [])
    chars = [max(1, len(s.get("text", ""))) for s in segs]
    tot = sum(chars)
    out, cur = [], 0.0
    for s, c in zip(segs, chars):
        d = total_dur * (c / tot) if tot else 0
        out.append({"role": s.get("role"), "text": s.get("text"),
                    "start": round(cur, 2), "end": round(cur + d, 2)})
        cur += d
    return out


async def synth(text, voice, rate, out_mp3):
    try:
        import edge_tts
    except ImportError:
        print("[fatal] 未安装 edge-tts：请在受管 venv 跑 $VPY -m pip install edge-tsx")
        return False
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(out_mp3)
    return True


def dur_of_mp3(path):
    """尽量用 ffprobe 取时长，失败则按字数/语速估算。"""
    try:
        import subprocess
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1", path],
                           capture_output=True, text=True, timeout=15)
        v = r.stdout.strip()
        if v:
            return float(v)
    except Exception:
        pass
    # 估算：去掉标点后按 4.5 字/秒（rate +15% 后约 5.2）
    txt = open(path.replace(".mp3", ".txt"), encoding="utf-8").read()
    n = sum(1 for ch in txt if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    return n / 5.0


def process(card, mode, voice, rate):
    out_dir = os.path.join(HERE, "video", "voice")
    os.makedirs(out_dir, exist_ok=True)
    cid = card["card_id"]
    text = full_text(card, mode)
    if not text:
        print(f"  - {cid} {mode} 无文案，跳过")
        return
    mp3 = os.path.join(out_dir, f"{cid}_{mode}.mp3")
    txt = os.path.join(out_dir, f"{cid}_{mode}.txt")
    js = os.path.join(out_dir, f"{cid}_{mode}.json")
    asyncio.run(synth(text, voice, rate, mp3))
    with open(txt, "w", encoding="utf-8") as f:
        f.write(text)
    total = dur_of_mp3(mp3)
    timings = est_timings(card, mode, total)
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"card_id": cid, "mode": mode, "voice": voice, "rate": rate,
                   "duration": round(total, 2), "segments": timings},
                  f, ensure_ascii=False, indent=2)
    print(f"  + {cid} {mode} → {os.path.basename(mp3)} ({total:.1f}s)")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--card")
    ap.add_argument("--mode", default="A", choices=["A", "B"])
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--voice", default=LOCKED_VOICE)
    ap.add_argument("--rate", default=DEFAULT_RATE)
    args = ap.parse_args()

    cards = read_index()
    if args.list:
        for c in cards:
            print(f"  {c['card_id']} {c['name']} {c['city']} 分{c.get('score')}")
        return
    if not cards:
        print("[fatal] workshop/index.json 为空，先跑 workshop.py")
        return

    sel = []
    if args.card:
        sel = [c for c in cards if c["card_id"] == args.card]
    elif args.all:
        sel = cards
    elif args.top:
        sel = cards[:args.top]
    else:
        sel = cards[:1]
    for c in sel:
        process(c, args.mode, args.voice, args.rate)
    print(f"[tts] 完成 {len(sel)} 张 · 模式 {args.mode}")


if __name__ == "__main__":
    main()

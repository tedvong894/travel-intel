# 全国旅游情报

高德 POI 自动采集全国旅游地点 → 分类（体验类型/热度/地区/季节）→ 综合评分 + 原因卡 →
自动生成 A 避坑 / B 感悟 两套短视频文案、12 列剪辑底稿、拍摄要点清单。
复用「长三角制造业情报」app 的同款流水线骨架。

## 核心能力

- **自动/手动采集**：`collect.py` 走高德 Web 服务 POI 关键字搜索（key 走环境变量 `AMAP_KEY` 或 `.amap_key`，不入库）；
  GitHub Actions 每日 08:10 北京自动跑，看板「⟳ 立即刷新」按钮触发云端采集
- **分类**：体验类型（爬山/观海/古镇/美食/博物馆/自然秘境/寺庙/夜景）× 热度（大众/小众，评分+知名度代理）× 地区（省/市）× 季节适配
- **综合评分**：景观价值30 + 性价比25 + 可达性20 + 出片率25 = 百分制，附四维明细与「为什么值得去 / 避坑」原因卡
- **🎬 短视频工坊**：`workshop.py` 自动出 A 避坑 / B 感悟 五段式口播文案 + 12 列剪辑底稿 + 拍摄要点清单，导出 xlsx
- **一键配音**：`tts_build.py` 复用定稿音色 A 云健 `zh-CN-YunjianNeural`（一个声音贯穿所有视频）

## 目录

```
collect.py            高德 POI 增量采集（去重、分类打标签）
classify.py           共享分类与评分规则（城市表/类型映射/季节/评分引擎）
travel_processor.py  算分+原因卡 → travel_db.jsonl → 渲染 index.html
workshop.py           短视频工坊（A/B 文案 + 12列底稿 + 拍摄要点 + xlsx）
tts_build.py          一键配音（读 workshop/index.json）
video-SOP.md          旅游短视频转化 SOP（风格/模板/素材/声音）
raw_YYYYMMDD.json     每日采集原始数据
travel_db.jsonl       累积景点卡（每行一张）
index.html            可视看板（GitHub Pages 入口）
workshop/             底稿 xlsx + index.json
.github/workflows/refresh.yml  每日自动采集+工坊+配音
refresh_via_actions.sh         App 内「立即刷新」触发脚本
push_pages.py          本地发布到 GitHub Pages
```

## 本地运行

```bash
cd travel
export AMAP_KEY=你的高德key          # 或在 .amap_key 写入（不入库）
python3 collect.py --limit 20        # 先看不写；去掉 --limit 跑全量
python3 travel_processor.py          # 算分 + 渲染看板
python3 workshop.py --top 12         # 导出前 12 张底稿 xlsx
python3 tts_build.py --top 6 --mode A  # 配音（需受管 venv 的 edge-tts）
```

> xlsx 导出需 openpyxl；配音需 `python3`（受管 venv）装 edge-tts。两者缺失时看板内仍有文案/底稿预览，不报错。

## 部署

仓库开 GitHub Pages（分支 `main`，根目录 `/`）。每日 08:10 自动采集+工坊+渲染+配音并提交；
手动触发用 `refresh_via_actions.sh` 或 `gh workflow run refresh.yml`。

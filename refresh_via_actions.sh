#!/usr/bin/env bash
# 触发云端采集工作流并等待站点更新（App 内「立即刷新」调用）
# 注意：本机直连 github 需绕过本地代理（与军机处同款处理）
set -e
export no_proxy='*' HTTPS_PROXY= https_proxy= HTTP_PROXY= http_proxy=
REPO="${1:-tedvong894/travel-intel}"
echo "→ 触发 $REPO 的 refresh 工作流…"
gh workflow run refresh.yml --repo "$REPO"
echo "→ 等待运行结束（最长 8 分钟）…"
for i in $(seq 1 40); do
  st=$(gh run list --repo "$REPO" --limit 1 --json status --jq '.[0].status' 2>/dev/null || echo "")
  if [ "$st" = "completed" ] || [ "$st" = "failure" ]; then
    echo "工作流状态：$st"
    break
  fi
  sleep 12
done
echo "→ 完成后 App 自动重载，仅显示新增景点。"

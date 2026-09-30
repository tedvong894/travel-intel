#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旅游情报 — 本地发布到 GitHub Pages（手动用）
逻辑：git add -A → commit → push 到 main（仓库已开 Pages，根目录 /）。
注意：本机直连 github 需绕过本地代理（memory 已记），脚本内自动清代理变量。
用法：python3 push_pages.py "提交说明（可选）"
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    env = dict(os.environ)
    env.update({"no_proxy": "*", "HTTPS_PROXY": "", "https_proxy": "",
                "HTTP_PROXY": "", "http_proxy": ""})
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=HERE, env=env, check=True)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "update: travel intel"
    run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "add", "-A"])
    run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "commit",
         "-m", msg, "--allow-empty"])
    run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "push", "-u", "origin", "main"])


if __name__ == "__main__":
    main()

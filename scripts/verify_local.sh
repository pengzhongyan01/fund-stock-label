#!/usr/bin/env bash
# 本地复现 GitHub Actions 的测试流程，用于生成"本地运行通过"的截图。
#
# 用法：
#   bash scripts/verify_local.sh
#
# 输出的终端结果可直接截图，和 GitHub Actions 页面上的结果是对应的。

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "============================================================"
echo " 本地验证：复现 GitHub Actions 的 CI 流程"
echo " 仓库：$(pwd)"
echo " 时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

echo
echo ">>> [1/5] Python 版本"
$PY --version

echo
echo ">>> [2/5] 安装依赖（pip install -r requirements.txt）"
$PY -m pip install --upgrade pip --quiet
$PY -m pip install -r requirements.txt -r requirements-dev.txt --quiet
echo "依赖安装完成："
$PY -m pip list 2>/dev/null | grep -iE "^(pandas|akshare|pytest) " || true

echo
echo ">>> [3/5] 编译检查（python -m compileall -q fundlab）"
$PY -m compileall -q fundlab
echo "编译检查通过"

echo
echo ">>> [4/5] 单元测试（python -m pytest -q）"
$PY -m pytest -q

echo
echo ">>> [5/5] CLI 可用性（python -m fundlab --help）"
$PY -m fundlab --help | head -20

echo
echo "============================================================"
echo " 全部通过 —— 这份输出可直接作为截图"
echo "============================================================"

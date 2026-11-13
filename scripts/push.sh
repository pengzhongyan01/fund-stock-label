#!/usr/bin/env bash
# 一键关联远程仓库并推送（交互式，按提示输入仓库地址）。
#
# 用法：
#   bash scripts/push.sh
#   bash scripts/push.sh https://github.com/<用户名>/<仓库名>.git

set -euo pipefail

cd "$(dirname "$0")/.."

echo "============================================================"
echo " 推送代码到 GitHub"
echo "============================================================"
echo

REPO_URL="${1:-}"

if [ -z "$REPO_URL" ]; then
    echo "请先在 GitHub 建好空仓库（不要勾 README / .gitignore / license），"
    echo "然后把仓库地址粘贴到这里："
    echo "    https://github.com/<用户名>/<仓库名>.git"
    echo
    read -r -p "仓库地址: " REPO_URL
    echo
fi

# 去掉末尾可能的斜杠和 .git
REPO_URL="${REPO_URL%/}"
REPO_URL="${REPO_URL%.git}"

if ! echo "$REPO_URL" | grep -qE '^https://github\.com/[^/]+/[^/]+$'; then
    echo "✗ 地址格式不对，应该像这样：https://github.com/pengzhongyan01/fund-stock-label.git"
    exit 1
fi

echo "目标仓库：$REPO_URL"
echo

# --- 身份检查 ---
GIT_NAME="$(git config user.name || true)"
GIT_EMAIL="$(git config user.email || true)"
echo "提交身份：${GIT_NAME:-<未配置>} <${GIT_EMAIL:-<未配置>}>"
if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
    echo
    read -r -p "未配置提交身份，请输入 GitHub 用户名: " GIT_NAME
    read -r -p "请输入 GitHub 邮箱: " GIT_EMAIL
    git config user.name "$GIT_NAME"
    git config user.email "$GIT_EMAIL"
    echo "已为本仓库设置身份"
fi
echo

# --- 远程仓库 ---
if git remote get-url origin >/dev/null 2>&1; then
    OLD_URL="$(git remote get-url origin)"
    if [ "$OLD_URL" != "$REPO_URL" ]; then
        echo "检测到已有的 origin：$OLD_URL"
        read -r -p "要改成本次输入的地址吗？(y/N) " ANS
        case "$ANS" in
            [yY]*) git remote set-url origin "$REPO_URL" ;;
            *) echo "保持原地址"; REPO_URL="$OLD_URL" ;;
        esac
    else
        echo "origin 已正确指向：$REPO_URL"
    fi
else
    git remote add origin "$REPO_URL"
    echo "已添加 origin：$REPO_URL"
fi
echo

# --- 状态检查 ---
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠ 有未提交的改动："
    git status --short
    echo
    read -r -p "要先提交这些改动吗？(y/N) " ANS
    case "$ANS" in
        [yY]*)
            read -r -p "提交信息: " MSG
            git add -A
            git commit -m "$MSG"
            echo "已提交"
            ;;
    esac
fi
echo

# --- 推送 ---
git branch -M main
echo ">>> 正在推送（首次会要求登录 GitHub）..."
echo
if git push -u origin main; then
    echo
    echo "============================================================"
    echo " ✓ 推送成功"
    echo "============================================================"
    echo
    echo "下一步："
    echo "  1. 打开 $REPO_URL"
    echo "  2. 点顶部 Actions 标签页，等 1~3 分钟"
    echo "  3. 全部变成绿色对勾后，按 docs/详细操作步骤.md 的阶段四截图"
    echo
else
    echo
    echo "✗ 推送失败。常见原因："
    echo "  · 仓库地址写错 —— 检查上面打印的地址"
    echo "  · 仓库不是空的 —— 删掉远程仓库重建（不要勾 README）"
    echo "  · 没配 Token —— 见 docs/详细操作步骤.md 的步骤 9"
    exit 1
fi

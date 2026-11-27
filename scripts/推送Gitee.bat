@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title 推送到 Gitee

rem ================================================================
rem  推送到 Gitee
rem  认证用 SSH 密钥：%USERPROFILE%\.ssh\id_ed25519_git
rem ================================================================

set "REPO_DIR=%~dp0.."
pushd "%REPO_DIR%"

set "GITEE_USER=peng-zhongyan"
set "REPO_NAME=fund-stock-label"
set "SSH_KEY=%USERPROFILE%\.ssh\id_ed25519_git"

echo.
echo ================================================================
echo   推送到 Gitee
echo ================================================================
echo.
echo   目标：git@gitee.com:%GITEE_USER%/%REPO_NAME%.git
echo.

rem ---------- 检查 SSH 密钥 ----------
if not exist "%SSH_KEY%" (
    echo [x] 找不到 SSH 密钥：%SSH_KEY%
    echo.
    echo 请先生成密钥并添加到 Gitee：
    echo   ssh-keygen -t ed25519 -C "15085958265@163.com"
    echo   然后把 %USERPROFILE%\.ssh\id_ed25519_git.pub 的内容
    echo   粘贴到 https://gitee.com/profile/sshkeys
    pause & popd & exit /b 1
)
echo [OK] SSH 密钥：%SSH_KEY%

rem ---------- 设置 GIT_SSH_COMMAND（用绝对路径，中文用户名下才不出错）----------
set "GIT_SSH_COMMAND=ssh -i ""%SSH_KEY%"" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=""%USERPROFILE%\.ssh\known_hosts"" -o ConnectTimeout=20"
set "GIT_SSH=%GIT_SSH_COMMAND%"
echo [OK] 已配置 SSH 连接参数
echo.

rem ---------- 测试连接 ----------
echo [i] 测试与 Gitee 的连接...
ssh -i "%SSH_KEY%" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="%USERPROFILE%\.ssh\known_hosts" -o ConnectTimeout=20 -T git@gitee.com 2>&1 | findstr /i "successfully authenticated"
if errorlevel 1 (
    echo [x] SSH 认证失败。
    echo     请确认公钥已添加到 https://gitee.com/profile/sshkeys
    pause & popd & exit /b 1
)
echo.

rem ---------- 确认远端仓库存在 ----------
set "REMOTE_URL=git@gitee.com:%GITEE_USER%/%REPO_NAME%.git"
git ls-remote --heads "%REMOTE_URL%" >nul 2>&1
if errorlevel 1 (
    echo [x] Gitee 上还没有仓库 %GITEE_USER%/%REPO_NAME%
    echo.
    echo 请先在浏览器里创建（30 秒）：
    echo   https://gitee.com/projects/new
    echo.
    echo   仓库名称填：%REPO_NAME%
    echo   路径 / 归属  填：%GITEE_USER%
    echo   仓库属性：选择「私有」或「公开」都可以
    echo   [重要] 不要勾选「使用 Readme 文件初始化这个仓库」
    echo.
    pause & popd & exit /b 1
)
echo [OK] 远端仓库已存在

rem ---------- 关联远程 ----------
git remote remove gitee 2>nul
git remote add gitee "%REMOTE_URL%"
echo [OK] 已设置 gitee 远程
echo.

rem ---------- 推送 ----------
echo [i] 正在推送...
echo.
git push -u gitee main
if errorlevel 1 (
    echo.
    echo [x] 推送失败。
    echo.
    pause & popd & exit /b 1
)

echo.
echo ================================================================
echo   推送成功
echo ================================================================
echo.
echo   仓库地址：https://gitee.com/%GITEE_USER%/%REPO_NAME%
echo.
echo   下一步：
echo     1. 打开上面的地址确认代码都在
echo     2. Gitee 没有自带 GitHub Actions 那样的 CI，
echo        但可以用「Gitee Go」或「流水线」手动配置，
echo        本地验证用 scripts\作业助手.bat 选 1
echo.
pause
popd
exit /b 0

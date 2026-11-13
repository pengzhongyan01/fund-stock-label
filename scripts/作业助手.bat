@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title 作业助手 - 基金持仓与股票市值标签化

rem ================================================================
rem  《代码阅读及调试》作业助手
rem    1 = 本地验证（复现 GitHub Actions，输出可直接截图）
rem    2 = 推送到 GitHub
rem
rem  不依赖 Git Bash / WSL，双击即可运行。
rem  会自动挑选装了依赖的 Python（你机器上有好几个 python）。
rem ================================================================

set "REPO_DIR=%~dp0.."
pushd "%REPO_DIR%"

echo.
echo ================================================================
echo   作业助手
echo   项目目录：%CD%
echo ================================================================
echo.

rem ================================================================
rem  选 Python
rem ================================================================
set "PY="
set "PYVER="

if defined FUNDLAB_PYTHON if exist "%FUNDLAB_PYTHON%" set "PY=%FUNDLAB_PYTHON%"

if not defined PY call :try_candidate "%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not defined PY call :try_launcher 3.13
if not defined PY call :try_launcher 3.12
if not defined PY call :try_launcher 3.11
if not defined PY call :try_path

if not defined PY (
    echo [x] 没找到可用的 Python
    echo.
    echo 解决办法（任选其一）：
    echo   A. 装一个标准 Python：https://www.python.org/downloads/
    echo      安装时勾选 "Add Python to PATH"，然后重新运行本文件
    echo   B. 在本文件所在目录新建 venv：
    echo      py -3.12 -m venv .venv
    echo      .venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
    echo      然后设置环境变量 FUNDLAB_PYTHON 指向 .venv\Scripts\python.exe
    echo.
    pause & popd & exit /b 1
)

rem 依赖是否齐全？
"%PY%" -c "import pandas, akshare, pytest" >nul 2>&1
if errorlevel 1 (
    echo [i] 当前 Python 缺依赖，正在安装（首次约 1-2 分钟）...
    "%PY%" -m pip install --upgrade pip --quiet
    "%PY%" -m pip install -r requirements.txt -r requirements-dev.txt
    if errorlevel 1 (
        echo [x] 依赖安装失败，请检查网络
        pause & popd & exit /b 1
    )
)

for /f "tokens=*" %%i in ('"%PY%" -c "import sys;print(sys.version.split()[0])"') do set "PYVER=%%i"
echo [OK] Python !PYVER!  -^>  %PY%
echo.

choice /c 12 /n /m "  请选择  [1]=本地验证（可截图）  [2]=推送到 GitHub  [Q]=退出 : "
if errorlevel 3 goto :end
if errorlevel 2 goto :push
goto :verify

rem ================================================================
rem  子过程：尝试一个候选 Python
rem ================================================================
:try_candidate
if defined PY goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import pandas, akshare, pytest" >nul 2>&1
if errorlevel 1 goto :eof
set "PY=%~1"
goto :eof

:try_launcher
if defined PY goto :eof
for /f "tokens=*" %%i in ('py -%~1 -c "import sys;print(sys.executable)" 2^>nul') do (
    if not defined PY call :try_candidate "%%i"
)
goto :eof

:try_path
if defined PY goto :eof
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    if not defined PY (
        echo %%i | findstr /i "WindowsApps" >nul || call :try_candidate "%%i"
    )
)
goto :eof

rem ================================================================
:verify
echo.
echo ================================================================
echo   本地验证：复现 GitHub Actions 的 CI 流程
echo ================================================================
echo.
echo   [1/5] Python 版本
"%PY%" --version
echo.
echo   [2/5] 安装依赖
"%PY%" -m pip install -r requirements.txt -r requirements-dev.txt --quiet
"%PY%" -m pip list 2>nul | findstr /i /r "^pandas ^akshare ^pytest"
echo.
echo   [3/5] 编译检查
"%PY%" -m compileall -q fundlab
if errorlevel 1 ( echo [x] 编译失败 & pause & popd & exit /b 1 )
echo   编译通过
echo.
echo   [4/5] 单元测试
"%PY%" -m pytest -q
if errorlevel 1 ( echo [x] 测试失败 & pause & popd & exit /b 1 )
echo.
echo   [5/5] 命令行入口
"%PY%" -m fundlab --help
echo.
echo ================================================================
echo   全部通过 —— 这份输出可直接作为截图
echo ================================================================
echo.
pause
popd
exit /b 0

rem ================================================================
:push
echo.
echo ================================================================
echo   推送到 GitHub
echo ================================================================
echo.

for /f "tokens=*" %%i in ('git config user.name') do set "GIT_NAME=%%i"
for /f "tokens=*" %%i in ('git config user.email') do set "GIT_EMAIL=%%i"
echo   提交身份：!GIT_NAME! ^<!GIT_EMAIL!^!
if "!GIT_NAME!"=="" (
    echo.
    set /p "GIT_NAME=请输入你的 GitHub 用户名: "
    set /p "GIT_EMAIL=请输入你的 GitHub 邮箱: "
    git config user.name "!GIT_NAME!"
    git config user.email "!GIT_EMAIL!"
    echo   已设置
)
echo.

git status --porcelain > "%TEMP%\_fl_status.txt"
for /f "usebackq delims=" %%i in ("%TEMP%\_fl_status.txt") do set "HASCHG=1"
if defined HASCHG (
    echo   检测到未提交的改动：
    git status --short
    echo.
    set /p "ANS=要先提交它们吗？(y/N) "
    if /i "!ANS!"=="y" (
        set /p "MSG=请输入提交信息: "
        git add -A
        git commit -m "!MSG!"
        echo   已提交
        echo.
    )
    set HASCHG=
)

echo   请先在 GitHub 建一个空仓库：
echo       https://github.com/new
echo     [重要] 不要勾选 Add a README file / .gitignore / license
echo.
set /p "REPO_URL=粘贴仓库地址（如 https://github.com/用户名/仓库名.git）: "
if "!REPO_URL!"=="" ( echo [x] 没输入地址，已取消 & pause & popd & exit /b 1 )

set "CLEAN=!REPO_URL:/=!"
if "!CLEAN:~-4!"==".git" set "CLEAN=!CLEAN:~0,-4!"
echo "!CLEAN!" | findstr /r /c:"^https://github.com/[^/]*/[^/]*$" >nul
if errorlevel 1 (
    echo [x] 地址格式不对，应该像：https://github.com/用户名/仓库名.git
    pause & popd & exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin "!CLEAN!"
    echo   已添加 origin：!CLEAN!
) else (
    for /f "tokens=*" %%i in ('git remote get-url origin') do set "OLDURL=%%i"
    if "!OLDURL!"=="!CLEAN!" (
        echo   origin 已正确
    ) else (
        echo   当前 origin：!OLDURL!
        set /p "ANS=要改成 !CLEAN! 吗？(y/N) "
        if /i "!ANS!"=="y" ( git remote set-url origin "!CLEAN!" & echo   已更新 ) else ( set "CLEAN=!OLDURL!" )
    )
)
echo.

git branch -M main
echo   正在推送（首次会弹出 GitHub 登录窗口，点 Authorize git）...
echo.
git push -u origin main
if errorlevel 1 (
    echo.
    echo [x] 推送失败。可能原因：
    echo     1. 仓库地址写错
    echo     2. 远程仓库不是空的（删掉重建，别勾 README）
    echo     3. 没配 Token：https://github.com/settings/tokens/new  （勾 repo 权限）
    echo.
    pause & popd & exit /b 1
)

echo.
echo ================================================================
echo   推送成功
echo ================================================================
echo.
echo   下一步：
echo     1. 浏览器打开 !CLEAN!
echo     2. 点顶部 Actions 标签页
echo     3. 等 1~3 分钟，全部变成绿色对勾
echo     4. 按 docs\详细操作步骤.md 的「阶段四」截图
echo.
pause
popd
exit /b 0

:end
popd
exit /b 0

@echo off
chcp 65001 > nul
title 打开本项目（VS Code）
start "" "D:\前端工具\Microsoft VS Code\Code.exe" "%~dp0"
exit /b 0

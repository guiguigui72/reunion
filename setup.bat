@echo off
chcp 65001 >nul
title 重逢 — 安装与启动

echo.
echo ╔══════════════════════════════════╗
echo ║       重逢 — AI 数字亲人          ║
echo ║     安装与一键启动脚本             ║
echo ╚══════════════════════════════════╝
echo.

:: ==========================================
:: Step 1: Check Python
:: ==========================================
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址：https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo.

:: ==========================================
:: Step 2: Install Python dependencies
:: ==========================================
echo [2/4] 安装 Python 依赖...
pip install -r backend\requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] Python 依赖安装失败，请检查网络连接后重试
    pause
    exit /b 1
)
echo Python 依赖安装完成
echo.

:: ==========================================
:: Step 3: Install Node.js dependencies
:: ==========================================
echo [3/4] 检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 22+
    echo 下载地址：https://nodejs.org/
    pause
    exit /b 1
)
node --version

echo 安装 Node.js 依赖...
call npm install
if %errorlevel% neq 0 (
    echo [错误] Node.js 依赖安装失败，请检查网络连接后重试
    pause
    exit /b 1
)
echo Node.js 依赖安装完成
echo.

:: ==========================================
:: Step 4: Start
:: ==========================================
echo [4/4] 启动重逢...
echo.
echo Electron 窗口即将打开...
echo 关闭此窗口或 Electron 窗口即可退出程序。
echo.
call npm run electron:dev

exit /b 0

@echo off
chcp 65001 >nul
echo ========================================
echo   IT管理部智能助手 - 一键启动
echo ========================================
echo.

set REPO_URL=https://github.com/chungkung/dingtalk-robot.git
set LOCAL_DIR=%USERPROFILE%\dingtalk-robot

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

if exist "%LOCAL_DIR%" (
    echo [1/4] 发现已有代码，检查更新...
    cd /d "%LOCAL_DIR%"
    git pull origin master >nul 2>&1
    echo [完成] 代码已更新
) else (
    echo [1/4] 正在从GitHub下载代码...
    cd /d %USERPROFILE%
    git clone %REPO_URL% dingtalk-robot
    cd /d "%LOCAL_DIR%"
)

echo [2/4] 安装依赖...
pip install -q flask werkzeug requests jieba duckduckgo-search lxml

echo [3/4] 检查natapp隧道...
echo.
echo 注意：确保natapp隧道正在运行！
echo.

echo [4/4] 启动服务...
echo.
echo ========================================
echo   服务启动成功！
echo   保持此窗口开启，机器人即可正常工作
echo ========================================
echo.
python -m src.app
pause

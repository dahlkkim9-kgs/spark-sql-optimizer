@echo off
REM =============================================
REM Spark SQL 优化工具 - 开发环境启动脚本
REM =============================================

echo.
echo ============================================
echo Spark SQL 优化工具 - 启动后端服务 (auto-reload)
echo ============================================
echo.
echo 端口: 8889
echo 模式: 开发 (代码变更自动重载)
echo.

cd /d "%~dp0backend"

REM 检查端口是否被占用，如果被占用则先关闭旧进程
netstat -ano | findstr ":8889.*LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo [提示] 端口 8889 已被占用，正在关闭旧进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8889.*LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    echo [完成] 旧进程已关闭
    echo.
)

echo [启动] FastAPI 后端服务 (带自动重载)...
python -m uvicorn api.main:app --host 127.0.0.1 --port 8889 --reload --reload-dir .

pause

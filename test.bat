@echo off
chcp 65001 >nul
echo =========================================
echo   Spark SQL 优化工具 - 快速测试模式
echo =========================================
echo.
echo 此脚本将同时启动：
echo   1. 后端 API (端口 8000)
echo   2. 前端开发服务器 (端口 3000)
echo.
echo 启动后在浏览器访问: http://localhost:3000
echo 按 Ctrl+C 停止所有服务
echo =========================================
echo.

REM 启动后端
echo [1/2] 启动后端...
start "Spark-SQL-Backend" cmd /k "cd backend && python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo [2/2] 启动前端...
start "Spark-SQL-Frontend" cmd /k "cd frontend && npm start"

echo.
echo ✅ 服务启动中...
echo.
echo 前端地址: http://localhost:3000
echo 后端文档: http://localhost:8000/docs
echo.
echo 关闭此窗口不会停止服务，请关闭各个服务窗口来停止
echo.
pause

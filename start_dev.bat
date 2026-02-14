@echo off
chcp 65001 >nul
echo ========================================
echo   Spark SQL 优化工具 - 开发环境启动
echo ========================================
echo.

:: 启动后端API服务
echo [1/2] 启动后端API服务...
cd backend
start "Spark SQL Backend" cmd /k "python -m api.main"
cd ..
timeout /t 3 /nobreak >nul

:: 启动前端开发服务器
echo [2/2] 启动前端开发服务器...
cd frontend
start "Spark SQL Frontend" cmd /k "npm start"
cd ..

echo.
echo ========================================
echo   启动完成！
echo   后端地址: http://localhost:8888
echo   前端地址: http://localhost:3000
echo ========================================
echo.
echo 请等待服务启动完成（约10-15秒）
echo 前端会自动打开浏览器
echo.
pause

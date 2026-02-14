@echo off
chcp 65001 >nul
echo =========================================
echo   Spark SQL 优化工具 - Windows 启动脚本
echo =========================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3
    pause
    exit /b 1
)

echo ✅ Python:
python --version

REM 检查Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Node.js
    echo 请先安装 Node.js
    pause
    exit /b 1
)

echo ✅ Node.js:
node --version

echo.
echo =========================================
echo   安装依赖
echo =========================================

REM 安装前端依赖
if exist "frontend" (
    echo 📦 安装前端依赖...
    cd frontend
    call npm install
    cd ..
)

REM 安装后端依赖
if exist "backend" (
    echo 📦 安装后端依赖...
    cd backend
    python -m pip install -r requirements.txt
    cd ..
)

REM 安装Electron依赖
echo 📦 安装Electron依赖...
call npm install

echo.
echo =========================================
echo   安装完成！
echo =========================================
echo.
echo 启动方式：
echo   开发模式: npm start
echo   打包Windows: npm run build:win
echo.
pause

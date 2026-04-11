@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Spark SQL 优化工具 - 一键构建
echo ========================================
echo.

REM Step 1: 构建前端
echo [1/3] 构建前端...
cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 (
    echo 前端构建失败！
    pause
    exit /b 1
)
echo 前端构建完成。
echo.

REM Step 2: PyInstaller 打包
echo [2/3] PyInstaller 打包...
cd /d "%~dp0backend"
pyinstaller backend.spec --noconfirm
if errorlevel 1 (
    echo PyInstaller 打包失败！
    pause
    exit /b 1
)
echo 打包完成。
echo.

REM Step 3: 完成
echo [3/3] 构建完成！
echo.
echo 输出目录: %~dp0backend\dist\
echo 可执行文件: spark-sql-backend.exe
echo.
echo 使用方法：双击 spark-sql-backend.exe 即可启动
echo.
pause

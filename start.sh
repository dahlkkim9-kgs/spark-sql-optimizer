#!/bin/bash

echo "========================================="
echo "  Spark SQL 优化工具 - 启动脚本"
echo "========================================="

# 检查Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3"
    exit 1
fi

echo "✅ Python 3: $(python3 --version)"

# 检查Node.js (Electron需要)
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js"
    echo "Electron需要Node.js，请先安装"
    exit 1
fi

echo "✅ Node.js: $(node --version)"

# 安装依赖
echo ""
echo "========================================="
echo "  安装依赖"
echo "========================================="

# 安装前端依赖
if [ -d "frontend" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 安装后端依赖
if [ -d "backend" ]; then
    echo "📦 安装后端依赖..."
    cd backend
    pip3 install -r requirements.txt
    cd ..
fi

# 安装Electron依赖
echo "📦 安装Electron依赖..."
npm install

echo ""
echo "========================================="
echo "  安装完成！"
echo "========================================="
echo ""
echo "启动方式："
echo "  开发模式: npm run start"
echo "  打包Windows: npm run build:win"
echo "  打包Mac: npm run build:mac"
echo "  打包Linux: npm run build:linux"

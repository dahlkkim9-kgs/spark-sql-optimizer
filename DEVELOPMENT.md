# Spark SQL 优化工具 - 开发指南

## 快速开始

### 1. 环境要求

```bash
# Python 3.9+
python3 --version  # 应该显示 3.9.x

# Node.js 18+
node --version      # 应该显示 v18.x.x

# npm
npm --version       # 应该显示 9.x.x
```

### 2. 安装依赖

```bash
# 运行启动脚本（推荐）
bash start.sh

# 或者手动安装
cd frontend && npm install && cd ..
cd backend && pip3 install -r requirements.txt && cd ..
npm install
```

### 3. 开发模式启动

```bash
# 启动应用（会自动启动前后端和Electron）
npm start
```

## 项目结构

```
spark-sql-optimizer/
├── frontend/              # React前端
│   ├── src/
│   │   ├── App.tsx      # 主应用组件
│   │   ├── App.css      # 样式文件
│   │   └── index.tsx    # 入口文件
│   ├── public/
│   │   └── index.html   # HTML模板
│   └── package.json
│
├── backend/               # Python后端
│   ├── api/
│   │   └── main.py       # FastAPI主应用
│   ├── core/
│   │   └── analyzer.py   # SQL分析器
│   └── requirements.txt
│
├── electron/              # Electron配置
│   ├── main.js           # 主进程
│   └── preload.js        # 预加载脚本
│
├── resources/            # 资源文件
│   └── rules/
│
└── package.json          # 主配置文件
```

## 开发流程

### 前端开发

```bash
cd frontend
npm start
# 访问 http://localhost:3000
```

### 后端开发

```bash
cd backend
python3 -m uvicorn api.main:app --reload
# API文档: http://localhost:8000/docs
```

### 添加新的优化规则

在 `backend/core/analyzer.py` 的 `_init_rules` 方法中添加：

```python
{
    "name": "RULE_NAME",
    "severity": "HIGH|MEDIUM|LOW",
    "pattern": r"正则表达式",
    "message": "问题描述",
    "suggestion": "优化建议",
    "rewrite": self._rewrite_function  # 可选
}
```

### 添加新的API接口

在 `backend/api/main.py` 中添加：

```python
@app.post("/your-endpoint")
def your_function():
    # 实现逻辑
    pass
```

## 构建和打包

### 开发构建

```bash
# 构建前端
cd frontend
npm run build
cd ..
```

### 打包桌面应用

```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux
```

打包完成后，安装文件在 `dist/` 目录。

## 调试技巧

### 前端调试

1. 在Electron中按 `F12` 打开开发者工具
2. 查看Console日志和Network请求
3. 使用React Developer Tools调试组件

### 后端调试

1. 查看终端输出的日志
2. API文档: http://localhost:8000/docs
3. 使用 `print()` 语句调试

### Electron调试

1. 启动时会自动打开DevTools（开发模式）
2. 查看主进程和渲染进程的日志

## 常见问题

### Python 3未找到

```bash
# 确保Python 3已安装
python3 --version

# 检查PATH
which python3
```

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000  # 8000端口

# 杀死进程
kill -9 <PID>
```

### Electron无法启动

```bash
# 检查Node.js版本
node --version

# 重新安装依赖
rm -rf node_modules package-lock.json
npm install
```

## 离线部署

### 内网环境部署

1. 在开发机上打包应用
2. 将 `dist/` 目录复制到内网机器
3. 直接运行安装文件

### 内网数据源连接

如果需要连接内网Hive/Spark，需要：

1. 安装相应Python依赖
2. 配置连接信息
3. 修改 `backend/connectors/` 中的连接器

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交变更
4. 发起Pull Request

## 许可证

MIT License - 详见 LICENSE 文件

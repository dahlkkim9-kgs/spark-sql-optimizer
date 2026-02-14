# Spark SQL 优化工具 - 项目结构说明

## 📁 目录结构

```
spark-sql-optimizer/
│
├── 📄 README.md                    # 项目说明
├── 📄 DEVELOPMENT.md               # 开发指南
├── 📄 PROJECT_STRUCTURE.md          # 本文件
├── 📄 start.sh                     # 启动脚本
│
├── 📁 frontend/                    # React前端
│   ├── 📄 package.json
│   ├── 📁 public/
│   │   └── 📄 index.html
│   └── 📁 src/
│       ├── 📄 App.tsx             # 主应用组件
│       ├── 📄 App.css             # 样式文件
│       └── 📄 index.tsx           # 入口文件
│
├── 📁 backend/                    # Python后端
│   ├── 📄 requirements.txt         # Python依赖
│   ├── 📁 api/
│   │   └── 📄 main.py             # FastAPI主应用
│   └── 📁 core/
│       └── 📄 analyzer.py         # SQL分析器核心
│
├── 📁 electron/                    # Electron桌面应用
│   ├── 📄 main.js                 # 主进程
│   └── 📄 preload.js              # 预加载脚本
│
├── 📁 resources/                  # 资源文件
│   └── 📁 rules/
│       └── 📄 rule_library.md     # 规则库文档
│
├── 📁 config/                     # 配置文件
│
├── 📁 dist/                        # 打包输出
│
├── 📄 package.json                # Electron主配置
│
└── 📁 logs/                        # 日志文件
```

## 📦 核心文件说明

### 前端

| 文件 | 说明 |
|------|------|
| `App.tsx` | 主应用组件，包含编辑器和分析结果展示 |
| `App.css` | 样式文件，定义UI样式 |
| `index.tsx` | React入口文件 |
| `index.html` | HTML模板 |
| `package.json` | 前端依赖配置 |

### 后端

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI主应用，定义REST API接口 |
| `analyzer.py` | SQL静态分析器，包含所有优化规则 |
| `requirements.txt` | Python依赖列表 |

### Electron

| 文件 | 说明 |
|------|------|
| `main.js` | Electron主进程，管理窗口和后端进程 |
| `preload.js` | 预加载脚本，暴露安全API给渲染进程 |

## 🚀 快速启动

### 开发模式

```bash
# 1. 安装依赖
bash start.sh

# 2. 启动应用
npm start
```

### 构建打包

```bash
# Windows
npm run build:win

# Linux
npm run build:linux

# macOS
npm run build:mac
```

## 🔧 下一步开发

1. **添加新规则**: 编辑 `backend/core/analyzer.py`
2. **修改UI**: 编辑 `frontend/src/App.tsx`
3. **添加API**: 编辑 `backend/api/main.py`

详细开发指南请查看 `DEVELOPMENT.md`

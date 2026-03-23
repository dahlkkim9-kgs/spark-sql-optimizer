# Spark SQL 优化工具

基于Electron + Python的离线Spark SQL静态分析和优化工具。

## 功能特性

- 🔍 SQL静态分析，检测性能问题
- 📝 智能SQL重写建议
- 📊 生成优化报告
- 🔧 自定义优化规则
- 📁 批量文件分析
- 🔗 连接内网Hive Metastore（可选）

## 技术栈

- **前端**: React + Monaco Editor
- **后端**: Python (FastAPI)
- **桌面框架**: Electron
- **SQL解析**: SqlGlot

## 目录结构

```
spark-sql-optimizer/
├── frontend/          # React前端
├── backend/           # Python后端
├── electron/           # Electron配置
├── resources/         # 资源文件
├── config/            # 配置文件
├── dist/              # 打包输出
└── logs/              # 日志文件
```

## 开发指南

### 前端开发

```bash
cd frontend
npm install
npm start
```

### 后端开发

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8889
```

### Electron开发

```bash
npm run dev
```

### 打包

```bash
npm run build:win    # Windows
npm run build:mac    # macOS
npm run build:linux  # Linux
```

## 许可证

MIT License

# Windows 本地测试指南

## 快速开始

### 方法一：一键安装并测试

1. 双击运行 `start.bat` 安装所有依赖
2. 双击运行 `test.bat` 启动测试服务
3. 浏览器访问 http://localhost:3000

### 方法二：手动测试步骤

```cmd
# 1. 安装前端依赖
cd frontend
npm install
cd ..

# 2. 安装后端依赖
cd backend
python -m pip install -r requirements.txt
cd ..

# 3. 安装 Electron 依赖
npm install
```

## 测试模式

### 开发模式（推荐用于调试）

双击 `test.bat` 或手动执行：

```cmd
# 终端1 - 启动后端
cd backend
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# 终端2 - 启动前端
cd frontend
npm start
```

访问：
- 前端：http://localhost:3000
- 后端 API 文档：http://localhost:8000/docs

### Electron 桌面模式

```cmd
# 先构建前端
cd frontend
npm run build
cd ..

# 启动 Electron
npm start
```

## 测试 SQL 示例

复制以下 SQL 到编辑器进行测试：

```sql
-- 测试 SELECT * 规则
SELECT * FROM users WHERE status = 'active';

-- 测试 CROSS JOIN 规则
SELECT * FROM table1 CROSS JOIN table2;

-- 测试 LIKE 通配符规则
SELECT * FROM users WHERE name LIKE '%john%';

-- 测试 OR 条件规则
SELECT * FROM orders WHERE status = 'A' OR status = 'B' OR status = 'C';

-- 测试 JOIN 无条件规则
SELECT * FROM table1 JOIN table2;
```

## 环境要求

- Windows 10/11
- Python 3.9+
- Node.js 18+
- npm 9+

## 常见问题

### 端口被占用

```cmd
# 查看 8000 端口
netstat -ano | findstr :8000

# 查看进程
tasklist | findstr <PID>

# 结束进程
taskkill /PID <PID> /F
```

### Python 模块安装失败

使用清华镜像源：

```cmd
cd backend
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### npm 安装失败

使用淘宝镜像源：

```cmd
npm config set registry https://registry.npmmirror.com
npm install
```

## 项目结构

```
spark-sql-optimizer/
├── frontend/          # React 前端 (端口 3000)
├── backend/           # Python 后端 (端口 8000)
├── electron/          # Electron 桌面应用
├── start.bat          # Windows 安装脚本
└── test.bat           # Windows 测试脚本
```

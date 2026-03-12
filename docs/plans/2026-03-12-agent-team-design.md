# 全栈开发智能体团队设计文档

**创建日期**: 2026-03-12
**项目**: Spark SQL 优化工具
**设计目标**: 构建基于 LangChain 的全栈开发智能体团队

---

## 1. 概述

### 1.1 目标
为现有的 Spark SQL 优化工具添加一个智能体团队系统，通过多个专业智能体的协作，提供 SQL 优化、前端优化、后端优化的全栈开发辅助能力。

### 1.2 设计原则
- **非侵入式**: 不破坏原有项目结构，仅新增功能模块
- **建议式**: 智能体提供建议，由用户决定是否采纳
- **可扩展**: 易于添加新的智能体角色
- **可测试**: 完整的测试覆盖

---

## 2. 架构设计

### 2.1 整体架构

```
用户输入 (任务)
       ↓
主协调器 (AgentCoordinator)
       ↓
   ┌────┴────┬────────┐
   ↓         ↓        ↓
SQL团队   前端团队   后端团队
   └────┬────┬────────┘
        ↓    ↓
    测试工程师
        ↓
    结果汇总
```

### 2.2 智能体角色

| 角色 | 职责 | 技术栈 |
|------|------|--------|
| 主协调器 | 任务路由、结果汇总 | LangChain |
| SQL 格式化专家 | SQL 语句格式化 | formatter_v4_fixed.py |
| SQL 语法验证器 | SQL 语法检查 | sqlparse |
| SQL 性能分析师 | 执行计划分析、优化建议 | spark-sql |
| 前端优化专家 | React/TS 代码优化 | React, TypeScript |
| UI/UX 专家 | 界面改进建议 | CSS, HTML |
| 后端优化专家 | Python/FastAPI 优化 | Python, FastAPI |
| API 设计师 | API 结构优化 | OpenAPI |
| 测试工程师 | 跨层测试 | pytest, jest |

---

## 3. 数据流与状态管理

### 3.1 状态定义

```python
class AgentState(TypedDict):
    input: str              # 用户输入
    task_type: str          # 任务类型: "sql" | "frontend" | "backend"
    sql_result: dict        # SQL 团队输出
    frontend_result: dict   # 前端团队输出
    backend_result: dict    # 后端团队输出
    test_results: dict      # 测试结果
    errors: list[str]       # 错误收集
    step: str               # 当前步骤
```

### 3.2 工作流定义

使用 LangGraph 定义状态图：
- 入口点: coordinator
- 条件路由: 根据 task_type 分流到对应团队
- 汇聚点: tester
- 终点: END

---

## 4. 错误处理与重试机制

### 4.1 重试策略
- 每个智能体最多重试 2 次
- 记录每次失败的错误信息
- 失败后继续执行下游智能体

### 4.2 错误恢复

| 场景 | 处理方式 |
|------|----------|
| 智能体执行失败 | 重试 2 次，记录错误，继续执行 |
| SQL 语法错误 | 返回具体错误位置，格式化专家跳过 |
| 前端组件不存在 | 返回文件列表，让用户选择 |
| 测试全部失败 | 回滚更改，返回原始输入 |
| API 超时 | 使用默认值，记录警告 |

### 4.3 状态快照与回滚

```python
class StateSnapshot:
    def save(state: AgentState)
    def rollback(steps: int) -> AgentState
```

---

## 5. 测试策略

### 5.1 测试层级

```
端到端测试
    ├── 完整工作流: 用户输入 → 最终输出
集成测试
    ├── 智能体间协作: 协调器 → 团队 → 测试
单元测试
    ├── 每个智能体独立功能
```

### 5.2 测试文件

- `backend/tests/test_agents.py` - 智能体团队集成测试
- `backend/tests/agents/test_syntax_agent.py` - 语法验证器单元测试
- `backend/tests/agents/test_format_agent.py` - 格式化专家单元测试
- `backend/tests/agents/test_frontend_agent.py` - 前端优化专家单元测试

---

## 6. API 接口设计

### 6.1 新增端点

```
POST /api/agent/execute
```

### 6.2 请求/响应

```python
class AgentRequest(BaseModel):
    input: str
    task_type: str  # "sql" | "frontend" | "backend"

class AgentResponse(BaseModel):
    result: dict
    errors: list[str]
    execution_time: float
```

### 6.3 前端集成

```typescript
interface AgentRequest {
  input: string;
  taskType: 'sql' | 'frontend' | 'backend';
}

async function executeAgent(request: AgentRequest): Promise<AgentResponse>
```

---

## 7. 文件结构

```
backend/
├── agents/
│   ├── __init__.py
│   ├── coordinator.py      # 主协调器
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── syntax_agent.py      # 语法验证器
│   │   ├── format_agent.py      # 格式化专家
│   │   ├── performance_agent.py  # 性能分析师
│   │   ├── frontend_agent.py    # 前端优化专家
│   │   ├── ux_agent.py          # UI/UX 专家
│   │   ├── backend_agent.py     # 后端优化专家
│   │   ├── api_agent.py         # API 设计师
│   │   └── test_agent.py        # 测试工程师
│   ├── graph.py             # LangGraph 工作流定义
│   └── state.py             # 状态定义
├── core/
│   └── formatter_v4_fixed.py    # 现有格式化器（不变）
└── tests/
    ├── test_agents.py           # 智能体集成测试
    └── agents/                  # 智能体单元测试
```

---

## 8. 依赖项

### 8.1 新增 Python 包

```
langchain>=0.1.0
langgraph>=0.0.20
sqlparse>=0.4.4
```

### 8.2 安装命令

```bash
pip install langchain langgraph sqlparse
```

---

## 9. 实施计划

详细的实施计划将由 `writing-plans` 技能生成。

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LangChain 版本兼容性问题 | 中 | 固定版本号，充分测试 |
| 智能体执行超时 | 低 | 设置超时限制，提供默认返回 |
| API 响应过大 | 低 | 实现分页或流式响应 |
| 测试覆盖不足 | 中 | 优先编写测试，TDD 方式开发 |

---

## 附录

### A. 使用示例

```typescript
// 优化前端组件
const result = await executeAgent({
  input: "优化 App.tsx 的加载性能",
  taskType: "frontend"
});

console.log(result.suggestions);
console.log(result.generated_code);
```

### B. 扩展指南

添加新智能体：
1. 在 `agents/agents/` 创建新文件
2. 继承 `BaseAgent` 类
3. 实现 `execute()` 方法
4. 在 `graph.py` 中注册

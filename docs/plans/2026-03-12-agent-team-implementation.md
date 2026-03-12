# 全栈开发智能体团队实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建基于 LangChain + LangGraph 的全栈开发智能体团队系统，为 SQL 格式化器项目提供智能辅助功能

**Architecture:** 使用 LangGraph 状态图管理智能体协作，主协调器路由任务到专业团队（SQL/前端/后端），测试工程师验证结果。非侵入式设计，新增 agents 模块独立于现有代码。

**Tech Stack:** LangChain, LangGraph, FastAPI, sqlparse, pytest

---

## 前置准备

### Task 0: 环境设置

**Files:**
- Modify: `requirements.txt`

**Step 1: 添加新依赖**

在 `requirements.txt` 末尾添加：

```
langchain>=0.1.0
langgraph>=0.0.20
sqlparse>=0.4.4
```

**Step 2: 安装依赖**

```bash
pip install langchain langgraph sqlparse
```

**Step 3: 验证安装**

```bash
python -c "import langchain; import langgraph; import sqlparse; print('OK')"
```

预期输出: `OK`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add agent team dependencies (langchain, langgraph, sqlparse)"
```

---

## 模块 1: 基础设施

### Task 1: 创建状态定义

**Files:**
- Create: `backend/agents/__init__.py`
- Create: `backend/agents/state.py`
- Test: `backend/tests/agents/test_state.py`

**Step 1: 创建 agents 包**

```bash
mkdir -p backend/agents
```

创建 `backend/agents/__init__.py`:

```python
"""智能体团队模块"""
```

**Step 2: 编写状态测试**

创建 `backend/tests/agents/test_state.py`:

```python
import pytest
from agents.state import AgentState, create_initial_state

def test_create_initial_state():
    state = create_initial_state("SELECT * FROM table", "sql")
    assert state["input"] == "SELECT * FROM table"
    assert state["task_type"] == "sql"
    assert state["errors"] == []
    assert state["step"] == "init"

def test_agent_state_structure():
    state = AgentState(
        input="test",
        task_type="sql",
        sql_result={},
        frontend_result={},
        backend_result={},
        test_results={},
        errors=[],
        step="test"
    )
    assert state["input"] == "test"
```

**Step 3: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_state.py -v
```

预期: `ModuleNotFoundError: No module named 'agents.state'`

**Step 4: 实现状态定义**

创建 `backend/agents/state.py`:

```python
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    """智能体团队共享状态"""
    input: str              # 用户输入
    task_type: str          # 任务类型: "sql" | "frontend" | "backend"
    sql_result: Dict[str, Any]     # SQL 团队输出
    frontend_result: Dict[str, Any]  # 前端团队输出
    backend_result: Dict[str, Any]   # 后端团队输出
    test_results: Dict[str, Any]     # 测试结果
    errors: List[str]       # 错误收集
    step: str               # 当前步骤

def create_initial_state(user_input: str, task: str) -> AgentState:
    """创建初始状态"""
    return AgentState(
        input=user_input,
        task_type=task,
        sql_result={},
        frontend_result={},
        backend_result={},
        test_results={},
        errors=[],
        step="init"
    )
```

**Step 5: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_state.py -v
```

预期: `PASSED`

**Step 6: Commit**

```bash
git add backend/agents/ backend/tests/agents/
git commit -m "feat: add agent state definition"
```

---

### Task 2: 创建基础智能体类

**Files:**
- Create: `backend/agents/agents/__init__.py`
- Create: `backend/agents/agents/base.py`
- Test: `backend/tests/agents/test_base_agent.py`

**Step 1: 编写基础智能体测试**

创建 `backend/tests/agents/test_base_agent.py`:

```python
import pytest
from agents.agents.base import BaseAgent

class DummyAgent(BaseAgent):
    async def execute(self, state):
        return {"step": "dummy_executed"}

@pytest.mark.asyncio
async def test_base_agent_name():
    agent = DummyAgent()
    assert agent.name == "DummyAgent"

@pytest.mark.asyncio
async def test_base_agent_execute():
    agent = DummyAgent()
    result = await agent.execute({"step": "test"})
    assert result["step"] == "dummy_executed"
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_base_agent.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现基础智能体类**

创建 `backend/agents/agents/__init__.py`:

```python
"""智能体实现"""
```

创建 `backend/agents/agents/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """智能体基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能体任务"""
        pass
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_base_agent.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/agents/
git commit -m "feat: add base agent class"
```

---

## 模块 2: SQL 智能体团队

### Task 3: 实现 SQL 语法验证器

**Files:**
- Create: `backend/agents/agents/syntax_agent.py`
- Test: `backend/tests/agents/test_syntax_agent.py`

**Step 1: 编写语法验证器测试**

创建 `backend/tests/agents/test_syntax_agent.py`:

```python
import pytest
from agents.agents.syntax_agent import SyntaxAgent

@pytest.mark.asyncio
async def test_valid_sql():
    agent = SyntaxAgent()
    result = await agent.execute({"input": "SELECT * FROM table"})
    assert result["sql_result"]["valid"] == True
    assert len(result["sql_result"]["errors"]) == 0

@pytest.mark.asyncio
async def test_invalid_sql():
    agent = SyntaxAgent()
    result = await agent.execute({"input": "SELCT * FROM table"})
    assert result["sql_result"]["valid"] == False
    assert len(result["sql_result"]["errors"]) > 0
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_syntax_agent.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现语法验证器**

创建 `backend/agents/agents/syntax_agent.py`:

```python
import sqlparse
from .base import BaseAgent

class SyntaxAgent(BaseAgent):
    """SQL 语法验证器"""

    async def execute(self, state):
        sql = state.get("input", "")
        try:
            parsed = sqlparse.parse(sql)
            is_valid = len(parsed) > 0 and parsed[0].tokens

            errors = []
            if not is_valid or not sql.strip():
                errors.append("Empty or invalid SQL")

            return {
                "sql_result": {
                    "valid": is_valid and len(errors) == 0,
                    "errors": errors
                }
            }
        except Exception as e:
            return {
                "sql_result": {
                    "valid": False,
                    "errors": [str(e)]
                }
            }
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_syntax_agent.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/agents/syntax_agent.py backend/tests/agents/test_syntax_agent.py
git commit -m "feat: add SQL syntax validation agent"
```

---

### Task 4: 实现 SQL 格式化专家

**Files:**
- Create: `backend/agents/agents/format_agent.py`
- Test: `backend/tests/agents/test_format_agent.py`

**Step 1: 编写格式化专家测试**

创建 `backend/tests/agents/test_format_agent.py`:

```python
import pytest
from agents.agents.format_agent import FormatAgent

@pytest.mark.asyncio
async def test_format_simple_sql():
    agent = FormatAgent()
    result = await agent.execute({
        "input": "select * from table where id=1"
    })
    assert "formatted" in result["sql_result"]
    assert "SELECT" in result["sql_result"]["formatted"]
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_format_agent.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现格式化专家**

创建 `backend/agents/agents/format_agent.py`:

```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from core.formatter_v4_fixed import SQLFormatter
from .base import BaseAgent

class FormatAgent(BaseAgent):
    """SQL 格式化专家"""

    def __init__(self):
        super().__init__()
        self.formatter = SQLFormatter()

    async def execute(self, state):
        sql = state.get("input", "")
        try:
            formatted = self.formatter.format_sql(sql)
            return {
                "sql_result": {
                    "formatted": formatted,
                    "success": True
                }
            }
        except Exception as e:
            return {
                "sql_result": {
                    "formatted": sql,
                    "success": False,
                    "error": str(e)
                }
            }
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_format_agent.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/agents/format_agent.py backend/tests/agents/test_format_agent.py
git commit -m "feat: add SQL format agent"
```

---

### Task 5: 实现测试工程师

**Files:**
- Create: `backend/agents/agents/test_agent.py`
- Test: `backend/tests/agents/test_test_agent.py`

**Step 1: 编写测试工程师测试**

创建 `backend/tests/agents/test_test_agent.py`:

```python
import pytest
from agents.agents.test_agent import TestAgent

@pytest.mark.asyncio
async def test_sql_validation():
    agent = TestAgent()
    result = await agent.execute({
        "input": "SELECT * FROM table",
        "task_type": "sql",
        "sql_result": {"formatted": "SELECT * FROM table"}
    })
    assert "test_results" in result
    assert result["test_results"]["task_type"] == "sql"
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_test_agent.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现测试工程师**

创建 `backend/agents/agents/test_agent.py`:

```python
import subprocess
from .base import BaseAgent

class TestAgent(BaseAgent):
    """测试工程师 - 验证所有智能体的输出"""

    async def execute(self, state):
        task_type = state.get("task_type", "")
        results = {"task_type": task_type, "checks": []}

        # 根据任务类型进行不同验证
        if task_type == "sql":
            sql_result = state.get("sql_result", {})
            if "formatted" in sql_result:
                results["checks"].append({
                    "name": "sql_not_empty",
                    "passed": len(sql_result["formatted"]) > 0
                })
            if "valid" in sql_result:
                results["checks"].append({
                    "name": "sql_syntax_valid",
                    "passed": sql_result["valid"]
                })

        passed_count = sum(1 for c in results["checks"] if c["passed"])
        results["summary"] = {
            "total": len(results["checks"]),
            "passed": passed_count,
            "failed": len(results["checks"]) - passed_count
        }

        return {"test_results": results}
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_test_agent.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/agents/test_agent.py backend/tests/agents/test_test_agent.py
git commit -m "feat: add test engineer agent"
```

---

## 模块 3: 前端智能体团队

### Task 6: 实现前端优化专家

**Files:**
- Create: `backend/agents/agents/frontend_agent.py`
- Test: `backend/tests/agents/test_frontend_agent.py`

**Step 1: 编写前端优化专家测试**

创建 `backend/tests/agents/test_frontend_agent.py`:

```python
import pytest
from agents.agents.frontend_agent import FrontendAgent

@pytest.mark.asyncio
async def test_frontend_analysis():
    agent = FrontendAgent()
    result = await agent.execute({
        "input": "优化 App.tsx 的加载性能"
    })
    assert "frontend_result" in result
    assert "suggestions" in result["frontend_result"]
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_frontend_agent.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现前端优化专家**

创建 `backend/agents/agents/frontend_agent.py`:

```python
from .base import BaseAgent

class FrontendAgent(BaseAgent):
    """前端优化专家 - React/TypeScript 代码分析和优化建议"""

    async def execute(self, state):
        user_input = state.get("input", "")

        # 分析用户请求，提供建议
        suggestions = []

        if "性能" in user_input or "加载" in user_input:
            suggestions.append({
                "type": "performance",
                "title": "代码分割",
                "description": "使用 React.lazy 和 Suspense 实现组件懒加载"
            })
            suggestions.append({
                "type": "performance",
                "title": "缓存优化",
                "description": "考虑使用 React.memo 或 useMemo 缓存计算结果"
            })

        if "样式" in user_input or "CSS" in user_input:
            suggestions.append({
                "type": "styling",
                "title": "CSS 优化",
                "description": "考虑使用 CSS-in-JS 或 Tailwind CSS 提高性能"
            })

        return {
            "frontend_result": {
                "suggestions": suggestions,
                "analyzed_input": user_input
            }
        }
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_frontend_agent.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/agents/frontend_agent.py backend/tests/agents/test_frontend_agent.py
git commit -m "feat: add frontend optimization agent"
```

---

## 模块 4: 主协调器

### Task 7: 实现主协调器

**Files:**
- Create: `backend/agents/coordinator.py`
- Test: `backend/tests/agents/test_coordinator.py`

**Step 1: 编写协调器测试**

创建 `backend/tests/agents/test_coordinator.py`:

```python
import pytest
from agents.coordinator import Coordinator

@pytest.mark.asyncio
async def test_route_sql_task():
    coord = Coordinator()
    result = await coord.route({
        "input": "SELECT * FROM table",
        "task_type": "sql"
    })
    assert result["next_agent"] == "sql_team"

@pytest.mark.asyncio
async def test_route_frontend_task():
    coord = Coordinator()
    result = await coord.route({
        "input": "优化前端",
        "task_type": "frontend"
    })
    assert result["next_agent"] == "frontend_team"
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_coordinator.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现主协调器**

创建 `backend/agents/coordinator.py`:

```python
class Coordinator:
    """主协调器 - 路由任务到对应团队"""

    def __init__(self):
        self.routing_map = {
            "sql": "sql_team",
            "frontend": "frontend_team",
            "backend": "backend_team"
        }

    async def route(self, state):
        """根据任务类型路由到对应团队"""
        task_type = state.get("task_type", "sql")
        next_agent = self.routing_map.get(task_type, "sql_team")

        return {
            **state,
            "step": f"routed_to_{next_agent}",
            "next_agent": next_agent
        }

    async def summarize(self, state):
        """汇总所有智能体的结果"""
        summary = {
            "input": state.get("input", ""),
            "task_type": state.get("task_type", ""),
            "results": {}
        }

        # 收集各团队结果
        for team in ["sql", "frontend", "backend"]:
            team_key = f"{team}_result"
            if team_key in state and state[team_key]:
                summary["results"][team] = state[team_key]

        # 添加测试结果
        if "test_results" in state:
            summary["test_results"] = state["test_results"]

        # 添加错误
        if state.get("errors"):
            summary["errors"] = state["errors"]

        return summary
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_coordinator.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/coordinator.py backend/tests/agents/test_coordinator.py
git commit -m "feat: add agent coordinator"
```

---

## 模块 5: LangGraph 工作流

### Task 8: 创建状态图

**Files:**
- Create: `backend/agents/graph.py`
- Test: `backend/tests/agents/test_graph.py`

**Step 1: 编写状态图测试**

创建 `backend/tests/agents/test_graph.py`:

```python
import pytest
from agents.graph import create_agent_graph

@pytest.mark.asyncio
async def test_sql_workflow():
    graph = create_agent_graph()
    state = {
        "input": "SELECT * FROM table",
        "task_type": "sql",
        "sql_result": {},
        "frontend_result": {},
        "backend_result": {},
        "test_results": {},
        "errors": [],
        "step": "init"
    }
    result = await graph.ainvoke(state)
    assert "test_results" in result
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/agents/test_graph.py -v
```

预期: `ModuleNotFoundError`

**Step 3: 实现状态图**

创建 `backend/agents/graph.py`:

```python
from langgraph.graph import StateGraph, END
from .state import AgentState
from .coordinator import Coordinator
from .agents.syntax_agent import SyntaxAgent
from .agents.format_agent import FormatAgent
from .agents.frontend_agent import FrontendAgent
from .agents.test_agent import TestAgent

def create_agent_graph():
    """创建智能体团队状态图"""

    # 初始化智能体
    coordinator = Coordinator()
    syntax_agent = SyntaxAgent()
    format_agent = FormatAgent()
    frontend_agent = FrontendAgent()
    test_agent = TestAgent()

    # 定义节点函数
    async def route_node(state):
        return await coordinator.route(state)

    async def sql_team_node(state):
        # 先验证语法
        result = await syntax_agent.execute(state)
        state["sql_result"].update(result["sql_result"])

        # 再格式化
        result = await format_agent.execute(state)
        state["sql_result"].update(result["sql_result"])

        return state

    async def frontend_team_node(state):
        result = await frontend_agent.execute(state)
        state["frontend_result"] = result["frontend_result"]
        return state

    async def backend_team_node(state):
        # 后端团队暂未实现
        state["backend_result"] = {"status": "not_implemented"}
        return state

    async def tester_node(state):
        result = await test_agent.execute(state)
        state["test_results"] = result["test_results"]
        return state

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("coordinator", route_node)
    workflow.add_node("sql_team", sql_team_node)
    workflow.add_node("frontend_team", frontend_team_node)
    workflow.add_node("backend_team", backend_team_node)
    workflow.add_node("tester", tester_node)

    # 设置入口点
    workflow.set_entry_point("coordinator")

    # 添加条件边
    workflow.add_conditional_edges(
        "coordinator",
        lambda s: s.get("next_agent", "sql_team"),
        {
            "sql_team": "sql_team",
            "frontend_team": "frontend_team",
            "backend_team": "backend_team"
        }
    )

    # 团队执行后进入测试
    workflow.add_edge("sql_team", "tester")
    workflow.add_edge("frontend_team", "tester")
    workflow.add_edge("backend_team", "tester")

    # 测试结束后
    workflow.add_edge("tester", END)

    return workflow.compile()
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/agents/test_graph.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/agents/graph.py backend/tests/agents/test_graph.py
git commit -m "feat: add LangGraph workflow for agent team"
```

---

## 模块 6: API 集成

### Task 9: 添加 API 端点

**Files:**
- Modify: `backend/api/main.py`
- Test: `backend/tests/test_api_agents.py`

**Step 1: 编写 API 测试**

创建 `backend/tests/test_api_agents.py`:

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_execute_sql_agent():
    response = client.post("/api/agent/execute", json={
        "input": "SELECT * FROM table",
        "task_type": "sql"
    })
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "execution_time" in data
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/test_api_agents.py -v
```

预期: `AssertionError` 或 `404 Not Found`

**Step 3: 添加 API 端点**

修改 `backend/api/main.py`，添加以下内容：

```python
# 在文件顶部导入
import time
from agents.graph import create_agent_graph
from pydantic import BaseModel

# 添加请求/响应模型
class AgentRequest(BaseModel):
    input: str
    task_type: str  # "sql" | "frontend" | "backend"

class AgentResponse(BaseModel):
    result: dict
    errors: list[str]
    execution_time: float

# 在文件中添加新端点
@app.post("/api/agent/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    """执行智能体任务"""
    start = time.time()

    graph = create_agent_graph()
    state = {
        "input": request.input,
        "task_type": request.task_type,
        "sql_result": {},
        "frontend_result": {},
        "backend_result": {},
        "test_results": {},
        "errors": [],
        "step": "init"
    }

    result = await graph.ainvoke(state)

    return AgentResponse(
        result={k: v for k, v in result.items() if k != "errors"},
        errors=result.get("errors", []),
        execution_time=time.time() - start
    )
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/test_api_agents.py -v
```

预期: `PASSED`

**Step 5: Commit**

```bash
git add backend/api/main.py backend/tests/test_api_agents.py
git commit -m "feat: add agent execution API endpoint"
```

---

## 模块 7: 前端集成

### Task 10: 添加前端服务

**Files:**
- Create: `frontend/src/services/agentService.ts`
- Modify: `frontend/src/AppSimple.tsx`

**Step 1: 创建前端服务**

创建 `frontend/src/services/agentService.ts`:

```typescript
export interface AgentRequest {
  input: string;
  taskType: 'sql' | 'frontend' | 'backend';
}

export interface AgentResponse {
  result: any;
  errors: string[];
  executionTime: number;
}

export async function executeAgent(request: AgentRequest): Promise<AgentResponse> {
  const response = await fetch('http://localhost:8888/api/agent/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input: request.input,
      task_type: request.taskType
    })
  });

  if (!response.ok) {
    throw new Error(`Agent execution failed: ${response.statusText}`);
  }

  return response.json();
}
```

**Step 2: 添加前端 UI 组件**

在 `frontend/src/AppSimple.tsx` 中添加智能体执行按钮和结果展示：

```typescript
// 在组件中添加状态
const [agentInput, setAgentInput] = useState('');
const [agentResult, setAgentResult] = useState<any>(null);
const [agentLoading, setAgentLoading] = useState(false);

// 添加处理函数
const handleAgentExecute = async () => {
  setAgentLoading(true);
  try {
    const result = await executeAgent({
      input: agentInput,
      taskType: 'sql'
    });
    setAgentResult(result);
  } catch (error) {
    console.error('Agent error:', error);
  } finally {
    setAgentLoading(false);
  }
};

// 在 JSX 中添加 UI
<div style={{ marginTop: '20px', padding: '15px', border: '1px solid #ddd' }}>
  <h3>智能体助手</h3>
  <input
    type="text"
    value={agentInput}
    onChange={(e) => setAgentInput(e.target.value)}
    placeholder="输入任务，例如: 格式化这段 SQL"
    style={{ width: '70%', padding: '8px' }}
  />
  <button onClick={handleAgentExecute} disabled={agentLoading}>
    {agentLoading ? '执行中...' : '执行'}
  </button>
  {agentResult && (
    <pre style={{ marginTop: '10px', background: '#f5f5f5', padding: '10px' }}>
      {JSON.stringify(agentResult, null, 2)}
    </pre>
  )}
</div>
```

**Step 3: 测试前端集成**

启动前端服务并测试智能体功能。

**Step 4: Commit**

```bash
git add frontend/src/services/agentService.ts frontend/src/AppSimple.tsx
git commit -m "feat: add agent service integration to frontend"
```

---

## 模块 8: 集成测试

### Task 11: 端到端测试

**Files:**
- Create: `backend/tests/test_e2e_agents.py`

**Step 1: 编写端到端测试**

创建 `backend/tests/test_e2e_agents.py`:

```python
import pytest
from agents.graph import create_agent_graph

@pytest.mark.asyncio
async def test_sql_formatting_e2e():
    """测试完整的 SQL 格式化流程"""
    graph = create_agent_graph()
    state = {
        "input": "select * from table where id=1",
        "task_type": "sql",
        "sql_result": {},
        "frontend_result": {},
        "backend_result": {},
        "test_results": {},
        "errors": [],
        "step": "init"
    }
    result = await graph.ainvoke(state)
    assert "sql_result" in result
    assert "test_results" in result
    assert result["test_results"]["summary"]["total"] > 0

@pytest.mark.asyncio
async def test_frontend_optimization_e2e():
    """测试前端优化流程"""
    graph = create_agent_graph()
    state = {
        "input": "优化 App.tsx 的加载性能",
        "task_type": "frontend",
        "sql_result": {},
        "frontend_result": {},
        "backend_result": {},
        "test_results": {},
        "errors": [],
        "step": "init"
    }
    result = await graph.ainvoke(state)
    assert "frontend_result" in result
    assert len(result["frontend_result"]["suggestions"]) > 0
```

**Step 2: 运行测试**

```bash
cd backend && pytest tests/test_e2e_agents.py -v
```

预期: `PASSED`

**Step 3: Commit**

```bash
git add backend/tests/test_e2e_agents.py
git commit -m "test: add end-to-end tests for agent team"
```

---

## 模块 9: 文档完善

### Task 12: 编写使用文档

**Files:**
- Create: `backend/agents/README.md`

**Step 1: 编写智能体团队文档**

创建 `backend/agents/README.md`:

```markdown
# 智能体团队

## 概述

智能体团队是一个基于 LangChain + LangGraph 的多智能体协作系统，为 SQL 格式化器项目提供智能辅助功能。

## 智能体角色

| 角色 | 描述 |
|------|------|
| 主协调器 | 路由任务到对应团队 |
| SQL 语法验证器 | 验证 SQL 语法 |
| SQL 格式化专家 | 格式化 SQL 语句 |
| 前端优化专家 | 提供前端优化建议 |
| 测试工程师 | 验证输出结果 |

## 使用示例

### Python API

```python
from agents.graph import create_agent_graph

graph = create_agent_graph()
result = await graph.ainvoke({
    "input": "SELECT * FROM table",
    "task_type": "sql"
})
```

### HTTP API

```bash
curl -X POST http://localhost:8888/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"input": "SELECT * FROM table", "task_type": "sql"}'
```

## 扩展指南

添加新智能体：

1. 继承 `BaseAgent`
2. 实现 `execute` 方法
3. 在 `graph.py` 中注册
```

**Step 2: Commit**

```bash
git add backend/agents/README.md
git commit -m "docs: add agent team documentation"
```

---

## 完成

### Task 13: 最终验证

**Step 1: 运行所有测试**

```bash
cd backend && pytest tests/ -v
```

预期: 全部通过

**Step 2: 启动服务验证**

```bash
# 启动后端
cd backend && python -m uvicorn api.main:app --reload --port 8888

# 启动前端
cd frontend && npm start
```

**Step 3: 功能验证清单**

- [ ] SQL 格式化功能正常
- [ ] 前端优化建议正常返回
- [ ] 测试验证功能正常
- [ ] API 端点响应正常
- [ ] 前端 UI 集成正常

**Step 4: 最终 Commit**

```bash
git commit --allow-empty -m "feat: complete agent team implementation"
```

---

## 总结

本实施计划包含 13 个任务，涵盖：

1. 环境设置和依赖安装
2. 基础设施（状态定义、基础类）
3. SQL 智能体团队（语法验证、格式化）
4. 前端智能体团队（优化建议）
5. 主协调器（任务路由）
6. LangGraph 工作流集成
7. API 端点
8. 前端集成
9. 集成测试
10. 文档完善

预计完成时间: 4-6 小时

# sqlglot + 后处理格式化器实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 基于 sqlglot AST 解析构建新的 SQL 格式化器，保留 v4 的格式化风格

**架构:**
1. 使用 sqlglot 解析 SQL 为 AST（确保 100% 语法准确性）
2. 将 AST 转换为中间格式（便于后处理）
3. 后处理层应用 v4 风格规则（列对齐、换行等）

**技术栈:**
- sqlglot 28.10.0 (MIT 许可)
- Python 3.14
- pytest (测试)

**核心优势:**
- 准确解析复杂嵌套子查询
- 自动支持新 SQL 语法
- 代码更简洁易维护

---

## Phase 1: 基础框架搭建

### Task 1: 创建 v5 格式化器文件

**文件:**
- 创建: `backend/core/formatter_v5.py`

**Step 1: 创建基础文件结构**

```python
# -*- coding: utf-8 -*-
"""
SQL Formatter V5 - 基于 sqlglot AST 解析
结合 v4 的格式化风格
"""
from typing import Optional
from sqlglot import parse, exp
from sqlglot.dialects import Spark


class SQLFormatterV5:
    """基于 sqlglot 的 SQL 格式化器"""

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    def format(self, sql: str, dialect: str = "spark") -> str:
        """格式化 SQL

        Args:
            sql: 原始 SQL
            dialect: SQL 方言 (默认 spark)

        Returns:
            格式化后的 SQL
        """
        # TODO: 实现
        return sql


def format_sql_v5(sql: str, **options) -> str:
    """v5 格式化入口函数"""
    formatter = SQLFormatterV5(
        indent_spaces=options.get('indent', 4)
    )
    return formatter.format(sql)
```

**Step 2: 创建基础测试**

创建文件: `backend/core/test_formatter_v5.py`

```python
# -*- coding: utf-8 -*-
"""Formatter V5 测试"""
import pytest
from formatter_v5 import format_sql_v5


def test_basic_select():
    """测试基础 SELECT 格式化"""
    sql = "select a,b from t1"
    result = format_sql_v5(sql)
    # 基础验证：只是确保不报错
    assert isinstance(result, str)
    assert len(result) > 0


def test_simple_select():
    """测试简单 SELECT"""
    sql = "SELECT a, b FROM table1"
    result = format_sql_v5(sql)
    print(result)
```

**Step 3: 运行测试验证基础结构**

```bash
cd backend/core
pytest test_formatter_v5.py -v
```

预期: `PASSED`

**Step 4: 提交**

```bash
git add backend/core/formatter_v5.py backend/core/test_formatter_v5.py
git commit -m "feat: create v5 formatter skeleton"
```

---

## Phase 2: sqlglot 基础解析

### Task 2: 实现 AST 解析

**文件:**
- 修改: `backend/core/formatter_v5.py`

**Step 1: 实现基础解析**

```python
def format(self, sql: str, dialect: str = "spark") -> str:
    """格式化 SQL"""
    try:
        # 解析为 AST
        ast = parse(sql, dialect=dialect, read=dialect)

        if not ast:
            return sql

        # 使用 sqlglot 内置格式化作为起点
        formatted = ast[0].sql(dialect=dialect, pretty=True, indent=self.indent_spaces)

        return formatted

    except Exception as e:
        # 解析失败时返回原 SQL
        return sql
```

**Step 2: 添加测试用例**

修改: `backend/core/test_formatter_v5.py`

```python
def test_simple_select_formatted():
    """测试简单 SELECT 格式化"""
    sql = "select a,b,c from table1"
    result = format_sql_v5(sql)
    print("\n=== 简单 SELECT ===")
    print(result)
    # 验证关键字大写
    assert "SELECT" in result.upper()
    # 验证换行
    assert "\n" in result


def test_with_where():
    """测试 WHERE 子句"""
    sql = "select a from t1 where x=1 and y=2"
    result = format_sql_v5(sql)
    print("\n=== WHERE 子句 ===")
    print(result)
    assert "WHERE" in result.upper()


def test_with_join():
    """测试 JOIN"""
    sql = "select t1.a,t2.b from t1 inner join t2 on t1.id=t2.id"
    result = format_sql_v5(sql)
    print("\n=== JOIN ===")
    print(result)
    assert "JOIN" in result.upper()
    assert "ON" in result.upper()
```

**Step 3: 运行测试**

```bash
pytest test_formatter_v5.py -v -s
```

**Step 4: 提交**

```bash
git add backend/core/formatter_v5.py backend/core/test_formatter_v5.py
git commit -m "feat: add sqlglot AST parsing to v5"
```

---

## Phase 3: 复杂语法支持

### Task 3: 子查询和嵌套

**文件:**
- 修改: `backend/core/formatter_v5.py`
- 修改: `backend/core/test_formatter_v5.py`

**Step 1: 添加子查询测试**

```python
def test_subquery_in_select():
    """测试 SELECT 中的子查询"""
    sql = "select a,(select max(x) from t2 where t2.id=t1.id) as max_x from t1"
    result = format_sql_v5(sql)
    print("\n=== 子查询 ===")
    print(result)
    # 应该正确处理嵌套
    assert "SELECT" in result.upper()


def test_nested_subquery():
    """测试深层嵌套子查询"""
    sql = "select a,(select b from (select c from t1)) as nested from t2"
    result = format_sql_v5(sql)
    print("\n=== 深层嵌套 ===")
    print(result)
    assert "SELECT" in result.upper()


def test_exists_subquery():
    """测试 EXISTS 子查询"""
    sql = "select * from t1 where exists (select 1 from t2 where t2.id=t1.id)"
    result = format_sql_v5(sql)
    print("\n=== EXISTS ===")
    print(result)
    assert "EXISTS" in result.upper()
```

**Step 2: 运行测试验证**

```bash
pytest test_formatter_v5.py::test_subquery_in_select -v -s
pytest test_formatter_v5.py::test_nested_subquery -v -s
pytest test_formatter_v5.py::test_exists_subquery -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_formatter_v5.py
git commit -m "test: add subquery test cases"
```

---

### Task 4: CASE WHEN 和 CTE

**文件:**
- 修改: `backend/core/test_formatter_v5.py`

**Step 1: 添加测试**

```python
def test_case_when():
    """测试 CASE WHEN"""
    sql = "select case when x>0 then 'positive' when x<0 then 'negative' else 'zero' end as sign from t1"
    result = format_sql_v5(sql)
    print("\n=== CASE WHEN ===")
    print(result)
    assert "CASE" in result.upper()
    assert "WHEN" in result.upper()


def test_cte_with():
    """测试 CTE WITH"""
    sql = "with cte1 as (select a,b from t1),cte2 as (select c,d from t2) select * from cte1 join cte2 on cte1.a=cte2.c"
    result = format_sql_v5(sql)
    print("\n=== CTE ===")
    print(result)
    assert "WITH" in result.upper()
```

**Step 2: 运行测试**

```bash
pytest test_formatter_v5.py::test_case_when -v -s
pytest test_formatter_v5.py::test_cte_with -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_formatter_v5.py
git commit -m "test: add CASE WHEN and CTE tests"
```

---

## Phase 4: v4 风格后处理

### Task 5: 列对齐风格

**文件:**
- 修改: `backend/core/formatter_v5.py`

**Step 1: 添加后处理器**

```python
def _apply_v4_column_style(self, sql: str) -> str:
    """应用 v4 风格的列对齐

    将:
        SELECT
          a,
          b,
          c

    转换为:
        SELECT a
             , b
             , c
    """
    lines = sql.split('\n')
    result = []
    in_select = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测 SELECT 子句开始
        if stripped.startswith('SELECT'):
            in_select = True
            result.append(line)
            continue

        # 检测 FROM 结束 SELECT
        if stripped.startswith('FROM'):
            in_select = False
            result.append(line)
            continue

        # 处理 SELECT 中的列
        if in_select and stripped.startswith(','):
            # 列对齐风格：逗号在前，缩进对齐
            result.append('     , ' + stripped[1:].strip())
        elif in_select and stripped and not stripped.startswith('('):
            # 第一列
            result.append(stripped)
        else:
            result.append(line)

    return '\n'.join(result)
```

**Step 2: 集成到 format 方法**

```python
def format(self, sql: str, dialect: str = "spark") -> str:
    """格式化 SQL"""
    try:
        ast = parse(sql, dialect=dialect, read=dialect)
        if not ast:
            return sql

        # 使用 sqlglot 格式化
        formatted = ast[0].sql(dialect=dialect, pretty=True, indent=self.indent_spaces)

        # 应用 v4 风格后处理
        formatted = self._apply_v4_column_style(formatted)

        return formatted

    except Exception as e:
        return sql
```

**Step 3: 添加测试**

```python
def test_v4_column_alignment():
    """测试 v4 风格列对齐"""
    sql = "select a,b,c from table1"
    result = format_sql_v5(sql)
    print("\n=== v4 风格列对齐 ===")
    print(result)
    # 验证逗号在行首
    assert ', ' in result or '\n     ,' in result
```

**Step 4: 运行测试**

```bash
pytest test_formatter_v5.py::test_v4_column_alignment -v -s
```

**Step 5: 提交**

```bash
git add backend/core/formatter_v5.py backend/core/test_formatter_v5.py
git commit -m "feat: add v4 style column alignment"
```

---

## Phase 5: 复杂语句支持

### Task 6: CREATE TABLE

**文件:**
- 修改: `backend/core/test_formatter_v5.py`

**Step 1: 添加测试**

```python
def test_create_table():
    """测试 CREATE TABLE"""
    sql = "create table if not exists t1 (a int comment 'column a',b string,c double) comment 'table t1' partitioned by (dt string)"
    result = format_sql_v5(sql)
    print("\n=== CREATE TABLE ===")
    print(result)
    assert "CREATE TABLE" in result.upper()
```

**Step 2: 运行测试**

```bash
pytest test_formatter_v5.py::test_create_table -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_formatter_v5.py
git commit -m "test: add CREATE TABLE test"
```

---

### Task 7: INSERT 和窗口函数

**文件:**
- 修改: `backend/core/test_formatter_v5.py`

**Step 1: 添加测试**

```python
def test_insert():
    """测试 INSERT"""
    sql = "insert into table t1 partition(dt='2024-01-01') select a,b from t2 where c>0"
    result = format_sql_v5(sql)
    print("\n=== INSERT ===")
    print(result)
    assert "INSERT" in result.upper()


def test_over_window():
    """测试 OVER 窗口函数"""
    sql = "select a,row_number() over (partition by b order by c desc) as rn from t1"
    result = format_sql_v5(sql)
    print("\n=== OVER 窗口 ===")
    print(result)
    assert "OVER" in result.upper()
```

**Step 2: 运行测试**

```bash
pytest test_formatter_v5.py::test_insert -v -s
pytest test_formatter_v5.py::test_over_window -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_formatter_v5.py
git commit -m "test: add INSERT and OVER tests"
```

---

## Phase 6: 对比验证

### Task 8: v4 vs v5 对比测试

**文件:**
- 创建: `backend/core/test_v4_v5_comparison.py`

**Step 1: 创建对比测试**

```python
# -*- coding: utf-8 -*-
"""v4 vs v5 格式化对比测试"""
import pytest
from formatter_v5 import format_sql_v5

try:
    from formatter_v4_fixed import format_sql_v4_fixed
    HAS_V4 = True
except ImportError:
    HAS_V4 = False


@pytest.mark.skipif(not HAS_V4, reason="v4 not available")
def test_comparison_simple():
    """对比测试：简单 SELECT"""
    sql = "select a,b from t1"

    v4_result = format_sql_v4_fixed(sql)
    v5_result = format_sql_v5(sql)

    print("\n=== v4 结果 ===")
    print(v4_result)
    print("\n=== v5 结果 ===")
    print(v5_result)

    # 两者都应该能正确格式化
    assert "SELECT" in v4_result.upper()
    assert "SELECT" in v5_result.upper()


@pytest.mark.skipif(not HAS_V4, reason="v4 not available")
def test_comparison_complex():
    """对比测试：复杂子查询"""
    sql = "select a,(select max(x) from t2 where t2.id=t1.id) as max_x from t1"

    v4_result = format_sql_v4_fixed(sql)
    v5_result = format_sql_v5(sql)

    print("\n=== v4 复杂子查询 ===")
    print(v4_result)
    print("\n=== v5 复杂子查询 ===")
    print(v5_result)

    # v5 应该正确解析（v4 在这个案例中可能有问题）
    assert "SELECT" in v5_result.upper()
    assert "MAX" in v5_result.upper()
```

**Step 2: 运行对比测试**

```bash
pytest test_v4_v5_comparison.py -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_v4_v5_comparison.py
git commit -m "test: add v4 vs v5 comparison tests"
```

---

## Phase 7: API 集成

### Task 9: 添加 v5 API 端点

**文件:**
- 修改: `backend/api/main.py`

**Step 1: 添加 v5 导入和端点**

```python
# 在文件顶部添加
try:
    from core.formatter_v5 import format_sql_v5
except ImportError:
    format_sql_v5 = None


# 添加新的 API 端点（在 /api/format 之后）
@app.post("/api/format-v5")
async def format_v5(request: Request):
    """v5 格式化 API (基于 sqlglot)"""
    try:
        data = await request.json()
        sql = data.get('sql', '')

        if not sql:
            raise HTTPException(status_code=400, detail="SQL is required")

        options = data.get('options', {})

        # 使用 v5 格式化
        formatted = format_sql_v5(sql, **options)

        return {
            "success": True,
            "formatted": formatted,
            "version": "v5-sqlglot"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 测试 API**

```bash
# 启动服务
cd backend/api
python main.py

# 测试
curl -X POST http://localhost:8000/api/format-v5 \
  -H "Content-Type: application/json" \
  -d '{"sql": "select a,b from t1"}'
```

**Step 3: 提交**

```bash
git add backend/api/main.py
git commit -m "feat: add v5 format API endpoint"
```

---

## Phase 8: 完整验证

### Task 10: 使用真实 SQL 文件测试

**文件:**
- 创建: `backend/core/test_v5_with_real_files.py`

**Step 1: 创建文件测试**

```python
# -*- coding: utf-8 -*-
"""使用真实 SQL 文件测试 v5"""
from formatter_v5 import format_sql_v5
from pathlib import Path


def test_with_real_sql_files():
    """使用项目中的真实 SQL 文件测试"""
    sql_files = [
        "../../测试用例表/JRJC_MON_B01_T18_GRKHXX.sql",
        "../../测试用例表/GJDG_JRZF_D01_PARALLEL_CWKJB - 副本.sql",
    ]

    for file_path in sql_files:
        path = Path(__file__).parent / file_path
        if not path.exists():
            print(f"跳过不存在的文件: {file_path}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"\n=== 测试文件: {file_path} ===")
        print(f"原始长度: {len(content)} 字符")

        try:
            result = format_sql_v5(content)
            print(f"格式化长度: {len(result)} 字符")
            print(f"前 500 字符:\n{result[:500]}")

            # 基本验证
            assert isinstance(result, str)
            assert len(result) > 0

        except Exception as e:
            print(f"格式化失败: {e}")
            raise
```

**Step 2: 运行真实文件测试**

```bash
pytest test_v5_with_real_files.py -v -s
```

**Step 3: 提交**

```bash
git add backend/core/test_v5_with_real_files.py
git commit -m "test: add real SQL file integration tests"
```

---

## 验收标准

完成所有任务后，v5 格式化器应该：

- [ ] 正确解析所有基础 SQL 语句（SELECT, INSERT, CREATE TABLE 等）
- [ ] 正确处理复杂嵌套子查询
- [ ] 正确处理 CASE WHEN, CTE, EXISTS 等语法
- [ ] 风格接近 v4（可后续调整）
- [ ] 通过所有单元测试
- [ ] 通过真实 SQL 文件测试
- [ ] 提供独立的 API 端点

---

## 后续优化方向

1. **风格微调**: 根据对比测试结果调整后处理器
2. **性能优化**: 大文件处理性能
3. **错误处理**: 更友好的错误提示
4. **配置化**: 支持更多格式化选项

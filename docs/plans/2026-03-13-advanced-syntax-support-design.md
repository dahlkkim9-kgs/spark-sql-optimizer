# 高级 SQL 语法支持扩展 - 设计文档

> **创建日期:** 2026-03-13
> **状态:** 设计完成，待实施

---

## 问题概述

当前 SQL 格式化器 (`formatter_v4_fixed.py`) 主要支持基础的 SELECT/INSERT/CREATE 语句格式化。对于以下高级 SQL 语法缺乏支持：

1. **集合操作**: UNION, UNION ALL, INTERSECT, EXCEPT, MINUS
2. **窗口函数**: OVER, PARTITION BY, ORDER BY, 窗口框架
3. **数据操作**: MERGE, INSERT OVERWRITE, 动态分区
4. **高级转换**: PIVOT, UNPIVOT, LATERAL VIEW, TRANSFORM

---

## 设计目标

### 功能目标

- 支持上述四类高级 SQL 语法的格式化
- 保持现有格式化规则的一致性
- 采用模块化架构，便于扩展和维护

### 非功能目标

- 不破坏现有功能
- 代码可读性和可维护性
- 可测试性

---

## 架构设计

### 核心策略：模块化共存

采用**语法处理器模块化架构**，将不同的 SQL 语法类型分配给专门的处理器模块：

```
现有格式化器 (formatter_v4_fixed.py)  ← 保持不变
    ↓
新入口协调器 (formatter_v5.py)
    ↓
SQL 分类器 (parser/sql_classifier.py)
    ↓
┌──────────┬──────────┬──────────┬──────────┐
│ 集合操作  │ 窗口函数  │ 数据操作  │ 高级转换  │
│处理器    │处理器    │处理器    │处理器    │
└──────────┴──────────┴──────────┴──────────┘
    ↓
输出格式化 SQL
```

### 目录结构

```
backend/core/
├── formatter_v4_fixed.py      # 现有格式化器（不变）
├── processors/                 # 新增：语法处理器目录
│   ├── __init__.py
│   ├── base_processor.py       # 基础处理器接口
│   ├── set_operations.py       # 集合操作处理器
│   ├── window_functions.py     # 窗口函数处理器
│   ├── data_operations.py      # 数据操作处理器
│   └── advanced_transforms.py  # 高级转换处理器
├── parser/
│   ├── __init__.py
│   └── sql_classifier.py       # SQL 分类器
└── formatter_v5.py             # 新入口（协调器）
```

---

## 各处理器设计

### 1. 集合操作处理器 (set_operations.py)

**支持语法**: UNION, UNION ALL, INTERSECT, EXCEPT, MINUS

**格式化规则**:
- 每个集合操作符前后换行
- 每个 SELECT 语句独立格式化（复用现有格式化器）
- 集合操作符大写
- 支持嵌套集合操作（带括号的优先级）

**输入示例**:
```sql
SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2 UNION SELECT e, f FROM t3
```

**输出示例**:
```sql
SELECT a
     , b
FROM t1
UNION ALL
SELECT c
     , d
FROM t2
UNION
SELECT e
     , f
FROM t3
```

**嵌套示例**:
```sql
(SELECT a UNION SELECT b) INTERSECT (SELECT c UNION SELECT d)
```

---

### 2. 窗口函数处理器 (window_functions.py)

**支持语法**: OVER, PARTITION BY, ORDER BY, WINDOW FRAME, WINDOW 子句

**格式化规则**:
- OVER 子句换行缩进
- PARTITION BY 和 ORDER BY 独立一行
- 窗口框架 (ROWS BETWEEN) 独立格式化
- 支持命名窗口 (WINDOW 子句)

**输入示例**:
```sql
SELECT dept, emp_name, salary, ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) AS rk, SUM(salary) OVER (PARTITION BY dept ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_sum FROM employees
```

**输出示例**:
```sql
SELECT dept
     , emp_name
     , salary
     , ROW_NUMBER() OVER (
                          PARTITION BY dept
                          ORDER BY salary DESC
                         ) AS rk
     , SUM(salary) OVER (
                         PARTITION BY dept
                         ORDER BY hire_date
                         ROWS BETWEEN UNBOUNDED PRECEDING
                             AND CURRENT ROW
                        ) AS running_sum
FROM employees
```

---

### 3. 数据操作处理器 (data_operations.py)

**支持语法**: MERGE, INSERT OVERWRITE, INSERT OVERWRITE DIRECTORY, 动态分区

**格式化规则**:
- MERGE 的每个 WHEN 分支独立格式化
- INSERT OVERWRITE 识别动态分区模式
- 支持多行 INSERT 语句

**MERGE 输入示例**:
```sql
MERGE INTO target_table USING source_table ON target.id = source.id WHEN MATCHED AND source.is_deleted = 1 THEN DELETE WHEN MATCHED THEN UPDATE SET target.value = source.value WHEN NOT MATCHED THEN INSERT (id, value) VALUES (source.id, source.value)
```

**MERGE 输出示例**:
```sql
MERGE INTO target_table
USING source_table
ON target.id = source.id
WHEN MATCHED AND source.is_deleted = 1 THEN
    DELETE
WHEN MATCHED THEN
    UPDATE SET target.value = source.value
WHEN NOT MATCHED THEN
    INSERT (id, value)
    VALUES (source.id, source.value)
```

---

### 4. 高级转换处理器 (advanced_transforms.py)

**支持语法**: PIVOT, UNPIVOT, LATERAL VIEW, TRANSFORM, CLUSTER BY, DISTRIBUTE BY

**格式化规则**:
- LATERAL VIEW 行独立格式化
- PIVOT/UNPIVOT 的聚合列对齐
- TRANSFORM 语句的特殊格式（脚本调用）

**LATERAL VIEW 输入示例**:
```sql
SELECT user_id, category FROM page_views LATERAL VIEW EXPLODE(pages) exploded_table AS category LATERAL VIEW EXPLODE(categories) cat_table AS category
```

**LATERAL VIEW 输出示例**:
```sql
SELECT user_id
     , category
FROM page_views
LATERAL VIEW EXPLODE(pages) exploded_table AS category
LATERAL VIEW EXPLODE(categories) cat_table AS category
```

---

## SQL 分类器设计

### 分类器职责

`sql_classifier.py` 负责识别 SQL 语句类型，分发到对应的处理器。

```python
class SQLClassifier:
    """SQL 语句分类器"""

    def classify(self, sql: str) -> List[str]:
        """
        返回该 SQL 包含的语法类型列表

        可能的返回值:
        - ['set_operations']     # UNION/INTERSECT/EXCEPT
        - ['window_functions']   # OVER 子句
        - ['data_operations']    # MERGE/INSERT OVERWRITE
        - ['advanced_transforms'] # PIVOT/LATERAL VIEW
        - ['basic']              # 基础 SELECT（现有格式化器处理）
        - ['set_operations', 'window_functions']  # 混合语法
        """
```

### 检测规则（按优先级）

| 优先级 | 语法模式 | 正则示例 |
|--------|----------|----------|
| 1 | MERGE 语句 | `^\s*MERGE\s+INTO\b` |
| 2 | 集合操作 | `\bUNION\s+(ALL\s+)?\b|\bINTERSECT\b|\bEXCEPT\b|\bMINUS\b` |
| 3 | INSERT OVERWRITE | `INSERT\s+OVERWRITE\s+(TABLE\s+)?[^\s]+` |
| 4 | 窗口函数 | `\bOVER\s*\(|WINDOW\s+\w+\s+AS\b` |
| 5 | PIVOT/UNPIVOT | `\bPIVOT\b|\bUNPIVOT\b` |
| 6 | LATERAL VIEW | `\bLATERAL\s+VIEW\b` |
| 7 | TRANSFORM | `\bTRANSFORM\s*\(` |
| 8 | CLUSTER/DISTRIBUTE BY | `\b(CLUSTER|DISTRIBUTE)\s+BY\b` |

---

## 缩进规则

### 现有规则（沿用）

| 场景 | 缩进规则 |
|------|----------|
| 基础层级 | 每级 4 个空格 |
| WHERE 子句 | WHERE 与 FROM 对齐（无缩进），AND/OR 缩进 4 个空格 |
| JOIN 子句 | JOIN 与 FROM 对齐（无缩进），ON 条件缩进 4 个空格 |
| 子查询内容 | 返回不带缩进内容，由调用代码统一添加缩进 |
| 括号对齐 | CTE/CACHE TABLE 使用括号位置对齐 |

### 新增规则

| 场景 | 缩进规则 |
|------|----------|
| 集合操作符 | UNION/INTERSECT 与 FROM 同级（无缩进），前后换行 |
| 窗口函数 OVER 子句 | 内容缩进 4 个空格（类似 JOIN 的 ON 条件） |
| 窗口框架 ROWS BETWEEN | 内容缩进 8 个空格（两级缩进） |
| MERGE WHEN 分支 | 每个分支独立一行，THEN 后语句缩进 4 个空格 |
| LATERAL VIEW | 沿用 JOIN 的对齐规则（无缩进） |

---

## 实施优先级

### Phase 1: 基础集合操作（优先级最高）
- UNION / UNION ALL / INTERSECT / EXCEPT / MINUS
- 预计工作量：2-3 小时

### Phase 2: 窗口函数（优先级高）
- OVER / PARTITION BY / ORDER BY / 窗口框架 / WINDOW 子句
- 预计工作量：3-4 小时

### Phase 3: 数据操作（优先级中）
- MERGE / INSERT OVERWRITE / 动态分区
- 预计工作量：4-5 小时

### Phase 4: 高级转换（优先级低）
- PIVOT / UNPIVOT / LATERAL VIEW / TRANSFORM
- 预计工作量：3-4 小时

---

## 修改文件

### 新增文件

```
backend/core/processors/__init__.py
backend/core/processors/base_processor.py
backend/core/processors/set_operations.py
backend/core/processors/window_functions.py
backend/core/processors/data_operations.py
backend/core/processors/advanced_transforms.py
backend/core/parser/__init__.py
backend/core/parser/sql_classifier.py
backend/core/formatter_v5.py
```

### 修改文件

```
backend/api/endpoints.py  # 添加 /format/v5 端点（可选）
```

### 不变文件

```
backend/core/formatter_v4_fixed.py  # 保持不变，复用现有功能
```

---

## 测试用例

### 集合操作测试

```python
# test_set_operations.py

def test_simple_union():
    input_sql = "SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2"
    # 验证 UNION ALL 前后换行

def test_nested_set_operations():
    input_sql = "(SELECT a UNION SELECT b) INTERSECT (SELECT c UNION SELECT d)"
    # 验证括号对齐

def test_mixed_union_and_join():
    input_sql = "SELECT a FROM t1 JOIN t2 ON t1.id = t2.id UNION SELECT b FROM t3"
    # 验证 JOIN 和 UNION 混合场景
```

### 窗口函数测试

```python
# test_window_functions.py

def test_simple_over():
    input_sql = "SELECT ROW_NUMBER() OVER (ORDER BY id) AS rk FROM t1"
    # 验证 OVER 子句格式化

def test_window_frame():
    input_sql = "SELECT SUM(val) OVER (ORDER BY time ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM t1"
    # 验证窗口框架格式化

def test_named_window():
    input_sql = "SELECT SUM(val) OVER w AS total FROM t1 WINDOW w AS (PARTITION BY cat)"
    # 验证命名窗口格式化
```

### MERGE 测试

```python
# test_merge.py

def test_simple_merge():
    input_sql = "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.val = s.val"
    # 验证 MERGE 基本格式化

def test_merge_with_delete():
    input_sql = "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED AND s.del = 1 THEN DELETE"
    # 验证 DELETE 分支格式化
```

### LATERAL VIEW 测试

```python
# test_lateral_view.py

def test_single_lateral_view():
    input_sql = "SELECT id, category FROM page_views LATERAL VIEW EXPLODE(pages) exploded AS category"
    # 验证单个 LATERAL VIEW 格式化

def test_multiple_lateral_views():
    input_sql = "SELECT id, cat FROM t LATERAL VIEW EXPLODE(arr1) e1 AS cat LATERAL VIEW EXPLODE(arr2) e2 AS cat"
    # 验证多个 LATERAL VIEW 格式化
```

---

## 预期效果

- ✅ 支持 UNION/INTERSECT/EXCEPT/MINUS 集合操作格式化
- ✅ 支持窗口函数 (OVER/PARTITION BY/窗口框架) 格式化
- ✅ 支持 MERGE/INSERT OVERWRITE 数据操作格式化
- ✅ 支持 PIVOT/LATERAL VIEW 高级转换格式化
- ✅ 保持现有格式化规则一致性
- ✅ 模块化架构便于后续扩展

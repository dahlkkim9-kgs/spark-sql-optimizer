# WITH AS 和 CACHE TABLE 格式化修复 - 设计文档

> **创建日期:** 2026-03-12
> **状态:** 设计完成，待实施

---

## 问题概述

当前 SQL 格式化器在处理 WITH AS (CTE) 和 CACHE TABLE 语句时失败，原因是在 `protect_special_subqueries` 函数中使用了有语法错误的正则表达式。

### 具体问题

1. **WITH AS 格式化崩溃**
   - 位置：`formatter_v4_fixed.py` 第 378 行
   - 错误：`re.PatternError: missing ), unterminated subpattern`
   - 正则：`r'(WITH\s+(?:\w+\s+AS\s*\([^)]+(?:\([^)]*\))*\)\s*,?\s*)+)'`

2. **CACHE TABLE 格式化失败**
   - 位置：`formatter_v4_fixed.py` 第 345 行
   - 类似的正则问题

3. **根本原因**
   - 正则使用 `[^)]+` 模式匹配括号内容
   - 无法处理嵌套括号、复杂 WHERE 子句、函数调用等

---

## 设计方案

### 核心策略

1. **移除有问题的正则表达式**
   - 删除 `protect_special_subqueries` 中的 WITH/CACHE 正则
   - 保留该函数的其他逻辑

2. **实现括号计数解析器**
   - 新增 `extract_balanced_paren_content()` 函数
   - 正确处理嵌套括号、字符串、注释

3. **复用现有格式化逻辑**
   - 递归调用 `_format_sql_structure()`
   - 自动获得 WHERE/JOIN/CASE 等格式化功能

4. **正确计算缩进**
   - SELECT 对齐到开括号位置 + 1
   - 闭括号对齐到开括号位置

---

## 架构设计

### 新增函数

```python
def extract_balanced_paren_content(sql: str, start_pos: int) -> Tuple[str, int]:
    """
    从 start_pos 开始，提取匹配的括号内容

    正确处理：
    - 嵌套括号
    - 字符串（单引号、双引号）
    - 转义字符

    返回: (括号内内容, 结束位置)
    """
```

### 修改的函数

#### `_format_with_statement()`

**输入：** `WITH A AS (SELECT ...), B AS (SELECT ...) SELECT * FROM A`

**处理流程：**
1. 分离 CTE 定义和主查询
2. 使用括号计数解析器提取每个 CTE 的子查询
3. 递归格式化子查询
4. 计算缩进并组装输出

**输出：**
```sql
WITH A AS (
      SELECT ...
     ),
B AS (
      SELECT ...
     )
SELECT *
FROM A
```

#### `_format_cache_table()`

**输入：** `CACHE TABLE B AS (SELECT ...)`

**处理流程：**
1. 使用括号计数解析器提取子查询
2. 递归格式化子查询
3. 计算缩进并组装输出

**输出：**
```sql
CACHE TABLE B AS (
                    SELECT ...
                   )
```

#### `_format_cte_only()`

修复只有 CTE 定义没有主查询的情况（`WITH A AS (...)` 结尾的语句）。

---

## 缩进规则

### WITH AS

```
WITH A AS (
      SELECT aa  ← 开括号位置 + 1
           , bb
      FROM tab_tes
     )  ← 对齐开括号
```

- 开括号位置 = `len("WITH A AS (")`
- SELECT 缩进 = 开括号位置 + 1
- 闭括号缩进 = 开括号位置

### CACHE TABLE

```
CACHE TABLE B AS (
                    SELECT aa  ← 开括号位置 + 1
                         , bb
                    FROM tab_tes
                   )  ← 对齐开括号
```

- 开括号位置 = `len("CACHE TABLE B AS (")`
- SELECT 缩进 = 开括号位置 + 1
- 闭括号缩进 = 开括号位置

---

## 复用现有功能

通过递归调用 `_format_sql_structure()`，WITH AS 和 CACHE TABLE 内的子查询自动获得：

- ✅ SELECT 字段对齐
- ✅ WHERE 条件格式化
- ✅ JOIN 格式化
- ✅ CASE 嵌套缩进
- ✅ 函数调用智能换行
- ✅ IN 列表多行保护
- ✅ 注释对齐

---

## 修改文件

- `spark-sql-optimizer/backend/core/formatter_v4_fixed.py`

### 修改位置

1. **新增函数** (约第 300-350 行)
   - `extract_balanced_paren_content()`

2. **删除代码** (约第 325-384 行)
   - `protect_special_subqueries()` 中的 WITH 和 CACHE TABLE 正则处理

3. **修改函数** (约第 1348-1400 行)
   - `_format_with_statement()`

4. **修改函数** (约第 1403-1470 行)
   - `_format_cte_only()`

5. **修改函数** (约第 1533-1560 行)
   - `_format_cache_table()`

---

## 测试用例

### 输入 1: 简单 WITH AS
```sql
WITH A AS (select aa,bb,cc from tab_tes where aa='1')
```

### 输出 1:
```sql
WITH A AS (
      SELECT aa
           , bb
           , cc
      FROM tab_tes
      WHERE aa = '1'
     )
```

### 输入 2: 复杂 WITH AS（嵌套）
```sql
WITH A AS (select aa,bb,cc from tab_tes where aa='1' and bb='2' or (aa='2' and bb='2' and cc='3'))
```

### 输出 2:
```sql
WITH A AS (
      SELECT aa
           , bb
           , cc
      FROM tab_tes
      WHERE aa = '1'
        AND bb = '2'
        OR (aa = '2'
            AND bb = '2'
            AND cc = '3')
     )
```

### 输入 3: 多个 CTE
```sql
WITH A AS (select id from users), B AS (select order_id from orders)
SELECT * FROM A JOIN B ON A.id = B.user_id
```

### 输出 3:
```sql
WITH A AS (
      SELECT id
      FROM users
     ),
B AS (
      SELECT order_id
      FROM orders
     )
SELECT *
FROM A
JOIN B ON A.id = B.user_id
```

### 输入 4: CACHE TABLE
```sql
CACHE TABLE B AS (select aa,bb,cc from tab_tes where aa='1')
```

### 输出 4:
```sql
CACHE TABLE B AS (
                    SELECT aa
                         , bb
                         , cc
                    FROM tab_tes
                    WHERE aa = '1'
                   )
```

### 输入 5: 包含 CASE WHEN
```sql
WITH A AS (select id, case when type=1 then 'VIP' when type=2 then 'NORMAL' else 'UNKNOWN' end as user_type from users)
```

### 输出 5:
```sql
WITH A AS (
      SELECT id
           , CASE
               WHEN type = 1 THEN 'VIP'
               WHEN type = 2 THEN 'NORMAL'
               ELSE 'UNKNOWN'
             END AS user_type
      FROM users
     )
```

---

## 预期效果

- ✅ WITH AS 语句正常格式化
- ✅ CACHE TABLE 语句正常格式化
- ✅ 复杂嵌套结构正确处理
- ✅ 开闭括号对齐
- ✅ 所有子查询格式化功能自动生效

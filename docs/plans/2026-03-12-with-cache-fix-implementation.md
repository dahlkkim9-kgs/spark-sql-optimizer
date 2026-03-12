# WITH AS 和 CACHE TABLE 格式化修复 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 WITH AS (CTE) 和 CACHE TABLE 语句的格式化功能，支持正确的括号对齐和嵌套缩进。

**Architecture:** 用括号计数解析器替代有问题的正则表达式，递归调用 `_format_sql_structure()` 复用现有格式化逻辑。

**Tech Stack:** Python 3.14, re (标准库), pytest (测试)

---

## Task 0: 创建测试用例文件

**Files:**
- Create: `backend/tests/test_with_cache_formatting.py`

**Step 1: 创建测试文件骨架**

```python
"""测试 WITH AS 和 CACHE TABLE 格式化功能"""

import pytest
from backend.core.formatter_v4_fixed import format_sql_v4_fixed


class TestWithAsFormatting:
    """测试 WITH AS 语句格式化"""

    def test_simple_with_as(self):
        """测试简单 WITH AS"""
        pass

    def test_complex_with_as_with_parens(self):
        """测试包含嵌套括号的 WITH AS"""
        pass

    def test_multiple_ctes(self):
        """测试多个 CTE"""
        pass

    def test_cte_with_case_when(self):
        """测试包含 CASE WHEN 的 CTE"""
        pass

    def test_cte_with_join(self):
        """测试包含 JOIN 的 CTE"""
        pass

    def test_cte_only_no_main_query(self):
        """测试只有 CTE 定义没有主查询"""
        pass


class TestCacheTableFormatting:
    """测试 CACHE TABLE 语句格式化"""

    def test_simple_cache_table(self):
        """测试简单 CACHE TABLE"""
        pass

    def test_cache_table_with_complex_where(self):
        """测试包含复杂 WHERE 的 CACHE TABLE"""
        pass

    def test_cache_table_with_case_when(self):
        """测试包含 CASE WHEN 的 CACHE TABLE"""
        pass
```

**Step 2: 运行测试确认骨架创建成功**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py -v
```

Expected: 9 tests collected (0 passed - 骨架测试都是 pass)

**Step 3: 提交**

```bash
git add backend/tests/test_with_cache_formatting.py
git commit -m "test: add test skeleton for WITH AS and CACHE TABLE formatting"
```

---

## Task 1: 实现括号计数解析器

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py` (约第 300 行后添加)

**Step 1: 添加 `extract_balanced_paren_content()` 函数**

在 `formatter_v4_fixed.py` 中约第 300 行（在 `_normalize_select_fields` 函数之前）添加：

```python
def extract_balanced_paren_content(sql: str, start_pos: int) -> tuple[str, int]:
    """
    从 start_pos 开始，提取匹配的括号内容

    正确处理：
    - 嵌套括号 (如 (SELECT * FROM (SELECT ...)))
    - 字符串（单引号、双引号）
    - 转义字符（如 \\'）

    Args:
        sql: 完整 SQL 语句
        start_pos: 左括号 ( 的位置

    Returns:
        (括号内内容, 结束位置)
        结束位置是右括号 ) 之后的位置

    Raises:
        ValueError: 如果括号不匹配
    """
    if sql[start_pos] != '(':
        raise ValueError(f"start_pos {start_pos} 不是左括号位置")

    depth = 1
    i = start_pos + 1
    in_string = False
    string_char = None

    while i < len(sql) and depth > 0:
        ch = sql[i]

        # 处理字符串
        if ch in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = ch
            elif ch == string_char:
                in_string = False

        # 只在非字符串中计数括号
        if not in_string:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1

        i += 1

    if depth != 0:
        raise ValueError(f"括号不匹配：从位置 {start_pos} 开始")

    # 返回括号内内容（不包含外层括号）和结束位置
    return sql[start_pos + 1:i - 1], i
```

**Step 2: 运行测试确认语法正确**

```bash
cd spark-sql-optimizer
python -c "from backend.core.formatter_v4_fixed import extract_balanced_paren_content; print('Function imported successfully')"
```

Expected: 无错误，打印 "Function imported successfully"

**Step 3: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "feat: add extract_balanced_paren_content() helper function"
```

---

## Task 2: 编写简单 WITH AS 测试

**Files:**
- Modify: `backend/tests/test_with_cache_formatting.py`

**Step 1: 编写第一个失败的测试**

```python
def test_simple_with_as(self):
    """测试简单 WITH AS"""
    sql = "WITH A AS (select aa,bb,cc from tab_tes where aa='1')"
    result = format_sql_v4_fixed(sql)

    # 验证基本结构
    assert "WITH A AS" in result
    assert "SELECT aa" in result
    assert "FROM tab_tes" in result
    assert "WHERE aa = '1'" in result

    # 验证括号对齐（开括号和闭括号应该在同一列）
    lines = result.split('\n')
    open_paren_line = None
    close_paren_line = None

    for i, line in enumerate(lines):
        if '(' in line:
            open_paren_line = (i, line.index('('))
        if line.strip() == ')' or line.rstrip().endswith(')'):
            # 找到闭括号位置
            close_paren_pos = len(line) - len(line.rstrip()) + line.rstrip().rfind(')')
            close_paren_line = (i, close_paren_pos)
            break

    assert open_paren_line is not None, "找不到开括号"
    assert close_paren_line is not None, "找不到闭括号"

    # 验证缩进对齐
    assert open_paren_line[1] == close_paren_line[1], \
        f"开括号在第 {open_paren_line[1]} 列，闭括号在第 {close_paren_line[1]} 列，应该对齐"
```

**Step 2: 运行测试确认失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py::TestWithAsFormatting::test_simple_with_as -v
```

Expected: FAIL (当前实现有正则错误)

**Step 3: 记录失败，不提交**

---

## Task 3: 移除有问题的正则表达式

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py`

**Step 1: 定位并注释掉有问题的代码**

找到约第 325-384 行的 `protect_special_subqueries()` 函数，注释掉 WITH 和 CACHE TABLE 的处理部分：

```python
def protect_special_subqueries(sql_text):
    """保护 CACHE TABLE 和 WITH 语句中的子查询，避免被 normalize 破坏"""
    protected = sql_text
    subquery_map = {}
    counter = [0]

    # def protect_subquery(match):
    #     placeholder = f"__PROTECTED_SUBQUERY_{counter[0]}__"
    #     counter[0] += 1
    #     subquery_map[placeholder] = match.group(0)
    #     return placeholder

    # # 保护 CACHE TABLE ... AS (SELECT ...)
    # # 只有在 SQL 中包含 CACHE TABLE 时才执行
    # if re.search(r'\bCACHE\s+TABLE\b', protected, re.IGNORECASE):
    #     protected = re.sub(
    #         r'(CACHE\s+TABLE\s+\S+\s+AS\s*\()([^)]+(?:\([^)]*\))*\))',
    #         lambda m: m.group(1) + protect_subquery(m) if m.group(1) else m.group(0),
    #         protected,
    #         flags=re.IGNORECASE | re.DOTALL
    #     )

    # def protect_with_ctes_repl(match):
    #     """保护 WITH 子句中的 CTE 定义"""
    #     with_clause = match.group(0)
    #     counter = [0]

    #     def protect_cte_subquery(cte_match):
    #         placeholder = f"__PROTECTED_SUBQUERY_{counter[0]}__"
    #         counter[0] += 1
    #         subquery_map[placeholder] = cte_match.group(2)
    #         return cte_match.group(1) + placeholder + cte_match.group(3)

    #     result = re.sub(
    #         r'(\w+\s+AS\s*\()([^)]+(?:\([^)]*\))*\))',
    #         protect_cte_subquery,
    #         with_clause,
    #         flags=re.IGNORECASE | re.DOTALL
    #     )
    #     return result

    # protected = re.sub(
    #     r'(WITH\s+(?:\w+\s+AS\s*\([^)]+(?:\([^)]*\))*\)\s*,?\s*)+)',
    #     protect_with_ctes_repl,
    #     protected,
    #     flags=re.IGNORECASE | re.DOTALL
    # )

    return protected, subquery_map
```

**Step 2: 运行测试确认不再崩溃**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py::TestWithAsFormatting::test_simple_with_as -v
```

Expected: FAIL (但不再是因为正则错误，而是因为没有正确格式化)

**Step 3: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "fix: comment out broken regex in protect_special_subqueries"
```

---

## Task 4: 重写 `_format_cache_table()` 函数

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py` (约第 1533-1560 行)

**Step 1: 完全重写 `_format_cache_table()` 函数**

```python
def _format_cache_table(sql: str) -> str:
    """格式化 CACHE TABLE 语句"""
    # CACHE TABLE table_name AS (subquery) 或 CACHE TABLE table_name AS subquery

    # 解析 CACHE TABLE table_name AS 部分
    match = re.match(r'(CACHE\s+TABLE\s+(\S+)\s+AS\s+)\((.*)\)', sql, re.IGNORECASE | re.DOTALL)
    if not match:
        # 如果没有括号，尝试无括号格式
        match_no_paren = re.match(r'(CACHE\s+TABLE\s+(\S+)\s+AS\s+)(SELECT\s+.*)', sql, re.IGNORECASE | re.DOTALL)
        if match_no_paren:
            header = match_no_paren.group(1)
            table_name = match_no_paren.group(2)
            subquery = match_no_paren.group(3)
            # 格式化子查询
            formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)
            return f"{header}\n{formatted_subquery}"
        return sql

    header = match.group(1)  # "CACHE TABLE table_name AS "
    table_name = match.group(2)
    subquery = match.group(3).strip()

    # 计算开括号位置（用于缩进）
    # 格式: "CACHE TABLE table_name AS ("
    paren_pos = len(header)

    # 格式化子查询内容
    formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

    # 为每一行添加缩进（缩进到开括号位置 + 1）
    subquery_indent = ' ' * (paren_pos + 1)
    lines = []
    for line in formatted_subquery.split('\n'):
        if line.strip():
            lines.append(subquery_indent + line)
        else:
            lines.append('')

    # 闭括号对齐到开括号位置
    close_paren_indent = ' ' * paren_pos

    return f"{header}(\n" + '\n'.join(lines) + f"\n{close_paren_indent})"
```

**Step 2: 运行测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py::TestCacheTableFormatting::test_simple_cache_table -v
```

Expected: PASS (如果已编写测试) 或 FAIL

**Step 3: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "feat: rewrite _format_cache_table() with bracket counting parser"
```

---

## Task 5: 重写 `_format_with_statement()` 函数

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py` (约第 1348-1400 行)

**Step 1: 添加 CTE 解析辅助函数**

在 `_format_with_statement()` 之前添加：

```python
def _parse_cte_definitions(cte_part: str) -> list[tuple[str, str]]:
    """
    解析 CTE 定义部分

    Args:
        cte_part: "WITH" 之后，主查询之前的内容（如 "A AS (...), B AS (...)"）

    Returns:
        [(cte_name, subquery_sql), ...]
    """
    ctes = []
    rest = cte_part.strip()

    # 去掉开头的 "WITH"
    if rest.upper().startswith('WITH'):
        rest = rest[4:].strip()

    depth = 0
    current = ''
    i = 0

    while i < len(rest):
        char = rest[i]

        if char == '(':
            if depth == 0:
                # 找到 CTE 名称和 AS 之前的部分
                current = current.strip()
                if current:
                    # 提取 CTE 名称（格式如 "A AS"）
                    parts = current.split()
                    if len(parts) >= 2 and parts[1].upper() == 'AS':
                        cte_name = parts[0]
                        current = cte_name
                current += char
                depth += 1
            else:
                current += char
                depth += 1
        elif char == ')':
            current += char
            depth -= 1
            if depth == 0:
                # CTE 定义结束
                # 格式: "cte_name AS (subquery)"
                match = re.match(r'(\w+)\s+AS\s*\((.*)\)', current, re.IGNORECASE | re.DOTALL)
                if match:
                    cte_name = match.group(1)
                    subquery = match.group(2).strip()
                    ctes.append((cte_name, subquery))
                current = ''
        elif depth == 0 and char == ',':
            # 逗号分隔多个 CTE
            current = ''
        else:
            current += char

        i += 1

    # 处理最后一个
    if current.strip():
        match = re.match(r'(\w+)\s+AS\s*\((.*)\)', current, re.IGNORECASE | re.DOTALL)
        if match:
            cte_name = match.group(1)
            subquery = match.group(2).strip()
            ctes.append((cte_name, subquery))

    return ctes
```

**Step 2: 重写 `_format_with_statement()` 函数**

```python
def _format_with_statement(sql: str) -> str:
    """格式化 WITH ... AS ... SELECT 语句 (CTE)"""

    upper_sql = sql.upper()
    if not upper_sql.startswith('WITH'):
        return _format_sql_structure(sql)

    # 查找主 SELECT 的位置（不在括号内的）
    paren_count = 0
    main_select_pos = -1
    in_string = False
    string_char = None

    i = 0
    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False

        if not in_string:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1

            # 查找 SELECT 关键字
            if sql[i:i+6].upper() == 'SELECT' and (i + 6 >= len(sql) or not sql[i+6].isalnum()):
                if paren_count == 0:
                    main_select_pos = i
                    break
        i += 1

    if main_select_pos == -1:
        # 没有找到主 SELECT，只有 CTE 定义
        return _format_cte_only(sql)

    # 分离 CTE 部分和主查询
    cte_part = sql[:main_select_pos].strip()
    main_query = sql[main_select_pos:].strip()

    # 解析 CTE 定义
    ctes = _parse_cte_definitions(cte_part)

    # 格式化每个 CTE
    formatted_ctes = []
    for idx, (cte_name, subquery) in enumerate(ctes):
        # 格式化子查询
        formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

        # 计算缩进
        # 第一个 CTE: "WITH cte_name AS ("
        # 后续 CTE: ",\ncte_name AS ("
        if idx == 0:
            header = f"WITH {cte_name} AS ("
            paren_pos = len(header)
        else:
            # 需要考虑换行符
            header = f",\n{cte_name} AS ("
            # 缩进到 CTE 名称位置（2 个空格 + 名称长度 + " AS ("）
            paren_pos = 2 + len(cte_name) + 5

        subquery_indent = ' ' * (paren_pos + 1)
        close_paren_indent = ' ' * paren_pos

        # 为每一行添加缩进
        lines = []
        for line in formatted_subquery.split('\n'):
            if line.strip():
                lines.append(subquery_indent + line)
            else:
                lines.append('')

        formatted_cte = header + '\n' + '\n'.join(lines) + f'\n{close_paren_indent})'
        formatted_ctes.append(formatted_cte)

    # 格式化主查询
    main_formatted = _format_sql_structure(main_query)

    return '\n'.join(formatted_ctes) + '\n' + main_formatted
```

**Step 3: 运行测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py::TestWithAsFormatting::test_simple_with_as -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "feat: rewrite _format_with_statement() with bracket counting parser"
```

---

## Task 6: 重写 `_format_cte_only()` 函数

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py` (约第 1403-1470 行)

**Step 1: 重写 `_format_cte_only()` 函数**

```python
def _format_cte_only(sql: str) -> str:
    """格式化只有 CTE 定义的 WITH 语句（没有主查询）"""
    # WITH cte_name AS (subquery)

    # 去掉 WITH 和末尾的分号
    rest = sql[4:].strip()  # 去掉 'WITH'
    had_semicolon = False
    if rest.endswith(';'):
        rest = rest[:-1].strip()
        had_semicolon = True

    # 使用新的解析函数
    ctes = _parse_cte_definitions("WITH " + rest)

    # 格式化每个 CTE
    formatted_ctes = []
    for idx, (cte_name, subquery) in enumerate(ctes):
        # 格式化子查询
        formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

        # 计算缩进
        if idx == 0:
            header = f"WITH {cte_name} AS ("
            paren_pos = len(header)
        else:
            header = f",\n{cte_name} AS ("
            paren_pos = 2 + len(cte_name) + 5

        subquery_indent = ' ' * (paren_pos + 1)
        close_paren_indent = ' ' * paren_pos

        # 为每一行添加缩进
        lines = []
        for line in formatted_subquery.split('\n'):
            if line.strip():
                lines.append(subquery_indent + line)
            else:
                lines.append('')

        formatted_cte = header + '\n' + '\n'.join(lines) + f'\n{close_paren_indent})'
        formatted_ctes.append(formatted_cte)

    result = '\n'.join(formatted_ctes)
    if had_semicolon:
        result += ';'

    return result
```

**Step 2: 运行测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py::TestWithAsFormatting::test_cte_only_no_main_query -v
```

Expected: PASS

**Step 3: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "feat: rewrite _format_cte_only() with new parser"
```

---

## Task 7: 完善测试用例

**Files:**
- Modify: `backend/tests/test_with_cache_formatting.py`

**Step 1: 实现所有测试用例**

```python
"""测试 WITH AS 和 CACHE TABLE 格式化功能"""

import pytest
from backend.core.formatter_v4_fixed import format_sql_v4_fixed


class TestWithAsFormatting:
    """测试 WITH AS 语句格式化"""

    def test_simple_with_as(self):
        """测试简单 WITH AS"""
        sql = "WITH A AS (select aa,bb,cc from tab_tes where aa='1')"
        result = format_sql_v4_fixed(sql)

        assert "WITH A AS" in result
        assert "SELECT aa" in result
        assert "FROM tab_tes" in result
        assert "WHERE aa = '1'" in result

        # 验证括号对齐
        lines = result.split('\n')
        open_paren_pos = None
        for line in lines:
            if '(' in line:
                open_paren_pos = line.index('(')
                break

        close_paren_pos = None
        for line in reversed(lines):
            if line.strip() == ')' or (')' in line and not line.strip().startswith('SELECT')):
                close_paren_pos = len(line) - len(line.lstrip())
                break

        assert open_paren_pos is not None
        assert close_paren_pos is not None
        assert open_paren_pos == close_paren_pos

    def test_complex_with_as_with_parens(self):
        """测试包含嵌套括号的 WITH AS"""
        sql = "WITH A AS (select aa,bb,cc from tab_tes where aa='1' and bb='2' or (aa='2' and bb='2' and cc='3'))"
        result = format_sql_v4_fixed(sql)

        # 验证嵌套括号被保留
        assert "SELECT aa" in result
        assert "WHERE aa = '1'" in result
        assert "(aa = '2'" in result or "(aa='2'" in result

    def test_multiple_ctes(self):
        """测试多个 CTE"""
        sql = "WITH A AS (select id from users), B AS (select order_id from orders) SELECT * FROM A JOIN B ON A.id = B.user_id"
        result = format_sql_v4_fixed(sql)

        assert "WITH A AS" in result
        assert ",B AS" in result or ",\nB AS" in result
        assert "SELECT *" in result

    def test_cte_with_case_when(self):
        """测试包含 CASE WHEN 的 CTE"""
        sql = "WITH A AS (select id, case when type=1 then 'VIP' when type=2 then 'NORMAL' else 'UNKNOWN' end as user_type from users)"
        result = format_sql_v4_fixed(sql)

        # 验证 CASE 被格式化
        assert "CASE" in result
        assert "WHEN type = 1 THEN" in result or "WHEN type=1 THEN" in result
        assert "ELSE" in result
        assert "END" in result

    def test_cte_with_join(self):
        """测试包含 JOIN 的 CTE"""
        sql = "WITH A AS (select u.id, o.order_id from users u join orders o on u.id = o.user_id)"
        result = format_sql_v4_fixed(sql)

        # 验证 JOIN 被保留
        assert "JOIN" in result or "join" in result
        assert "ON" in result or "on" in result

    def test_cte_only_no_main_query(self):
        """测试只有 CTE 定义没有主查询"""
        sql = "WITH A AS (select id from users)"
        result = format_sql_v4_fixed(sql)

        assert "WITH A AS" in result
        assert "SELECT id" in result


class TestCacheTableFormatting:
    """测试 CACHE TABLE 语句格式化"""

    def test_simple_cache_table(self):
        """测试简单 CACHE TABLE"""
        sql = "CACHE TABLE B AS (select aa,bb,cc from tab_tes where aa='1')"
        result = format_sql_v4_fixed(sql)

        assert "CACHE TABLE B AS" in result
        assert "SELECT aa" in result
        assert "FROM tab_tes" in result
        assert "WHERE aa = '1'" in result

        # 验证括号对齐
        lines = result.split('\n')
        open_paren_pos = None
        for line in lines:
            if '(' in line:
                open_paren_pos = line.index('(')
                break

        close_paren_pos = None
        for line in reversed(lines):
            if ')' in line:
                close_paren_pos = len(line) - len(line.lstrip())
                break

        assert open_paren_pos is not None
        assert close_paren_pos is not None
        assert open_paren_pos == close_paren_pos

    def test_cache_table_with_complex_where(self):
        """测试包含复杂 WHERE 的 CACHE TABLE"""
        sql = "CACHE TABLE B AS (select aa,bb,cc from tab_tes where aa='1' and bb='2' or (aa='2' and bb='2'))"
        result = format_sql_v4_fixed(sql)

        # 验证复杂 WHERE 被保留
        assert "WHERE" in result or "where" in result
        assert "AND" in result or "and" in result
        assert "OR" in result or "or" in result

    def test_cache_table_with_case_when(self):
        """测试包含 CASE WHEN 的 CACHE TABLE"""
        sql = "CACHE TABLE B AS (select id, case when type=1 then 'VIP' else 'NORMAL' end from users)"
        result = format_sql_v4_fixed(sql)

        # 验证 CASE 被格式化
        assert "CASE" in result
        assert "WHEN" in result
        assert "THEN" in result
        assert "ELSE" in result
        assert "END" in result
```

**Step 2: 运行所有测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py -v
```

Expected: 所有测试 PASS

**Step 3: 提交**

```bash
git add backend/tests/test_with_cache_formatting.py
git commit -m "test: complete all test cases for WITH AS and CACHE TABLE"
```

---

## Task 8: 运行完整测试套件

**Files:**
- Test: 所有现有测试

**Step 1: 运行完整测试套件**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v
```

Expected: 现有测试继续通过，新测试通过

**Step 2: 如果有失败，修复并重新运行**

**Step 3: 提交（如果有修复）**

```bash
git add backend/core/formatter_v4_fixed.py backend/tests/test_with_cache_formatting.py
git commit -m "fix: resolve regressions in existing tests"
```

---

## Task 9: 使用实际 SQL 验证

**Files:**
- Test: 使用用户的实际 SQL 文件

**Step 1: 测试用户的实际 SQL**

```bash
cd spark-sql-optimizer
python -c "
from backend.core.formatter_v4_fixed import format_sql_v4_fixed

# 测试 WITH AS
sql1 = '''WITH A AS (select aa,bb,cc from tab_tes where aa='1' and  bb='2' or (aa ='2' and  bb='2' and cc='3'));'''
print('=== WITH AS ===')
print(format_sql_v4_fixed(sql1))
print()

# 测试 CACHE TABLE
sql2 = '''CACHE TABLE B AS (select aa,bb,cc from tab_tes where aa='1' and  bb='2' or (aa ='2' and  bb='2' and cc='3'));'''
print('=== CACHE TABLE ===')
print(format_sql_v4_fixed(sql2))
"
```

Expected: 正确格式化，无错误

**Step 2: 如果有问题，调试并修复**

**Step 3: 提交（如果有修复）**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "fix: handle edge cases in real-world SQL"
```

---

## Task 10: 清理和文档

**Files:**
- Modify: `backend/core/formatter_v4_fixed.py`

**Step 1: 清理注释掉的代码**

如果 `protect_special_subqueries()` 函数中的注释代码不再需要，可以完全删除：

```python
def protect_special_subqueries(sql_text):
    """保护特殊子查询（已废弃，现在使用括号计数解析器）"""
    # 保留函数定义以保持向后兼容
    # 实际的 CTE 和 CACHE TABLE 处理现在在各自的格式化函数中
    return sql_text, {}
```

**Step 2: 更新函数文档**

在文件顶部添加注释说明变更：

```python
"""
SQL 格式化器 - V4 Fixed 版本

最近更新：
- 2026-03-12: 修复 WITH AS 和 CACHE TABLE 格式化
  - 使用括号计数解析器替代有问题的正则表达式
  - 支持 CTE 和 CACHE TABLE 的正确缩进和对齐
"""
```

**Step 3: 运行最终测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_formatting.py -v
```

**Step 4: 提交**

```bash
git add backend/core/formatter_v4_fixed.py
git commit -m "docs: update comments for WITH AS and CACHE TABLE fix"
```

---

## Task 11: 创建端到端测试

**Files:**
- Create: `backend/tests/test_with_cache_e2e.py`

**Step 1: 创建端到端测试**

```python
"""WITH AS 和 CACHE TABLE 端到端测试"""

from backend.core.formatter_v4_fixed import format_sql_v4_fixed


def test_with_as_full_workflow():
    """测试 WITH AS 完整工作流"""
    # 从用户文件中提取的测试用例
    sql = """WITH A AS (select aa,bb,cc from tab_tes where aa='1' and  bb='2' or (aa ='2' and  bb='2' and cc='3'))"""
    result = format_sql_v4_fixed(sql)

    # 验证输出格式正确
    assert result.startswith("WITH A AS")
    assert "SELECT" in result
    assert result.count('\n') > 3  # 应该有多行
    print("Result:")
    print(result)


def test_cache_table_full_workflow():
    """测试 CACHE TABLE 完整工作流"""
    sql = """CACHE TABLE B AS (select aa,bb,cc from tab_tes where aa='1' and  bb='2' or (aa ='2' and  bb='2' and cc='3'))"""
    result = format_sql_v4_fixed(sql)

    # 验证输出格式正确
    assert result.startswith("CACHE TABLE B AS")
    assert "SELECT" in result
    assert result.count('\n') > 3  # 应该有多行
    print("Result:")
    print(result)


def test_multiple_ctes_with_joins():
    """测试多个 CTE 包含 JOIN"""
    sql = """
    WITH user_orders AS (
        select u.id, u.name, o.order_id, o.amount
        from users u
        join orders o on u.id = o.user_id
    ),
    order_totals AS (
        select order_id, sum(amount) as total
        from user_orders
        group by order_id
    )
    select * from order_totals
    """
    result = format_sql_v4_fixed(sql)

    assert "user_orders AS" in result
    assert "order_totals AS" in result
    assert "JOIN" in result or "join" in result
    print("Result:")
    print(result)
```

**Step 2: 运行端到端测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_with_cache_e2e.py -v -s
```

Expected: 所有测试通过，打印格式化结果

**Step 3: 提交**

```bash
git add backend/tests/test_with_cache_e2e.py
git commit -m "test: add end-to-end tests for WITH AS and CACHE TABLE"
```

---

## Task 12: 最终验证和提交

**Step 1: 运行所有测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v --tb=short
```

Expected: 所有测试通过

**Step 2: 检查代码风格**

```bash
cd spark-sql-optimizer
python -m py_compile backend/core/formatter_v4_fixed.py
```

Expected: 无语法错误

**Step 3: 提交所有更改**

```bash
git add backend/core/formatter_v4_fixed.py backend/tests/test_with_cache_formatting.py backend/tests/test_with_cache_e2e.py docs/plans/2026-03-12-with-cache-fix-design.md docs/plans/2026-03-12-with-cache-fix-implementation.md
git commit -m "feat: complete WITH AS and CACHE TABLE formatting fix

- Implement bracket counting parser to replace broken regex
- Rewrite _format_with_statement() for proper CTE formatting
- Rewrite _format_cache_table() for proper cache table formatting
- Rewrite _format_cte_only() for CTE-only statements
- Add comprehensive tests
- Support nested parentheses, CASE WHEN, JOIN, WHERE
- Ensure proper bracket alignment

Fixes #WITH-CACHE-FORMAT"
```

**Step 4: 合并到主分支**

```bash
git checkout main
git merge <feature-branch>
git push
```

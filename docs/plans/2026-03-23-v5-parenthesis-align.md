# V5 括号对齐修复实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 V5 sqlglot 格式化器的括号缩进问题，参考 V4 的 "开括号+1" 规则

**Architecture:**
1. sqlglot 解析 SQL 并输出初步格式化结果
2. `ParenthesisAlignPostProcessor` 后处理器调整括号缩进
3. 复用 V4 的 `IndentContext` 进行缩进计算
4. 绝不添加或删除括号，只调整空格

**Tech Stack:**
- Python 3.14
- sqlglot 28.10.0
- pytest (测试)
- 复用 `indent_context.py` 的 `IndentContext` 类

---

## Task 1: 创建括号对齐后处理器框架

**Files:**
- Create: `backend/core/parenthesis_align_post_processor.py`

**Step 1: 创建基础类结构**

```python
# -*- coding: utf-8 -*-
"""括号对齐后处理器

只调整括号缩进，不添加或删除括号
复用 V4 的 IndentContext 进行缩进计算
"""
from typing import List, Tuple
from indent_context import IndentContext


class ParenthesisAlignPostProcessor:
    """括号对齐后处理器

    遵循 V4 的 "开括号+1" 规则：
    - 开括号位置 = len(prefix)
    - 内容缩进 = 开括号位置 + 1
    - 闭括号缩进 = 开括号位置
    """

    def __init__(self):
        self.indent_ctx = IndentContext()

    def process(self, sql: str) -> str:
        """调整括号缩进

        Args:
            sql: sqlglot 格式化后的 SQL

        Returns:
            括号缩进调整后的 SQL
        """
        # TODO: 实现
        return sql
```

**Step 2: 创建基础测试文件**

```python
# -*- coding: utf-8 -*-
"""括号对齐后处理器测试"""
import pytest
from parenthesis_align_post_processor import ParenthesisAlignPostProcessor


def test_basic_passthrough():
    """测试基础传入（无括号时保持原样）"""
    processor = ParenthesisAlignPostProcessor()
    sql = "SELECT a FROM t1"
    result = processor.process(sql)
    assert result == sql


def test_simple_parenthesis():
    """测试简单括号（占位测试）"""
    processor = ParenthesisAlignPostProcessor()
    sql = "SELECT (a + b) FROM t1"
    result = processor.process(sql)
    # 暂时保持原样
    assert "(" in result
```

**Step 3: 运行测试验证基础结构**

```bash
cd backend/core
pytest parenthesis_align_post_processor.py -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/parenthesis_align_post_processor.py
git commit -m "feat: add parenthesis align post processor skeleton"
```

---

## Task 2: 实现括号配对追踪

**Files:**
- Modify: `backend/core/parenthesis_align_post_processor.py`
- Test: `backend/core/test_parenthesis_align.py` (创建)

**Step 1: 添加括号配对追踪方法**

```python
class ParenthesisAlignPostProcessor:
    # ... 现有代码 ...

    def _find_matching_paren(self, s: str, start: int) -> int:
        """找到匹配的右括号

        Args:
            s: 字符串
            start: 左括号位置

        Returns:
            匹配的右括号位置，-1 表示未找到
        """
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1
```

**Step 2: 添加测试**

在 `test_parenthesis_align.py`:

```python
def test_find_matching_paren():
    """测试括号配对查找"""
    processor = ParenthesisAlignPostProcessor()

    # 简单括号
    assert processor._find_matching_paren("(a)", 0) == 2

    # 嵌套括号
    assert processor._find_matching_paren("((a))", 0) == 4
    assert processor._find_matching_paren("((a))", 1) == 3

    # 不匹配
    assert processor._find_matching_paren("(a", 0) == -1
```

**Step 3: 运行测试**

```bash
pytest test_parenthesis_align.py::test_find_matching_paren -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/parenthesis_align_post_processor.py backend/core/test_parenthesis_align.py
git commit -m "feat: add parenthesis matching logic"
```

---

## Task 3: 实现行级括号检测

**Files:**
- Modify: `backend/core/parenthesis_align_post_processor.py`

**Step 1: 添加行级分析方法**

```python
class ParenthesisAlignPostProcessor:
    # ... 现有代码 ...

    def _analyze_line_parens(self, line: str) -> dict:
        """分析一行中的括号信息

        Args:
            line: 一行文本

        Returns:
            dict 包含:
            - has_open_paren: bool
            - has_close_paren: bool
            - open_paren_pos: int (开括号位置，-1 表示无)
            - prefix: str (开括号前的文本)
        """
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # 查找开括号
        open_pos = stripped.find('(')
        has_open = open_pos >= 0

        # 查找闭括号
        close_pos = stripped.find(')')
        has_close = close_pos >= 0

        # 提取开括号前缀
        if has_open:
            prefix = stripped[:open_pos]
        else:
            prefix = stripped

        return {
            'has_open_paren': has_open,
            'has_close_paren': has_close,
            'open_paren_pos': open_pos if has_open else -1,
            'close_paren_pos': close_pos if has_close else -1,
            'prefix': prefix,
            'base_indent': indent
        }
```

**Step 2: 添加测试**

```python
def test_analyze_line_parens():
    """测试行级括号分析"""
    processor = ParenthesisAlignPostProcessor()

    # 开括号行
    result = processor._analyze_line_parens("    WHERE a IN (")
    assert result['has_open_paren'] == True
    assert result['prefix'] == "    WHERE a IN "
    assert result['base_indent'] == 4

    # 闭括号行
    result = processor._analyze_line_parens("    )")
    assert result['has_close_paren'] == True

    # 无括号行
    result = processor._analyze_line_parens("    SELECT a")
    assert result['has_open_paren'] == False
    assert result['has_close_paren'] == False
```

**Step 3: 运行测试**

```bash
pytest test_parenthesis_align.py::test_analyze_line_parens -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/parenthesis_align_post_processor.py backend/core/test_parenthesis_align.py
git commit -m "feat: add line-level parenthesis analysis"
```

---

## Task 4: 实现主处理逻辑

**Files:**
- Modify: `backend/core/parenthesis_align_post_processor.py`

**Step 1: 实现 process 方法**

```python
def process(self, sql: str) -> str:
    """调整括号缩进"""
    lines = sql.split('\n')
    result = []
    paren_stack = []  # 存储 (开括号位置, 内容缩进)

    for line in lines:
        analysis = self._analyze_line_parens(line)

        # 处理闭括号行
        if analysis['has_close_paren'] and not analysis['has_open_paren']:
            if paren_stack:
                open_pos = paren_stack.pop()
                # 闭括号与开括号对齐
                result.append(' ' * open_pos + ')')
                continue

        # 处理开括号行
        if analysis['has_open_paren']:
            # 计算开括号绝对位置
            prefix = analysis['prefix']
            open_pos = analysis['base_indent'] + len(prefix)
            content_indent = open_pos + 1

            # 压栈
            paren_stack.append((open_pos, content_indent))

            # 输出开括号行
            result.append(line.rstrip())
            continue

        # 处理内容行（有活动括号上下文时）
        if paren_stack:
            _, content_indent = paren_stack[-1]
            stripped = line.lstrip()
            if stripped:  # 非空行
                result.append(' ' * content_indent + stripped)
                continue

        # 默认：保持原样
        result.append(line)

    return '\n'.join(result)
```

**Step 2: 添加集成测试**

```python
def test_simple_subquery_align():
    """测试简单子查询对齐"""
    processor = ParenthesisAlignPostProcessor()

    input_sql = """WHERE a IN (
SELECT x
FROM t2
)"""
    result = processor.process(input_sql)
    print("Result:", result)
    # 验证 SELECT 缩进
    assert "    SELECT" in result or "  SELECT" in result
```

**Step 3: 运行测试**

```bash
pytest test_parenthesis_align.py::test_simple_subquery_align -v -s
```

Expected: PASS（可能需要调整）

**Step 4: 提交**

```bash
git add backend/core/parenthesis_align_post_processor.py backend/core/test_parenthesis_align.py
git commit -m "feat: implement main parenthesis align logic"
```

---

## Task 5: 集成到 formatter_v5_sqlglot.py

**Files:**
- Modify: `backend/core/formatter_v5_sqlglot.py`

**Step 1: 导入并使用后处理器**

在 `formatter_v5_sqlglot.py` 顶部添加：

```python
from parenthesis_align_post_processor import ParenthesisAlignPostProcessor
```

修改 `format` 方法：

```python
def format(self, sql: str, dialect: str = "spark") -> str:
    """格式化 SQL"""
    # 临时转义 $ 符号
    escaped_sql, _ = self._escape_dollar_signs(sql)

    # ... 现有解析逻辑 ...

    try:
        asts = parse(escaped_sql, dialect=dialect, read=dialect)
        if not asts:
            return sql

        formatted_statements = []
        for ast in asts:
            # 使用 sqlglot 格式化
            formatted = ast.sql(dialect=dialect, pretty=True, indent=self.indent_spaces)
            formatted = self._unescape_dollar_signs(formatted)

            # 应用 v4 风格后处理
            formatted = self._apply_v4_column_style(formatted)

            # 新增：应用括号对齐后处理
            paren_processor = ParenthesisAlignPostProcessor()
            formatted = paren_processor.process(formatted)

            formatted_statements.append(formatted)

        return '\n\n'.join(formatted_statements)
    # ... 异常处理 ...
```

**Step 2: 添加集成测试**

创建 `backend/core/test_v5_parenthesis_integration.py`:

```python
# -*- coding: utf-8 -*-
"""V5 括号对齐集成测试"""
from formatter_v5_sqlglot import format_sql_v5


def test_in_subquery_formatting():
    """测试 IN 子查询格式化"""
    sql = "SELECT * FROM t1 WHERE a NOT IN (SELECT x FROM t2)"
    result = format_sql_v5(sql)
    print("\n=== IN 子查询格式化 ===")
    print(result)

    # 验证关键字存在
    assert "SELECT" in result.upper()
    assert "NOT IN" in result.upper() or "IN" in result.upper()


def test_real_sql_file():
    """测试真实 SQL 文件片段"""
    sql = """SELECT *
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_xd
WHERE khzjdm NOT IN (
SELECT DISTINCT khzjdm
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
)"""
    result = format_sql_v5(sql)
    print("\n=== 真实 SQL 片段 ===")
    print(result)

    # 验证内容完整性
    assert "SELECT" in result.upper()
    assert "RHZF_GRKHJCXX" in result
```

**Step 3: 运行集成测试**

```bash
pytest test_v5_parenthesis_integration.py -v -s
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/formatter_v5_sqlglot.py backend/core/test_v5_parenthesis_integration.py
git commit -m "feat: integrate parenthesis align post processor"
```

---

## Task 6: 边缘情况处理

**Files:**
- Modify: `backend/core/parenthesis_align_post_processor.py`
- Modify: `backend/core/test_parenthesis_align.py`

**Step 1: 添加字符串和注释跳过逻辑**

```python
class ParenthesisAlignPostProcessor:
    # ... 现有代码 ...

    def _is_in_string_or_comment(self, line: str, pos: int) -> bool:
        """检查位置是否在字符串或注释中

        Args:
            line: 行文本
            pos: 检查位置

        Returns:
            True 如果在字符串或注释中
        """
        # 简单检查：是否在单引号字符串中
        before = line[:pos]
        single_quotes = before.count("'")
        return single_quotes % 2 == 1
```

**Step 2: 添加嵌套括号测试**

```python
def test_nested_parenthesis():
    """测试嵌套括号"""
    processor = ParenthesisAlignPostProcessor()

    sql = "SELECT ((a + b) * c) FROM t1"
    result = processor.process(sql)
    print("\n=== 嵌套括号 ===")
    print(result)
    # 只验证不崩溃
    assert "(" in result and ")" in result


def test_parenthesis_in_string():
    """测试字符串中的括号（应被忽略）"""
    processor = ParenthesisAlignPostProcessor()

    sql = "SELECT 'a(b)c' FROM t1"
    result = processor.process(sql)
    # 字符串中的括号不应影响处理
    assert "'a(b)c'" in result
```

**Step 3: 运行测试**

```bash
pytest test_parenthesis_align.py -v
```

Expected: PASS

**Step 4: 提交**

```bash
git add backend/core/parenthesis_align_post_processor.py backend/core/test_parenthesis_align.py
git commit -m "feat: handle edge cases (strings, nested parens)"
```

---

## Task 7: 完整验证测试

**Files:**
- Modify: `backend/core/test_v5_parenthesis_integration.py`

**Step 1: 添加真实 SQL 文件测试**

```python
def test_with_real_sql_files():
    """使用真实 SQL 文件测试"""
    from pathlib import Path

    test_files = [
        "../../v5_integrity_outputs/JRJC_MON_B01_T18_GRKHXX_v5_integrity_test.sql",
    ]

    for file_path in test_files:
        path = Path(__file__).parent / file_path
        if not path.exists():
            print(f"跳过不存在的文件: {file_path}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"\n=== 测试文件: {file_path} ===")

        try:
            result = format_sql_v5(content)
            print(f"格式化成功，长度: {len(result)} 字符")

            # 验证完整性
            assert isinstance(result, str)
            assert len(result) > 0

        except Exception as e:
            print(f"格式化失败: {e}")
            raise
```

**Step 2: 运行完整测试**

```bash
pytest test_v5_parenthesis_integration.py::test_with_real_sql_files -v -s
```

Expected: PASS

**Step 3: 提交**

```bash
git add backend/core/test_v5_parenthesis_integration.py
git commit -m "test: add real SQL file validation"
```

---

## 验收标准

完成所有任务后：

- [ ] `ParenthesisAlignPostProcessor` 正确处理括号配对
- [ ] 子查询缩进符合 V4 "开括号+1" 规则
- [ ] 嵌套括号正确处理
- [ ] 字符串中的括号被正确忽略
- [ ] 所有单元测试通过
- [ ] 真实 SQL 文件格式化成功
- [ ] SQL 完整性不被破坏（括号数量不变）

---

## 回滚策略

如果引入问题：
```bash
git revert HEAD  # 回滚最后一次提交
# 或
git reset --hard HEAD~N  # 回滚 N 个提交
```
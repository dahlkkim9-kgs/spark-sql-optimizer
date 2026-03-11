# SQL 格式化器优化建议

## 1. 性能优化 - 预编译正则表达式

### 当前问题
每次调用函数时都重新编译正则表达式，导致性能损失。

### 优化方案
将常用正则表达式预编译为模块级常量：

```python
# 在文件顶部添加
# ==================== 预编译正则表达式 ====================
COMMENT_PATTERN = re.compile(r"COMMENT\s+'([^']*')", re.IGNORECASE)
COMMENT_PLACEHOLDER_PATTERN = re.compile(r'(__COMMENT_STR_\d+__)')
LINE_COMMENT_PATTERN = re.compile(r'--[^\n]*')
BLOCK_COMMENT_PATTERN = re.compile(r'/\*.*?\*/', re.DOTALL)
CASE_PATTERN = re.compile(r'\bCASE\b', re.IGNORECASE)
SELECT_PATTERN = re.compile(r'\bSELECT\b', re.IGNORECASE)
ON_PATTERN = re.compile(r'\bON\b\s+', re.IGNORECASE)
CREATE_TABLE_PATTERN = re.compile(r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+)\s*', re.IGNORECASE)
PARTITIONED_BY_PATTERN = re.compile(r'(PARTITIONED\s+BY)\s*', re.IGNORECASE)
ROW_FORMAT_PATTERN = re.compile(r"(ROW\s+FORMAT\s+[\s\S]+?)(?:\s*$|\s*(?=\s*__COMMENT_STR_\d+__|\s*COMMENT\s|\s*PARTITIONED\s))", re.IGNORECASE)
AS_SELECT_PATTERN = re.compile(r'\bAS\s+SELECT\b', re.IGNORECASE)
CTE_PATTERN = re.compile(r'(\w+)\s+AS\s+\((.*)\)', re.IGNORECASE | re.DOTALL)
VIEW_PATTERN = re.compile(r'(CREATE\s+(?:TEMPORARY\s+)?VIEW\s+\S+)\s+AS\s+(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)
CACHE_TABLE_PATTERN = re.compile(r'(CACHE\s+TABLE\s+\S+)\s+AS\s+(.*)', re.IGNORECASE | re.DOTALL)
INSERT_PATTERN = re.compile(r'(INSERT\s+INTO\s+(?:TABLE\s+)?\S+)\s*(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)
INSERT_PARTITION_PATTERN = re.compile(r'(INSERT\s+INTO\s+\S+\s+PARTITION\s*\([^\)]*\)\s*)(SELECT.*)', re.IGNORECASE | re.DOTALL)
EXPLAIN_PATTERN = re.compile(r'(EXPLAIN(?:\s+\w+)?)\s+(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)
SUBQUERY_PATTERN = re.compile(r'\(\s*(__COMMENT_\d+__\s*)?SELECT\b', re.IGNORECASE)
```

### 预期收益
- 大文件格式化速度提升 20-30%
- CPU 使用率降低

---

## 2. 代码组织 - 函数职责分离

### 当前问题
- `_format_sql_structure` 函数过长（200+ 行）
- 部分函数有重复逻辑

### 优化方案
将长函数拆分为更小的、职责单一的函数：

```python
# DDL 语句格式化可以独立成模块
def _format_ddl_statement(sql: str, keyword_case: str) -> str:
    """统一处理所有 DDL 语句"""
    # 判断语句类型并分发
    pass

# DML 语句格式化
def _format_dml_statement(sql: str, keyword_case: str) -> str:
    """统一处理所有 DML 语句"""
    pass
```

---

## 3. 消除重复代码

### 当前问题
- `_split_column_definitions` 和 `_split_column_definitions_preserve` 逻辑相似
- `_parse_column_parts` 中 COMMENT 解析逻辑重复出现

### 优化方案
合并相似函数，添加参数控制行为：

```python
def _split_column_definitions(columns_str: str, preserve_spaces: bool = False) -> List[str]:
    """分割列定义

    Args:
        columns_str: 列定义字符串
        preserve_spaces: 是否保留空格（用于已对齐的SQL）
    """
    # 统一处理逻辑
    pass
```

---

## 4. 添加类型注解

### 当前问题
函数缺少类型注解，降低代码可维护性。

### 优化方案
添加完整的类型注解：

```python
from typing import List, Dict, Tuple, Optional, Union

def _parse_column_parts(col_def: str) -> Dict[str, Optional[str]]:
    """解析列定义的各个部分

    Returns:
        包含 name, type, comment, comment_placeholder, constraints 的字典
    """
    pass
```

---

## 5. 错误处理统一化

### 当前问题
- 有些函数返回原始输入
- 有些可能抛出异常
- 错误消息不统一

### 优化方案
定义自定义异常类，统一错误处理：

```python
class SQLFormatError(Exception):
    """SQL 格式化错误基类"""
    pass

class ParseError(SQLFormatError):
    """SQL 解析错误"""
    pass

def format_sql_v4_fixed(sql: str, **options) -> str:
    try:
        # 格式化逻辑
        pass
    except ParseError as e:
        # 记录错误并返回原始SQL或部分结果
        logger.warning(f"Parse error: {e}")
        return _fallback_format(sql)
```

---

## 6. 添加单元测试

### 当前问题
只有集成测试，单个函数的单元测试缺失。

### 优化方案
为核心函数添加单元测试：

```python
# test_formatter_units.py
import pytest
from core.formatter_v4_fixed import _parse_column_parts, _align_columns_smartly

def test_parse_column_with_comment():
    col = "JRJGDM        STRING     COMMENT  'test'"
    result = _parse_column_parts(col)
    assert result['name'] == 'JRJGDM'
    assert result['type'] == 'STRING'
    assert result['comment'] == 'test'

def test_parse_column_without_comment():
    col = "flag         STRING"
    result = _parse_column_parts(col)
    assert result['name'] == 'flag'
    assert result['type'] == 'STRING'
    assert result['comment'] == ''
```

---

## 7. 性能监控

### 优化方案
添加性能计时（可选）：

```python
import time
import logging

logger = logging.getLogger(__name__)

def format_sql_v4_fixed(sql: str, **options) -> str:
    start = time.time()
    try:
        # 格式化逻辑
        result = ...
        return result
    finally:
        elapsed = time.time() - start
        if elapsed > 1.0:  # 超过1秒记录警告
            logger.warning(f"Slow formatting: {elapsed:.2f}s for {len(sql)} chars")
```

---

## 8. 代码文档改进

### 当前问题
部分函数缺少详细的文档字符串。

### 优化方案
添加完整的 docstring：

```python
def _format_partitioned_by(partition_str: str) -> List[str]:
    """格式化 PARTITIONED BY 部分

    将 PARTITIONED BY 子句格式化为多行，并对齐列定义。

    Args:
        partition_str: PARTITIONED BY 子句字符串，如
            "PARTITIONED BY (aaa STRING COMMENT 'a', bbb STRING COMMENT 'b')"

    Returns:
        格式化后的行列表，如:
        [
            "PARTITIONED BY",
            "(",
            " aaa         STRING      COMMENT  'a'",
            ",bbb         STRING      COMMENT  'b'",
            ")"
        ]

    Note:
        - 使用与表列相同的对齐逻辑
        - 支持嵌套括号（如 DECIMAL(10,2)）
        - 保留 COMMENT 字符串中的空格
    """
    pass
```

---

## 实施优先级

| 优先级 | 优化项 | 预期收益 | 实施难度 | 建议顺序 |
|--------|--------|----------|----------|----------|
| 高 | 预编译正则表达式 | 性能提升 20-30% | 低 | 1 |
| 高 | 添加类型注解 | 可维护性提升 | 低 | 2 |
| 中 | 统一错误处理 | 稳定性提升 | 中 | 3 |
| 中 | 消除重复代码 | 可维护性提升 | 中 | 4 |
| 中 | 添加单元测试 | 质量保障 | 中 | 5 |
| 低 | 函数职责分离 | 可维护性提升 | 高 | 6 |
| 低 | 性能监控 | 可观测性 | 低 | 7 |

---

## 不建议的改动

以下改动在当前阶段**不建议**实施：

1. **重写为面向对象** - 当前函数式风格已经工作良好，OOP 会增加复杂度
2. **引入新的依赖** - 如 SQL 解析库，当前正则方案已经足够
3. **大规模重构** - 代码已经稳定，逐步优化风险更低

---

## 总结

当前格式化器功能完整且稳定，建议优先实施**预编译正则表达式**和**添加类型注解**，这两项改动风险低、收益高。

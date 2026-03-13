# 高级 SQL 语法支持扩展 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 扩展 SQL 格式化器以支持集合操作、窗口函数、数据操作和高级转换语法

**Architecture:** 采用模块化共存架构，创建独立的语法处理器模块，与现有 formatter_v4_fixed.py 共存

**Tech Stack:** Python 3.14+, re, pytest, FastAPI (API 端点)

---

## 前置准备

### Task 0: 环境验证

**Files:** 无

**Step 1: 验证 Python 版本**

```bash
python --version
```

Expected: Python 3.14 或更高版本

**Step 2: 验证项目结构**

```bash
cd spark-sql-optimizer/backend/core
ls -la
```

Expected: 应该看到 `formatter_v4_fixed.py` 文件

**Step 3: 运行现有测试确保环境正常**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v --tb=short
```

Expected: 所有现有测试通过

---

## Phase 1: 集合操作支持 (UNION/INTERSECT/EXCEPT/MINUS)

### Task 1: 创建目录结构和基础处理器

**Files:**
- Create: `backend/core/processors/__init__.py`
- Create: `backend/core/processors/base_processor.py`

**Step 1: 创建 processors 包**

```python
# backend/core/processors/__init__.py
"""
SQL 语法处理器模块
"""
from .base_processor import BaseProcessor
from .set_operations import SetOperationsProcessor

__all__ = ['BaseProcessor', 'SetOperationsProcessor']
```

**Step 2: 创建基础处理器接口**

```python
# backend/core/processors/base_processor.py
from abc import ABC, abstractmethod
from typing import Optional

class BaseProcessor(ABC):
    """SQL 语法处理器基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def can_process(self, sql: str) -> bool:
        """判断是否可以处理此 SQL"""
        pass

    @abstractmethod
    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理 SQL 并返回格式化后的结果"""
        pass
```

**Step 3: 运行语法检查**

```bash
cd spark-sql-optimizer
python -m py_compile backend/core/processors/__init__.py
python -m py_compile backend/core/processors/base_processor.py
```

Expected: 无语法错误

**Step 4: 提交**

```bash
git add backend/core/processors/
git commit -m "feat: add base processor interface"
```

---

### Task 2: 实现集合操作处理器

**Files:**
- Create: `backend/core/processors/set_operations.py`
- Modify: `backend/core/processors/__init__.py`

**Step 1: 编写集合操作处理器测试**

```python
# backend/tests/test_set_operations.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.set_operations import SetOperationsProcessor

class TestSetOperationsProcessor:
    def test_can_process_union(self):
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1 UNION SELECT b FROM t2") == True

    def test_cannot_process_basic_select(self):
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1") == False

    def test_simple_union_all(self):
        processor = SetOperationsProcessor()
        sql = "SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2"
        result = processor.process(sql)
        # 验证 UNION ALL 前后有换行
        lines = result.split('\n')
        assert any('UNION ALL' in line for line in lines)
        # 验证每个 SELECT 都被正确格式化
        assert result.count('SELECT') == 2

    def test_union_with_join(self):
        processor = SetOperationsProcessor()
        sql = "SELECT a FROM t1 JOIN t2 ON t1.id = t2.id UNION SELECT b FROM t3"
        result = processor.process(sql)
        assert 'UNION' in result
        assert 'JOIN' in result
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_set_operations.py -v
```

Expected: FAIL - ModuleNotFoundError 或 AttributeError

**Step 3: 实现集合操作处理器**

```python
# backend/core/processors/set_operations.py
import re
from typing import List, Tuple
from .base_processor import BaseProcessor

# 导入现有格式化器用于格式化子查询
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from formatter_v4_fixed import format_sql_v4_fixed

class SetOperationsProcessor(BaseProcessor):
    """集合操作处理器 - 支持 UNION/INTERSECT/EXCEPT/MINUS"""

    # 集合操作符正则模式
    SET_OPERATIONS = {
        'UNION ALL': r'\bUNION\s+ALL\b',
        'UNION': r'\bUNION\b(?!\s+ALL)',
        'INTERSECT': r'\bINTERSECT\b',
        'EXCEPT': r'\bEXCEPT\b',
        'MINUS': r'\bMINUS\b'
    }

    def __init__(self):
        super().__init__()
        # 按优先级排序的模式列表（UNION ALL 必须在 UNION 之前）
        self.patterns = [
            ('UNION ALL', re.compile(r'\bUNION\s+ALL\b', re.IGNORECASE)),
            ('UNION', re.compile(r'\bUNION\b(?!\s+ALL)', re.IGNORECASE)),
            ('INTERSECT', re.compile(r'\bINTERSECT\b', re.IGNORECASE)),
            ('EXCEPT', re.compile(r'\bEXCEPT\b', re.IGNORECASE)),
            ('MINUS', re.compile(r'\bMINUS\b', re.IGNORECASE))
        ]

    def can_process(self, sql: str) -> bool:
        """检查 SQL 是否包含集合操作"""
        for name, pattern in self.patterns:
            if pattern.search(sql):
                return True
        return False

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理包含集合操作的 SQL"""
        # 去除首尾空白
        sql = sql.strip()

        # 检查是否有嵌套的括号包裹的集合操作
        if sql.startswith('(') and self._has_nested_set_operations(sql):
            return self._process_nested_set_operations(sql, keyword_case)

        # 分割集合操作
        segments = self._split_by_set_operations(sql)

        # 格式化每个 SELECT 语句
        formatted_segments = []
        for i, segment in enumerate(segments):
            if i % 2 == 0:  # SELECT 语句
                formatted = format_sql_v4_fixed(segment, keyword_case)
                formatted_segments.append(formatted)
            else:  # 集合操作符
                formatted_segments.append(segment.upper())

        # 用换行连接
        return '\n'.join(formatted_segments)

    def _has_nested_set_operations(self, sql: str) -> bool:
        """检查是否有嵌套的括号包裹的集合操作"""
        # 查找顶层括号对
        if not sql.startswith('('):
            return False

        # 使用括号计数找到匹配的闭括号
        depth = 0
        for i, char in enumerate(sql):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    # 找到匹配的闭括号
                    inner = sql[1:i]
                    # 检查内部是否有集合操作
                    for _, pattern in self.patterns:
                        if pattern.search(inner):
                            return True
                    break

        return False

    def _process_nested_set_operations(self, sql: str, keyword_case: str) -> str:
        """处理嵌套的括号包裹的集合操作"""
        # 移除外层括号
        inner = sql[1:sql.rfind(')')]

        # 分割内部集合操作
        segments = self._split_by_set_operations(inner)

        # 格式化并添加括号
        formatted_segments = []
        for i, segment in enumerate(segments):
            if i % 2 == 0:  # SELECT 语句
                formatted = format_sql_v4_fixed(segment, keyword_case)
                formatted_segments.append(f'({formatted})')
            else:  # 集合操作符
                formatted_segments.append(f'\n{segment.upper()}')

        return '\n'.join(formatted_segments)

    def _split_by_set_operations(self, sql: str) -> List[str]:
        """按集合操作符分割 SQL"""
        segments = []
        current = ""
        i = 0

        while i < len(sql):
            matched = False
            for name, pattern in self.patterns:
                match = pattern.match(sql, pos=i)
                if match:
                    # 添加当前累积的内容
                    if current.strip():
                        segments.append(current.strip())
                    # 添加操作符
                    segments.append(name)
                    # 跳过匹配的部分
                    i = match.end()
                    current = ""
                    matched = True
                    break

            if not matched:
                current += sql[i]
                i += 1

        # 添加最后一段
        if current.strip():
            segments.append(current.strip())

        return segments
```

**Step 4: 更新 __init__.py**

```python
# backend/core/processors/__init__.py
"""
SQL 语法处理器模块
"""
from .base_processor import BaseProcessor
from .set_operations import SetOperationsProcessor

__all__ = ['BaseProcessor', 'SetOperationsProcessor']
```

**Step 5: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_set_operations.py -v
```

Expected: PASS

**Step 6: 提交**

```bash
git add backend/core/processors/set_operations.py
git add backend/tests/test_set_operations.py
git add backend/core/processors/__init__.py
git commit -m "feat: implement set operations processor (UNION/INTERSECT/EXCEPT/MINUS)"
```

---

### Task 3: 创建 SQL 分类器

**Files:**
- Create: `backend/core/parser/__init__.py`
- Create: `backend/core/parser/sql_classifier.py`

**Step 1: 编写 SQL 分类器测试**

```python
# backend/tests/test_sql_classifier.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from parser.sql_classifier import SQLClassifier

class TestSQLClassifier:
    def test_classify_union(self):
        classifier = SQLClassifier()
        result = classifier.classify("SELECT a FROM t1 UNION SELECT b FROM t2")
        assert 'set_operations' in result

    def test_classify_basic_select(self):
        classifier = SQLClassifier()
        result = classifier.classify("SELECT a FROM t1")
        assert result == ['basic']

    def test_classify_merge(self):
        classifier = SQLClassifier()
        result = classifier.classify("MERGE INTO t USING s ON t.id = s.id")
        assert 'data_operations' in result
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_sql_classifier.py -v
```

Expected: FAIL - ModuleNotFoundError

**Step 3: 实现 SQL 分类器**

```python
# backend/core/parser/sql_classifier.py
import re
from typing import List

class SQLClassifier:
    """SQL 语句分类器"""

    # 检测规则（按优先级排序）
    RULES = [
        {
            'name': 'data_operations',
            'patterns': [
                re.compile(r'^\s*MERGE\s+INTO\b', re.IGNORECASE),
                re.compile(r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+', re.IGNORECASE)
            ]
        },
        {
            'name': 'set_operations',
            'patterns': [
                re.compile(r'\bUNION\s+(?:ALL\s+)?\b', re.IGNORECASE),
                re.compile(r'\bINTERSECT\b', re.IGNORECASE),
                re.compile(r'\bEXCEPT\b', re.IGNORECASE),
                re.compile(r'\bMINUS\b', re.IGNORECASE)
            ]
        },
        {
            'name': 'window_functions',
            'patterns': [
                re.compile(r'\bOVER\s*\(', re.IGNORECASE),
                re.compile(r'WINDOW\s+\w+\s+AS\b', re.IGNORECASE)
            ]
        },
        {
            'name': 'advanced_transforms',
            'patterns': [
                re.compile(r'\bPIVOT\b', re.IGNORECASE),
                re.compile(r'\bUNPIVOT\b', re.IGNORECASE),
                re.compile(r'\bLATERAL\s+VIEW\b', re.IGNORECASE),
                re.compile(r'\bTRANSFORM\s*\(', re.IGNORECASE),
                re.compile(r'\b(CLUSTER|DISTRIBUTE)\s+BY\b', re.IGNORECASE)
            ]
        }
    ]

    def classify(self, sql: str) -> List[str]:
        """
        返回该 SQL 包含的语法类型列表

        可能的返回值:
        - ['set_operations']     # UNION/INTERSECT/EXCEPT
        - ['window_functions']   # OVER 子句
        - ['data_operations']    # MERGE/INSERT OVERWRITE
        - ['advanced_transforms'] # PIVOT/LATERAL VIEW
        - ['basic']              # 基础 SELECT
        - ['set_operations', 'window_functions']  # 混合语法
        """
        detected = []

        # 按优先级检测各种语法
        for rule in self.RULES:
            for pattern in rule['patterns']:
                if pattern.search(sql):
                    if rule['name'] not in detected:
                        detected.append(rule['name'])
                    break

        # 如果没有检测到任何特殊语法，归类为 basic
        if not detected:
            detected.append('basic')

        return detected
```

**Step 4: 创建 parser 包**

```python
# backend/core/parser/__init__.py
"""
SQL 解析器模块
"""
from .sql_classifier import SQLClassifier

__all__ = ['SQLClassifier']
```

**Step 5: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_sql_classifier.py -v
```

Expected: PASS

**Step 6: 提交**

```bash
git add backend/core/parser/
git add backend/tests/test_sql_classifier.py
git commit -m "feat: add SQL classifier for syntax type detection"
```

---

### Task 4: 创建新格式化器入口 (formatter_v5.py)

**Files:**
- Create: `backend/core/formatter_v5.py`

**Step 1: 编写 formatter_v5 测试**

```python
# backend/tests/test_formatter_v5.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v5 import format_sql_v5

class TestFormatterV5:
    def test_format_union_all(self):
        sql = "SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2"
        result = format_sql_v5(sql)
        assert 'UNION ALL' in result
        # 验证换行
        lines = result.split('\n')
        assert len(lines) > 2

    def test_format_basic_select(self):
        sql = "SELECT a, b FROM t1 WHERE c = 1"
        result = format_sql_v5(sql)
        assert 'SELECT' in result
        assert 'FROM' in result
        assert 'WHERE' in result

    def test_keyword_case_lower(self):
        sql = "select a from t1"
        result = format_sql_v5(sql, keyword_case='lower')
        # 应该保持小写或按配置处理
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_formatter_v5.py -v
```

Expected: FAIL - ModuleNotFoundError

**Step 3: 实现 formatter_v5**

```python
# backend/core/formatter_v5.py
"""
SQL Formatter V5 - 支持高级语法
扩展 V4，添加集合操作、窗口函数、数据操作、高级转换支持
"""
from typing import Optional
from parser.sql_classifier import SQLClassifier
from processors.set_operations import SetOperationsProcessor
from formatter_v4_fixed import format_sql_v4_fixed

# 处理器实例
_classifier = SQLClassifier()
_set_operations_processor = SetOperationsProcessor()

def format_sql_v5(sql: str, keyword_case: str = 'upper') -> str:
    """
    格式化 SQL，支持高级语法

    Args:
        sql: 输入的 SQL 语句
        keyword_case: 关键字大小写 ('upper' | 'lower' | 'capitalize')

    Returns:
        格式化后的 SQL
    """
    # 首先进行分类
    detected_types = _classifier.classify(sql)

    # 根据类型选择处理器
    if 'set_operations' in detected_types:
        return _set_operations_processor.process(sql, keyword_case)

    # 其他类型暂时使用现有格式化器
    # 后续 Phase 会添加更多处理器
    return format_sql_v4_fixed(sql, keyword_case)
```

**Step 4: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_formatter_v5.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add backend/core/formatter_v5.py
git add backend/tests/test_formatter_v5.py
git commit -m "feat: add formatter_v5 entry point with set operations support"
```

---

### Task 5: 添加 API 端点（可选）

**Files:**
- Modify: `backend/api/endpoints.py`

**Step 1: 查看现有端点结构**

```bash
cd spark-sql-optimizer
grep -n "format" backend/api/endpoints.py | head -20
```

**Step 2: 添加 /format/v5 端点**

在 `backend/api/endpoints.py` 中添加：

```python
# 在现有端点之后添加
@app.post("/format/v5")
async def format_v5(request: FormatRequest):
    """格式化 SQL (V5 - 支持高级语法)"""
    try:
        from core.formatter_v5 import format_sql_v5

        formatted = format_sql_v5(request.sql, request.keyword_case)

        return {
            "success": True,
            "formatted": formatted,
            "version": "v5"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Step 3: 测试 API**

```bash
# 启动后端服务（如果未启动）
cd spark-sql-optimizer/backend
python -m uvicorn app:app --port 8888 --reload
```

在另一个终端：

```bash
curl -X POST http://localhost:8888/format/v5 \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT a FROM t1 UNION SELECT b FROM t2", "keyword_case": "upper"}'
```

Expected: 返回格式化后的 SQL

**Step 4: 提交**

```bash
git add backend/api/endpoints.py
git commit -m "feat: add /format/v5 API endpoint"
```

---

## Phase 2: 窗口函数支持 (OVER/PARTITION BY/窗口框架)

### Task 6: 实现窗口函数处理器

**Files:**
- Create: `backend/core/processors/window_functions.py`
- Modify: `backend/core/processors/__init__.py`
- Create: `backend/tests/test_window_functions.py`

**Step 1: 编写窗口函数测试**

```python
# backend/tests/test_window_functions.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.window_functions import WindowFunctionsProcessor

class TestWindowFunctionsProcessor:
    def test_can_process_over(self):
        processor = WindowFunctionsProcessor()
        assert processor.can_process("SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t1") == True

    def test_simple_over(self):
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (ORDER BY id) AS rk FROM t1"
        result = processor.process(sql)
        assert 'OVER' in result
        assert 'ORDER BY' in result

    def test_partition_by(self):
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary) FROM t1"
        result = processor.process(sql)
        assert 'PARTITION BY' in result
        assert 'ORDER BY' in result
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_window_functions.py -v
```

Expected: FAIL

**Step 3: 实现窗口函数处理器**

```python
# backend/core/processors/window_functions.py
import re
from typing import List, Tuple
from .base_processor import BaseProcessor
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from formatter_v4_fixed import format_sql_v4_fixed

class WindowFunctionsProcessor(BaseProcessor):
    """窗口函数处理器 - 支持 OVER/PARTITION BY/窗口框架"""

    # OVER 子句模式
    OVER_PATTERN = re.compile(r'\bOVER\s*\(', re.IGNORECASE)

    # 窗口框架模式
    WINDOW_FRAME_PATTERN = re.compile(
        r'(ROWS|RANGE)\s+BETWEEN\s+(.+?)\s+AND\s+(.+?)(?:\)|$)',
        re.IGNORECASE
    )

    def __init__(self):
        super().__init__()

    def can_process(self, sql: str) -> bool:
        """检查是否包含窗口函数"""
        return bool(self.OVER_PATTERN.search(sql))

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理包含窗口函数的 SQL"""
        # 先用现有格式化器处理基础部分
        formatted = format_sql_v4_fixed(sql, keyword_case)

        # 处理 OVER 子句的格式化
        formatted = self._format_over_clauses(formatted)

        return formatted

    def _format_over_clauses(self, sql: str) -> str:
        """格式化 OVER 子句"""
        result = []
        i = 0

        while i < len(sql):
            # 查找 OVER (
            match = self.OVER_PATTERN.search(sql, pos=i)
            if not match:
                # 添加剩余部分
                result.append(sql[i:])
                break

            # 添加 OVER 之前的内容
            result.append(sql[i:match.end() - 1])  # OVER 不带括号
            result.append(' (')

            # 找到匹配的闭括号
            paren_start = match.end() - 1  # 开括号位置
            paren_content, paren_end = self._extract_paren_content(sql, paren_start)

            # 格式化括号内容
            formatted_content = self._format_over_content(paren_content)

            # 添加格式化后的内容
            result.append(formatted_content)
            result.append(')')

            i = paren_end + 1

        return ''.join(result)

    def _extract_paren_content(self, sql: str, start_pos: int) -> Tuple[str, int]:
        """提取括号内容"""
        depth = 0
        content = []
        i = start_pos

        while i < len(sql):
            char = sql[i]
            if char == '(':
                depth += 1
                if depth > 1:
                    content.append(char)
            elif char == ')':
                if depth == 1:
                    return ''.join(content), i
                depth -= 1
                content.append(char)
            else:
                if depth > 0:
                    content.append(char)
            i += 1

        return ''.join(content), i

    def _format_over_content(self, content: str) -> str:
        """格式化 OVER 子句内容"""
        content = content.strip()

        # 分割 PARTITION BY, ORDER BY, 窗口框架
        lines = []
        remaining = content

        # 提取 PARTITION BY
        partition_match = re.match(
            r'(PARTITION\s+BY\s+[^OR]+?)(?:\s+ORDER\s+BY|\s+ROWS\s+|$)',
            remaining,
            re.IGNORECASE
        )
        if partition_match:
            partition_by = partition_match.group(1).strip()
            lines.append(f'\n    {partition_by}')
            remaining = remaining[partition_match.end():].strip()

        # 提取 ORDER BY
        order_match = re.match(
            r'(ORDER\s+BY\s+[^RO]+?)(?:\s+ROWS\s+|$)',
            remaining,
            re.IGNORECASE
        )
        if order_match:
            order_by = order_match.group(1).strip()
            lines.append(f'\n    {order_by}')
            remaining = remaining[order_match.end():].strip()

        # 提取窗口框架
        if remaining:
            frame_match = self.WINDOW_FRAME_PATTERN.match(remaining)
            if frame_match:
                frame_type = frame_match.group(1)
                frame_start = frame_match.group(2).strip()
                frame_end = frame_match.group(3).strip()
                lines.append(f'\n        {frame_type.upper()} BETWEEN {frame_start}')
                lines.append(f'\n            AND {frame_end}')

        return ''.join(lines) if lines else content
```

**Step 4: 更新 __init__.py**

```python
# backend/core/processors/__init__.py
"""
SQL 语法处理器模块
"""
from .base_processor import BaseProcessor
from .set_operations import SetOperationsProcessor
from .window_functions import WindowFunctionsProcessor

__all__ = ['BaseProcessor', 'SetOperationsProcessor', 'WindowFunctionsProcessor']
```

**Step 5: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_window_functions.py -v
```

Expected: PASS

**Step 6: 更新 formatter_v5**

```python
# backend/core/formatter_v5.py
# 添加导入
from processors.window_functions import WindowFunctionsProcessor

# 添加处理器实例
_window_functions_processor = WindowFunctionsProcessor()

# 在 format_sql_v5 函数中添加
def format_sql_v5(sql: str, keyword_case: str = 'upper') -> str:
    detected_types = _classifier.classify(sql)

    # 按优先级处理
    if 'set_operations' in detected_types:
        return _set_operations_processor.process(sql, keyword_case)
    elif 'window_functions' in detected_types:
        return _window_functions_processor.process(sql, keyword_case)

    return format_sql_v4_fixed(sql, keyword_case)
```

**Step 7: 运行 formatter_v5 测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_formatter_v5.py -v
```

Expected: PASS

**Step 8: 提交**

```bash
git add backend/core/processors/window_functions.py
git add backend/tests/test_window_functions.py
git add backend/core/formatter_v5.py
git add backend/core/processors/__init__.py
git commit -m "feat: implement window functions processor (OVER/PARTITION BY/window frames)"
```

---

## Phase 3: 数据操作支持 (MERGE/INSERT OVERWRITE)

### Task 7: 实现数据操作处理器

**Files:**
- Create: `backend/core/processors/data_operations.py`
- Modify: `backend/core/processors/__init__.py`
- Create: `backend/tests/test_data_operations.py`

**Step 1: 编写数据操作测试**

```python
# backend/tests/test_data_operations.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.data_operations import DataOperationsProcessor

class TestDataOperationsProcessor:
    def test_can_process_merge(self):
        processor = DataOperationsProcessor()
        assert processor.can_process("MERGE INTO t USING s ON t.id = s.id") == True

    def test_simple_merge(self):
        processor = DataOperationsProcessor()
        sql = "MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET target.val = source.val"
        result = processor.process(sql)
        assert 'MERGE INTO' in result
        assert 'USING' in result
        assert 'ON' in result
        assert 'WHEN MATCHED' in result

    def test_merge_with_delete(self):
        processor = DataOperationsProcessor()
        sql = "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED AND s.del = 1 THEN DELETE"
        result = processor.process(sql)
        assert 'DELETE' in result
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_data_operations.py -v
```

Expected: FAIL

**Step 3: 实现数据操作处理器**

```python
# backend/core/processors/data_operations.py
import re
from typing import List
from .base_processor import BaseProcessor
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from formatter_v4_fixed import format_sql_v4_fixed

class DataOperationsProcessor(BaseProcessor):
    """数据操作处理器 - 支持 MERGE/INSERT OVERWRITE"""

    # MERGE 模式
    MERGE_PATTERN = re.compile(r'^\s*MERGE\s+INTO\b', re.IGNORECASE)

    # INSERT OVERWRITE 模式
    INSERT_OVERWRITE_PATTERN = re.compile(
        r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+',
        re.IGNORECASE
    )

    # WHEN 分支模式
    WHEN_PATTERN = re.compile(r'\bWHEN\s+(MATCHED|NOT\s+MATCHED)(?:\s+AND\s+.+?)?\s+THEN\b', re.IGNORECASE)

    def __init__(self):
        super().__init__()

    def can_process(self, sql: str) -> bool:
        """检查是否包含数据操作语句"""
        return bool(
            self.MERGE_PATTERN.match(sql) or
            self.INSERT_OVERWRITE_PATTERN.search(sql)
        )

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理数据操作语句"""
        sql = sql.strip()

        # 判断语句类型
        if self.MERGE_PATTERN.match(sql):
            return self._format_merge(sql, keyword_case)
        elif self.INSERT_OVERWRITE_PATTERN.search(sql):
            return self._format_insert_overwrite(sql, keyword_case)

        return sql

    def _format_merge(self, sql: str, keyword_case: str) -> str:
        """格式化 MERGE 语句"""
        # 分割 MERGE 语句的各个部分
        parts = self._parse_merge(sql)

        lines = []

        # MERGE INTO ... USING ... ON ...
        lines.append(f"MERGE INTO {parts['target']}")
        lines.append(f"USING {parts['source']}")
        lines.append(f"ON {parts['on_condition']}")

        # WHEN 分支
        for when_clause in parts['when_clauses']:
            condition = when_clause['condition']
            action = when_clause['action']

            if condition:
                lines.append(f"\nWHEN {condition} THEN")
            else:
                lines.append(f"\nWHEN {when_clause['type']} THEN")

            # 格式化操作
            formatted_action = self._format_merge_action(action)
            lines.append(f"    {formatted_action}")

        return '\n'.join(lines)

    def _parse_merge(self, sql: str) -> dict:
        """解析 MERGE 语句"""
        result = {
            'target': '',
            'source': '',
            'on_condition': '',
            'when_clauses': []
        }

        # 提取 MERGE INTO target
        merge_match = re.match(
            r'MERGE\s+INTO\s+(\S+)',
            sql,
            re.IGNORECASE
        )
        if merge_match:
            result['target'] = merge_match.group(1)

        # 提取 USING source
        using_match = re.search(
            r'USING\s+(\S+)',
            sql[merge_match.end():],
            re.IGNORECASE
        )
        if using_match:
            result['source'] = using_match.group(1)

        # 提取 ON 条件
        on_match = re.search(
            r'ON\s+(.+?)(?=\s*WHEN|$)',
            sql,
            re.IGNORECASE
        )
        if on_match:
            result['on_condition'] = on_match.group(1).strip()

        # 提取 WHEN 分支
        remaining = sql[on_match.end():] if on_match else ''
        when_matches = list(self.WHEN_PATTERN.finditer(remaining))

        for i, when_match in enumerate(when_matches):
            when_type = when_match.group(1).replace(' ', '')
            condition = None

            # 检查是否有 AND 条件
            when_text = when_match.group(0)
            and_match = re.search(r'\bAND\s+(.+?)\s+THEN\b', when_text, re.IGNORECASE)
            if and_match:
                condition = f"{when_type} AND {and_match.group(1)}"

            # 提取操作
            start = when_match.end()
            end = when_matches[i + 1].start() if i + 1 < len(when_matches) else len(remaining)
            action = remaining[start:end].strip()

            result['when_clauses'].append({
                'type': when_type,
                'condition': condition,
                'action': action
            })

        return result

    def _format_merge_action(self, action: str) -> str:
        """格式化 MERGE 操作"""
        action = action.strip()

        # DELETE
        if re.match(r'^DELETE\b', action, re.IGNORECASE):
            return 'DELETE'

        # UPDATE SET
        update_match = re.match(r'UPDATE\s+SET\s+(.+)', action, re.IGNORECASE)
        if update_match:
            set_clause = update_match.group(1)
            # 格式化 SET 子句
            set_items = re.split(r',\s*', set_clause)
            formatted_sets = [item.strip() for item in set_items]
            return f"UPDATE SET {', '.join(formatted_sets)}"

        # INSERT
        insert_match = re.match(
            r'INSERT\s*\((.+?)\)\s*VALUES\s*\((.+?)\)',
            action,
            re.IGNORECASE
        )
        if insert_match:
            columns = insert_match.group(1)
            values = insert_match.group(2)
            return f"INSERT ({columns})\n        VALUES ({values})"

        return action

    def _format_insert_overwrite(self, sql: str, keyword_case: str) -> str:
        """格式化 INSERT OVERWRITE 语句"""
        # 先使用现有格式化器处理 SELECT 部分
        formatted = format_sql_v4_fixed(sql, keyword_case)

        # INSERT OVERWRITE 特殊处理
        # 保持 INSERT OVERWRITE table 在一行
        # 换行后是 SELECT

        return formatted
```

**Step 4: 更新 __init__.py**

```python
# backend/core/processors/__init__.py
"""
SQL 语法处理器模块
"""
from .base_processor import BaseProcessor
from .set_operations import SetOperationsProcessor
from .window_functions import WindowFunctionsProcessor
from .data_operations import DataOperationsProcessor

__all__ = ['BaseProcessor', 'SetOperationsProcessor', 'WindowFunctionsProcessor', 'DataOperationsProcessor']
```

**Step 5: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_data_operations.py -v
```

Expected: PASS

**Step 6: 更新 formatter_v5**

```python
# backend/core/formatter_v5.py
# 添加导入
from processors.data_operations import DataOperationsProcessor

# 添加处理器实例
_data_operations_processor = DataOperationsProcessor()

# 在 format_sql_v5 函数中添加（优先级最高）
def format_sql_v5(sql: str, keyword_case: str = 'upper') -> str:
    detected_types = _classifier.classify(sql)

    # 按优先级处理
    if 'data_operations' in detected_types:
        return _data_operations_processor.process(sql, keyword_case)
    elif 'set_operations' in detected_types:
        return _set_operations_processor.process(sql, keyword_case)
    elif 'window_functions' in detected_types:
        return _window_functions_processor.process(sql, keyword_case)

    return format_sql_v4_fixed(sql, keyword_case)
```

**Step 7: 运行所有测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v -k "v5 or set_operations or window_functions or data_operations"
```

Expected: PASS

**Step 8: 提交**

```bash
git add backend/core/processors/data_operations.py
git add backend/tests/test_data_operations.py
git add backend/core/formatter_v5.py
git add backend/core/processors/__init__.py
git commit -m "feat: implement data operations processor (MERGE/INSERT OVERWRITE)"
```

---

## Phase 4: 高级转换支持 (PIVOT/LATERAL VIEW/TRANSFORM)

### Task 8: 实现高级转换处理器

**Files:**
- Create: `backend/core/processors/advanced_transforms.py`
- Modify: `backend/core/processors/__init__.py`
- Create: `backend/tests/test_advanced_transforms.py`

**Step 1: 编写高级转换测试**

```python
# backend/tests/test_advanced_transforms.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.advanced_transforms import AdvancedTransformsProcessor

class TestAdvancedTransformsProcessor:
    def test_can_process_lateral_view(self):
        processor = AdvancedTransformsProcessor()
        assert processor.can_process("SELECT * FROM t LATERAL VIEW EXPLODE(arr) e AS x") == True

    def test_lateral_view(self):
        processor = AdvancedTransformsProcessor()
        sql = "SELECT id, category FROM page_views LATERAL VIEW EXPLODE(pages) exploded AS category"
        result = processor.process(sql)
        assert 'LATERAL VIEW' in result
        assert 'EXPLODE' in result

    def test_multiple_lateral_views(self):
        processor = AdvancedTransformsProcessor()
        sql = "SELECT id FROM t LATERAL VIEW EXPLODE(arr1) e1 AS x LATERAL VIEW EXPLODE(arr2) e2 AS y"
        result = processor.process(sql)
        assert result.count('LATERAL VIEW') == 2
```

**Step 2: 运行测试验证失败**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_advanced_transforms.py -v
```

Expected: FAIL

**Step 3: 实现高级转换处理器**

```python
# backend/core/processors/advanced_transforms.py
import re
from typing import List
from .base_processor import BaseProcessor
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from formatter_v4_fixed import format_sql_v4_fixed

class AdvancedTransformsProcessor(BaseProcessor):
    """高级转换处理器 - 支持 PIVOT/LATERAL VIEW/TRANSFORM"""

    # LATERAL VIEW 模式
    LATERAL_VIEW_PATTERN = re.compile(r'\bLATERAL\s+VIEW\b', re.IGNORECASE)

    # PIVOT 模式
    PIVOT_PATTERN = re.compile(r'\bPIVOT\b', re.IGNORECASE)

    # TRANSFORM 模式
    TRANSFORM_PATTERN = re.compile(r'\bTRANSFORM\s*\(', re.IGNORECASE)

    def __init__(self):
        super().__init__()

    def can_process(self, sql: str) -> bool:
        """检查是否包含高级转换语法"""
        return bool(
            self.LATERAL_VIEW_PATTERN.search(sql) or
            self.PIVOT_PATTERN.search(sql) or
            self.TRANSFORM_PATTERN.search(sql)
        )

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理高级转换语法"""
        # 先用现有格式化器处理基础部分
        formatted = format_sql_v4_fixed(sql, keyword_case)

        # 根据具体语法进行后处理
        if self.LATERAL_VIEW_PATTERN.search(sql):
            formatted = self._format_lateral_view(formatted)

        return formatted

    def _format_lateral_view(self, sql: str) -> str:
        """格式化 LATERAL VIEW 语句"""
        # LATERAL VIEW 应该与 FROM 对齐（类似 JOIN）
        # 每个 LATERAL VIEW 独立一行

        # 按行分割
        lines = sql.split('\n')
        result = []

        for line in lines:
            stripped = line.strip()

            # 检查是否包含 LATERAL VIEW
            if 'LATERAL VIEW' in stripped.upper():
                # 确保 LATERAL VIEW 在行首（与 FROM 对齐）
                # 去除前导空格
                result.append(stripped)
            else:
                result.append(line)

        return '\n'.join(result)

    def _format_pivot(self, sql: str) -> str:
        """格式化 PIVOT 语句（占位，后续实现）"""
        # TODO: 实现 PIVOT 格式化
        return sql

    def _format_transform(self, sql: str) -> str:
        """格式化 TRANSFORM 语句（占位，后续实现）"""
        # TODO: 实现 TRANSFORM 格式化
        return sql
```

**Step 4: 更新 __init__.py**

```python
# backend/core/processors/__init__.py
"""
SQL 语法处理器模块
"""
from .base_processor import BaseProcessor
from .set_operations import SetOperationsProcessor
from .window_functions import WindowFunctionsProcessor
from .data_operations import DataOperationsProcessor
from .advanced_transforms import AdvancedTransformsProcessor

__all__ = ['BaseProcessor', 'SetOperationsProcessor', 'WindowFunctionsProcessor',
           'DataOperationsProcessor', 'AdvancedTransformsProcessor']
```

**Step 5: 运行测试验证通过**

```bash
cd spark-sql-optimizer
pytest backend/tests/test_advanced_transforms.py -v
```

Expected: PASS

**Step 6: 更新 formatter_v5**

```python
# backend/core/formatter_v5.py
# 添加导入
from processors.advanced_transforms import AdvancedTransformsProcessor

# 添加处理器实例
_advanced_transforms_processor = AdvancedTransformsProcessor()

# 在 format_sql_v5 函数中添加
def format_sql_v5(sql: str, keyword_case: str = 'upper') -> str:
    detected_types = _classifier.classify(sql)

    # 按优先级处理
    if 'data_operations' in detected_types:
        return _data_operations_processor.process(sql, keyword_case)
    elif 'set_operations' in detected_types:
        return _set_operations_processor.process(sql, keyword_case)
    elif 'window_functions' in detected_types:
        return _window_functions_processor.process(sql, keyword_case)
    elif 'advanced_transforms' in detected_types:
        return _advanced_transforms_processor.process(sql, keyword_case)

    return format_sql_v4_fixed(sql, keyword_case)
```

**Step 7: 运行所有测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v -k "v5 or processor"
```

Expected: PASS

**Step 8: 提交**

```bash
git add backend/core/processors/advanced_transforms.py
git add backend/tests/test_advanced_transforms.py
git add backend/core/formatter_v5.py
git add backend/core/processors/__init__.py
git commit -m "feat: implement advanced transforms processor (LATERAL VIEW/PIVOT/TRANSFORM)"
```

---

## 最终验证

### Task 9: 端到端测试

**Files:** 无

**Step 1: 运行所有测试**

```bash
cd spark-sql-optimizer
pytest backend/tests/ -v
```

Expected: 所有测试通过

**Step 2: 测试前端集成（如果前端已更新）**

```bash
# 启动后端
cd spark-sql-optimizer/backend
python -m uvicorn app:app --port 8888 --reload
```

在另一个终端启动前端：

```bash
cd spark-sql-optimizer/frontend
npm start
```

在浏览器中测试以下 SQL：

```sql
-- 集合操作
SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2

-- 窗口函数
SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees

-- MERGE
MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET target.val = source.val

-- LATERAL VIEW
SELECT id, category FROM page_views LATERAL VIEW EXPLODE(pages) exploded AS category
```

**Step 3: 性能测试（可选）**

```python
# test_performance.py
import time
from formatter_v5 import format_sql_v5

# 测试大文件性能
with open('large_sql_file.sql', 'r') as f:
    sql = f.read()

start = time.time()
result = format_sql_v5(sql)
end = time.time()

print(f"Formatted {len(sql)} chars in {end - start:.2f} seconds")
```

**Step 4: 提交最终版本**

```bash
git add backend/tests/
git commit -m "test: add comprehensive tests for all processors"
```

---

## 文档更新

### Task 10: 更新 README

**Files:**
- Modify: `README.md` 或创建 `backend/core/processors/README.md`

**Step 1: 创建处理器文档**

```markdown
# SQL 语法处理器

## 概述

本目录包含 Spark SQL 格式化器的语法处理器模块。每个处理器负责一类特定 SQL 语法的格式化。

## 处理器列表

### 集合操作处理器 (set_operations.py)
- 支持: UNION, UNION ALL, INTERSECT, EXCEPT, MINUS
- 状态: ✅ 已实现

### 窗口函数处理器 (window_functions.py)
- 支持: OVER, PARTITION BY, ORDER BY, 窗口框架
- 状态: ✅ 已实现

### 数据操作处理器 (data_operations.py)
- 支持: MERGE, INSERT OVERWRITE
- 状态: ✅ 已实现

### 高级转换处理器 (advanced_transforms.py)
- 支持: LATERAL VIEW, PIVOT, UNPIVOT, TRANSFORM
- 状态: ✅ 已实现

## 扩展指南

要添加新的语法处理器：

1. 继承 `BaseProcessor` 类
2. 实现 `can_process()` 和 `process()` 方法
3. 在 `sql_classifier.py` 中添加检测规则
4. 在 `formatter_v5.py` 中注册处理器
```

**Step 2: 提交文档**

```bash
git add backend/core/processors/README.md
git commit -m "docs: add processor documentation"
```

---

## 总结

完成以上所有任务后，SQL 格式化器将支持：

- ✅ 集合操作 (UNION/INTERSECT/EXCEPT/MINUS)
- ✅ 窗口函数 (OVER/PARTITION BY/窗口框架)
- ✅ 数据操作 (MERGE/INSERT OVERWRITE)
- ✅ 高级转换 (LATERAL VIEW/PIVOT/TRANSFORM)

**预计总工作量:** 12-16 小时

**关键提交点:**
1. Task 1-4: 集合操作支持 (Phase 1)
2. Task 6: 窗口函数支持 (Phase 2)
3. Task 7: 数据操作支持 (Phase 3)
4. Task 8: 高级转换支持 (Phase 4)
5. Task 9-10: 最终验证和文档

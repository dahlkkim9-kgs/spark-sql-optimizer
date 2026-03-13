# SQL 语法处理器架构

## 概述

本目录包含 Spark SQL 优化工具的格式化处理器系统。每个处理器负责处理特定的 SQL 语法类型，提供可扩展、可维护的架构。

## 架构设计

### 基础架构

```
formatter_v5.py (入口点)
    |
    v
SQLClassifier (语法分类器)
    |
    +-- SetOperationsProcessor (集合操作)
    +-- WindowFunctionsProcessor (窗口函数)
    +-- DataOperationsProcessor (数据操作)
    +-- AdvancedTransformsProcessor (高级转换)
    |
    v
formatter_v4_fixed.py (基础 SELECT 格式化)
```

### 核心组件

1. **BaseProcessor** - 所有处理器的抽象基类
   - `can_process(sql: str) -> bool`: 判断是否能处理此 SQL
   - `process(sql: str, keyword_case: str) -> str`: 处理并返回格式化结果

2. **SQLClassifier** - 语法分类器
   - 分析 SQL 语句类型
   - 返回语法类型列表 (set_operations, window_functions, data_operations, etc.)

3. **Processor 链** - 按优先级处理 SQL
   - 每个处理器检查是否能处理当前 SQL
   - 第一个匹配的处理器处理 SQL
   - 未匹配时回退到基础格式化器

## 处理器列表

### 1. SetOperationsProcessor - 集合操作处理器

**文件**: `set_operations.py`

**支持的语法**:
- UNION [ALL]
- INTERSECT
- EXCEPT
- MINUS (Spark SQL 语法)

**功能特性**:
- 识别 UNION ALL (优先于 UNION)
- 格式化集合操作关键字
- 对齐多个 SELECT 语句
- 处理嵌套集合操作

**示例**:
```sql
-- 输入
SELECT a FROM t1 UNION ALL SELECT b FROM t2

-- 输出
SELECT a
FROM t1
UNION ALL
SELECT b
FROM t2
```

### 2. WindowFunctionsProcessor - 窗口函数处理器

**文件**: `window_functions.py`

**支持的语法**:
- OVER (PARTITION BY ... ORDER BY ...)
- Window frames (ROWS BETWEEN, RANGE BETWEEN)
- Named windows (WINDOW clause)
- 窗口函数: ROW_NUMBER(), RANK(), DENSE_RANK(), LEAD(), LAG(), 等

**功能特性**:
- 格式化 OVER 子句
- 对齐 PARTITION BY 和 ORDER BY
- 处理窗口框架规范
- 支持命名窗口

**示例**:
```sql
-- 输入
SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) as rk FROM emp

-- 输出
SELECT ROW_NUMBER() OVER (
                          PARTITION BY dept
                          ORDER BY salary DESC
                        ) AS rk
FROM emp
```

### 3. DataOperationsProcessor - 数据操作处理器

**文件**: `data_operations.py`

**支持的语法**:
- MERGE INTO ... WHEN MATCHED THEN ... WHEN NOT MATCHED THEN ...
- INSERT OVERWRITE [TABLE] ... PARTITION (...)

**功能特性**:
- 格式化 MERGE 语句
- 处理 WHEN MATCHED/NOT MATCHED 子句
- 支持 INSERT OVERWRITE 与 PARTITION 子句
- 保留字符串字面量和注释

**示例**:
```sql
-- 输入
MERGE INTO target t USING source s ON t.id=s.id WHEN MATCHED THEN UPDATE SET t.val=s.val

-- 输出
MERGE INTO target t
USING source s
ON t.id = s.id
WHEN MATCHED
    THEN UPDATE
         SET t.val = s.val
```

### 4. AdvancedTransformsProcessor - 高级转换处理器

**文件**: `advanced_transforms.py`

**支持的语法**:
- LATERAL VIEW [OUTER] EXPLODE(...) table_alias AS column_alias
- LATERAL VIEW JSON_TUPLE(...) table_alias AS column_aliases
- CLUSTER BY
- DISTRIBUTE BY
- PIVOT (基础支持)
- UNPIVOT (基础支持)
- TRANSFORM (基础支持)

**功能特性**:
- 格式化 LATERAL VIEW 子句
- 支持多个 LATERAL VIEW 链式调用
- 处理 CLUSTER BY 和 DISTRIBUTE BY
- 检测高级语法后委托给基础格式化器

**示例**:
```sql
-- 输入
SELECT id, category FROM table LATERAL VIEW EXPLODE(categories) cat AS category

-- 输出
SELECT id
     , category
FROM table
LATERAL VIEW EXPLODE(categories) cat AS category
```

## 使用方法

### 直接使用处理器

```python
from backend.core.processors.set_operations import SetOperationsProcessor

processor = SetOperationsProcessor()
if processor.can_process(sql):
    formatted = processor.process(sql, keyword_case='upper')
```

### 使用格式化器入口

```python
from backend.core.formatter_v5 import format_sql_v5

# 自动分类并路由到正确的处理器
formatted = format_sql_v5(sql, keyword_case='upper')
```

### API 调用

```python
import requests

response = requests.post('http://localhost:8000/api/format', json={
    'sql': 'SELECT a FROM t1 UNION SELECT b FROM t2',
    'keyword_case': 'upper'
})
formatted = response.json()['formatted_sql']
```

## 扩展指南

### 添加新处理器

1. **创建处理器类**:

```python
from backend.core.processors.base_processor import BaseProcessor
import re

class NewProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        # 定义检测模式
        self.pattern = re.compile(r'YOUR_KEYWORD', re.IGNORECASE)

    def can_process(self, sql: str) -> bool:
        """判断是否能处理此 SQL"""
        return self.pattern.search(sql) is not None

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理 SQL 并返回格式化后的结果"""
        # 实现格式化逻辑
        return formatted_sql
```

2. **更新 SQLClassifier**:

在 `sql_classifier.py` 中添加新语法类型:

```python
def classify(self, sql: str) -> List[str]:
    types = []
    if re.search(r'YOUR_KEYWORD', sql, re.IGNORECASE):
        types.append('your_syntax_type')
    # ... 其他检查
    return types
```

3. **在 formatter_v5.py 中注册**:

```python
from backend.core.processors.new_processor import NewProcessor

processors = [
    SetOperationsProcessor(),
    WindowFunctionsProcessor(),
    DataOperationsProcessor(),
    AdvancedTransformsProcessor(),
    NewProcessor(),  # 添加新处理器
]
```

### 处理器优先级

处理器按以下顺序检查:
1. SetOperationsProcessor (集合操作)
2. WindowFunctionsProcessor (窗口函数)
3. DataOperationsProcessor (数据操作)
4. AdvancedTransformsProcessor (高级转换)
5. formatter_v4_fixed (基础 SELECT)

### 测试新处理器

创建测试文件 `tests/test_new_processor.py`:

```python
import pytest
from backend.core.processors.new_processor import NewProcessor

class TestNewProcessor:
    def test_can_process(self):
        processor = NewProcessor()
        assert processor.can_process("YOUR KEYWORD ...")

    def test_formatting(self):
        processor = NewProcessor()
        result = processor.process("YOUR KEYWORD ...")
        assert "EXPECTED" in result
```

## 测试

运行所有处理器测试:

```bash
pytest backend/tests/test_set_operations.py -v
pytest backend/tests/test_window_functions.py -v
pytest backend/tests/test_data_operations.py -v
pytest backend/tests/test_advanced_transforms.py -v
pytest backend/tests/test_sql_classifier.py -v
```

## 常见问题

### Q: 如何调试处理器匹配问题?

A: 使用 SQLClassifier 查看 SQL 分类结果:

```python
from backend.core.parser.sql_classifier import SQLClassifier

classifier = SQLClassifier()
types = classifier.classify(your_sql)
print(f"Detected types: {types}")
```

### Q: 处理器没有处理我的 SQL?

A: 检查:
1. `can_process()` 方法返回 True
2. 处理器优先级 (其他处理器可能先匹配)
3. 使用 SQLClassifier 验证语法类型检测

### Q: 如何添加新的 SQL 关键字?

A: 在相应处理器中:
1. 更新检测正则表达式
2. 添加格式化逻辑
3. 添加测试用例

## 相关文档

- [格式化示例](./EXAMPLES.md) - 各种 SQL 语法格式化示例
- [测试用例](../../tests/) - 完整的测试集合
- [设计文档](../../../docs/plans/) - 架构设计文档

## 版本历史

- **v1.0** (2026-03-13) - 初始架构
  - SetOperationsProcessor
  - WindowFunctionsProcessor
  - DataOperationsProcessor
  - AdvancedTransformsProcessor
  - SQLClassifier
  - formatter_v5 入口点

# V5 括号对齐修复设计文档

**日期**: 2026-03-23
**状态**: 设计阶段

---

## 问题描述

### 当前问题
V5 sqlglot 版本格式化后的 SQL 存在括号缩进问题：

1. **子查询缩进过深**: `IN (` 、`FROM (`、`join (` 等后的子查询缩进不一致
2. **括号对齐不统一**: 闭合括号位置混乱
3. **SQL 完整性**: 不能添加或删除括号，只能调整缩进

### 示例

**sqlglot 默认输出（问题）**:
```sql
WHERE
  NOT khzjdm IN (
      SELECT DISTINCT    -- 缩进过深
        khzjdm
      FROM t2
  )
```

**目标格式**:
```sql
WHERE khzjdm NOT IN (
                     SELECT DISTINCT      -- 统一缩进
                         khzjdm
                     FROM t2
                    )
```

---

## 设计方案

### 核心原则

1. **SQL 完整性优先**: 绝不添加或删除括号
2. **复用 V4 逻辑**: 使用 `IndentContext` 的缩进计算规则
3. **两阶段处理**: sqlglot 解析 → 后处理器调整缩进

### V4 括号对齐规则（参考）

**"开括号+1"规则**:
```
对于: prefix (
- 开括号位置 = len(prefix)
- 内容缩进   = len(prefix) + 1
- 闭括号缩进 = len(prefix)
```

**示例**:
```
FROM (                      <- 开括号位置 = 5
      SELECT a              <- 内容缩进 = 6 (5+1)
      FROM t1               <- 内容缩进 = 6
     )                      <- 闭括号缩进 = 5
```

---

## 架构设计

### 处理流程

```
原始 SQL
    ↓
sqlglot 解析 (AST)
    ↓
sqlglot 格式化输出
    ↓
ParenthesisAlignPostProcessor (调整括号缩进)
    ↓
格式化 SQL
```

### 类设计

```python
class ParenthesisAlignPostProcessor:
    """括号对齐后处理器

    只调整括号缩进，不添加或删除括号
    复用 V4 的 IndentContext 进行缩进计算
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
        pass
```

---

## 实现要点

### 1. 括号配对追踪

- 维护括号栈，记录开括号位置
- 遇到 `(` 时，记录位置并压栈
- 遇到 `)` 时，弹栈并对齐

### 2. 缩进计算

```python
# 开括号行
paren_pos = len(prefix) + current_base_indent
content_indent = paren_pos + 1

# 内容行
indent = paren_pos + 1

# 闭括号行
indent = paren_pos
```

### 3. 特殊情况处理

- **函数调用括号**: 保持 sqlglot 原有格式
- **子查询括号**: 应用对齐规则
- **CASE WHEN 括号**: 保持原样
- **注释行**: 跳过处理

---

## 文件变更

| 文件 | 操作 | 描述 |
|------|------|------|
| `formatter_v5_sqlglot.py` | 修改 | 添加 `ParenthesisAlignPostProcessor` |
| `test_formatter_v5.py` | 新增 | 添加括号对齐测试用例 |

---

## 测试用例

```python
def test_in_subquery_indent():
    """测试 IN 子查询缩进"""
    sql = "SELECT * FROM t1 WHERE a NOT IN (SELECT x FROM t2)"
    result = format_sql_v5(sql)
    # 验证括号对齐

def test_nested_parenthesis():
    """测试嵌套括号"""
    sql = "SELECT (SELECT (SELECT x FROM t3) FROM t2) FROM t1"
    result = format_sql_v5(sql)
    # 验证多层括号对齐
```

---

## 后续步骤

1. 实现 `ParenthesisAlignPostProcessor`
2. 集成到 `formatter_v5_sqlglot.py`
3. 添加测试用例
4. 验证真实 SQL 文件
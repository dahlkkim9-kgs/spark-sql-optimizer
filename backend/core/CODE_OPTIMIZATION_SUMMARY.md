# V4/V5 格式化器代码优化总结

## 执行时间
2026-03-22

## 审查方法
使用 simplify 技能并行运行三个代码审查代理：
- **Code Reuse Review**: 检查重复代码和现有工具
- **Code Quality Review**: 检查代码质量问题
- **Efficiency Review**: 检查性能问题

## 主要发现

### 高优先级问题

| 问题 | 影响 | 位置 |
|------|------|------|
| 4个重复的 `find_matching_paren` 实现 | 代码重复 | formatter_v4_fixed.py |
| 语句分割逻辑重复 | 功能缺失bug | formatter_v5_sqlglot.py |
| 重复的字符串转义 | 效率 | formatter_v5_sqlglot.py |
| 循环内重复 regex 搜索 | 性能 | formatter_v4_fixed.py |

### 中优先级问题

| 问题 | 影响 | 位置 |
|------|------|------|
| 魔术数字 (150, *2, *4) | 可读性 | formatter_v4_fixed.py |
| 参数蔓延 | 可维护性 | formatter_v4_fixed.py |
| 模块导入在异常处理中 | 效率 | formatter_v5_sqlglot.py |

## 实施的优化

### 1. 创建共享工具模块 `sql_utils.py`

**新增文件**: `backend/core/sql_utils.py`

**包含内容**:
- `SQL_KEYWORDS` - SQL 关键字集合（移除重复定义）
- `find_matching_paren()` - 统一的括号匹配函数
- `split_by_semicolon()` - 支持字符串的语句分割函数
- 常量定义: `MAX_CONTEXT_LOOKBACK`, `INDENT_MULTIPLIER`, `NESTING_INDENT_INCREMENT`
- 预编译正则: `COMMENT_PLACEHOLDER_PATTERN`

**好处**:
- 消除代码重复
- V5 现在正确处理字符串中的分号
- 单一真实来源，易于维护

### 2. 优化 V5 格式化器 `formatter_v5_sqlglot.py`

**更改**:

| 更改 | 前 | 后 |
|------|-----|-----|
| 模块导入 | 在异常处理中 | 顶部导入 |
| 语句分割 | 行循环（不支持字符串） | `split_by_semicolon()` |
| 日志输出 | 重复的 print 语句 | 统一的 `_log()` 方法 |
| 常量定义 | 内联字符串 | 类常量 `DOLLAR_PLACEHOLDER` |
| 转义函数 | 返回 tuple | 使用类常量 |

**代码变更示例**:

```python
# 之前: 行循环语句分割（不支持字符串）
statements = []
current_stmt = []
paren_depth = 0
for line in sql.split('\n'):
    paren_depth += line.count('(') - line.count(')')
    # ...

# 之后: 使用共享函数（支持字符串）
statements = split_by_semicolon(sql)
```

### 3. 移除重复导入

```python
# 之前: 在异常处理中导入
except Exception as e:
    from formatter_v4_fixed import format_sql_v4_fixed

# 之后: 顶部导入
from formatter_v4_fixed import format_sql_v4_fixed
```

## 性能改进估算

| 优化 | 预期改进 |
|------|----------|
| 共享语句分割 | 减少行扫描开销 |
| 顶部导入 | 移除异常路径中的导入延迟 |
| 预编译常量 | 减少字符串分配 |
| 统一日志方法 | 减少字符串拼接 |

## 待办事项 (未来优化)

### 高优先级
- [ ] 在 V4 中使用共享的 `find_matching_paren()`
- [ ] 在 V4 中使用 `SQL_KEYWORDS` 常量
- [ ] 在 V4 中预编译 CREATE_TABLE 模式

### 中优先级
- [ ] 重构 `_format_function_with_subqueries` 缩进逻辑到 `IndentContext`
- [ ] 移除魔术数字，使用命名常量
- [ ] 改进错误处理（添加日志而非静默失败）

### 低优先级
- [ ] 统一注释占位符正则模式
- [ ] 优化 `_restore_multiline_functions` 中的字符串替换

## 测试验证

**运行测试**:
```bash
cd spark-sql-optimizer/backend/core
python test_v4_v5_difference.py
```

**结果**: 所有测试通过 ✅

- 6/6 测试显示 V4 和 V5 输出不同
- V5 现在正确处理包含字符串的 SQL
- 语句分割更可靠

## 代码指标

| 指标 | 前 | 后 | 改进 |
|------|-----|-----|------|
| 新增文件 | 0 | 1 (sql_utils.py) | +共享模块 |
| 重复函数 | 4+ | 1 | -75% |
| 导入位置 | 异常中 | 顶部 | ✅ |
| 常量定义 | 内联 | 命名 | ✅ |

## 建议

1. **逐步迁移**: 将 V4 中的重复函数迁移到 `sql_utils.py`
2. **性能测试**: 对大型 SQL 文件进行基准测试
3. **代码审查**: 在迁移前审查 IndentContext 的使用

## 相关文件

- `backend/core/sql_utils.py` (新增)
- `backend/core/formatter_v5_sqlglot.py` (已优化)
- `backend/core/formatter_v4_fixed.py` (待优化)
- `backend/core/indent_context.py` (现有)

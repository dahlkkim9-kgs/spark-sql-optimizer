# sqlglot v5 格式化器开发总结

> **开发时间**: 2026-03-21
> **分支**: feature/sqlglot-formatter
> **Worktree**: `.worktrees/sqlglot-formatter`

---

## 项目目标

基于 sqlglot AST 解析构建新的 SQL 格式化器，保留 v4 的格式化风格，解决正则表达式的局限性。

## 技术方案

| 组件 | 技术 |
|------|------|
| **解析器** | sqlglot 28.10.0 (MIT 许可) |
| **架构** | sqlglot AST → 中间格式 → v4 风格后处理 |
| **代码量** | ~250 行（vs v4 的 5,489 行） |

## 完成的功能

### 核心功能
- ✅ AST 解析与格式化
- ✅ v4 风格列对齐（逗号在行首）
- ✅ 多语句支持（分号分隔）
- ✅ SELECT DISTINCT 保留

### SQL 语法支持
- ✅ SELECT / INSERT / CREATE TABLE / DROP TABLE
- ✅ WHERE / JOIN / GROUP BY / HAVING / ORDER BY
- ✅ INNER / LEFT / RIGHT / FULL / CROSS JOIN
- ✅ CASE WHEN / EXISTS / IN / BETWEEN
- ✅ OVER 窗口函数 (PARTITION BY / ORDER BY)
- ✅ CTE / WITH 语句
- ✅ UNION / INTERSECT / EXCEPT / MINUS
- ✅ 深层嵌套子查询（2-4 层）
- ✅ 函数内子查询 (AVG, COALESCE, SUM)

### 新增文件

| 文件 | 描述 |
|------|------|
| `formatter_v5_sqlglot.py` | 基于 sqlglot 的 v5 格式化器 |
| `test_formatter_v5.py` | 单元测试（14 个测试用例） |
| `test_v5_multi_statement.py` | 多语句支持测试 |
| `test_formatter_v5_distinct.py` | DISTINCT 处理测试 |
| `test_v4_v5_comparison.py` | v4 vs v5 对比测试 |
| `test_v4_v5_detailed_comparison.py` | 详细对比测试 |
| `test_v5_with_real_files.py` | 真实文件集成测试 |

### API 端点

| 端点 | 描述 |
|------|------|
| `/api/format-v5` | **新增** - 基于 sqlglot AST 解析 |
| `/format/v5` | 保留 - 旧版本（基于 SQLClassifier） |

## 测试结果

**单元测试**: 17/17 通过 (100%)
- 基础功能测试
- 子查询嵌套测试
- CASE WHEN / CTE 测试
- CREATE TABLE / INSERT / OVER 测试
- 多语句测试
- DISTINCT 测试

**真实文件测试**: 全部通过
- 真实世界 SQL 文件
- 复杂嵌套子查询
- CTE 语句

## v4 vs v5 对比

| 特性 | v4 (正则方案) | v5 (sqlglot 方案) |
|------|---------------|-------------------|
| 解析准确性 | ⚠️ 中 (正则局限) | ✅ 高 (AST) |
| 深层嵌套子查询 | ⚠️ 有 bug | ✅ 正确处理 |
| 新语法支持 | 需写新正则 | ✅ 自动支持 |
| 代码行数 | 5,489 行 | ~250 行 |
| 商用许可 | ✅ 自有 | ✅ MIT |
| WHERE 格式 | 详细缩进 | 紧凑格式 |
| CASE WHEN | 多行展开 | 单行/紧凑 |
| 多语句 | 添加分号 | 空行分隔 |
| SELECT DISTINCT | ✅ 支持 | ✅ 支持 |

## 提交历史

```
2ddfb23 fix: preserve SELECT DISTINCT modifier in column alignment
d5dfcc7 test: add detailed v4 vs v5 comparison
2602d1c feat: add multi-statement support and improve column alignment
b28581f fix: improve column alignment to handle subqueries correctly
b9f1297 test: add real SQL file integration tests
41f3b77 feat: add v5 sqlglot format API endpoint (/api/format-v5)
a1cb633 test: add v4 vs v5 comparison tests
91e85fb test: add CREATE TABLE, INSERT and OVER tests
cdfdc4f feat: add v4 style column alignment
56094a0 test: add CASE WHEN and CTE tests
0314759 test: add subquery test cases
876472c feat: add sqlglot AST parsing to v5
9453dd5 feat: create v5 sqlglot formatter skeleton
```

## 已知限制

1. **注释格式**: 注释位置可能与原 SQL 不同
2. **风格差异**: WHERE/ON 子句缩进比 v4 更紧凑
3. **CASE WHEN**: 默认单行格式（v4 是多行展开）

## 后续优化方向

1. **风格微调**: 根据 v4 风格调整后处理器
2. **注释保留**: 改进注释位置处理
3. **配置化**: 支持更多格式化选项
4. **性能优化**: 大文件处理性能
5. **错误处理**: 更友好的错误提示

## 集成策略

- ✅ v4 保持不变，继续服务
- ✅ v5 作为新端点 `/api/format-v5`
- ✅ 前端可选择使用哪个版本
- ✅ 验证稳定后再考虑替换

# 测试用例库 - 完整指南

## 已创建内容

### 测试用例 (39个)

| 类别 | 文件数 | 测试内容 |
|------|--------|----------|
| **basic** | 6 | 简单SELECT, WHERE, JOIN, GROUP BY, INSERT, CREATE |
| **complex** | 6 | 嵌套子查询, 双层嵌套, NOT IN, CASE WHEN, 多JOIN, CTE |
| **edge_cases** | 5 | 空SQL, 空格, 单字段, 特殊字符, 多语句 |
| **spark_specific** | 4 | PARTITION, COMMENT空格, DISTRIBUTE BY, CACHE |
| **regression** | 3 | 历史bug验证 |
| **window_functions** | 3 | 窗口函数 (ROW_NUMBER, RANK, LAG, LEAD) |
| **advanced_grouping** | 3 | 高级聚合 (GROUPING SETS, ROLLUP, CUBE, FILTER) |
| **complex_types** | 3 | 复杂数据类型 (ARRAY, MAP, STRUCT, LATERAL VIEW) |
| **special_syntax** | 3 | 特殊语法 (CLUSTER BY, PIVOT, TRANSFORM) |
| **advanced_functions** | 3 | 高级函数 (JSON函数, Lambda表达式) |

### 测试脚本

1. **run_tests_simple.py** - 完整测试套件
   ```bash
   python run_tests_simple.py
   # 输出: Results: 39/39 passed
   ```

2. **quick_test.py** - 快速验证（开发时用）
   ```bash
   python quick_test.py
   # 输出: All quick tests passed!
   ```

3. **run_tests.py** - 详细版本（可选）

## 目录结构

```
spark-sql-optimizer/
├── test_cases/
│   ├── README.md                      # 测试用例说明
│   ├── basic/                         # 基础功能 (6个)
│   │   ├── 01_simple_select.sql
│   │   ├── 02_select_with_where.sql
│   │   ├── 03_select_with_joins.sql
│   │   ├── 04_select_with_group_by.sql
│   │   ├── 05_insert_select.sql
│   │   └── 06_create_table.sql
│   ├── complex/                       # 复杂场景 (6个)
│   │   ├── 01_nested_subquery.sql
│   │   ├── 02_double_nested_subquery.sql
│   │   ├── 03_not_in_subquery.sql
│   │   ├── 04_case_when.sql
│   │   ├── 05_multiple_joins.sql
│   │   └── 06_with_cte.sql
│   ├── edge_cases/                    # 边界情况 (5个)
│   │   ├── 01_empty_sql.sql
│   │   ├── 02_whitespace_only.sql
│   │   ├── 03_single_field.sql
│   │   ├── 04_special_characters.sql
│   │   └── 05_multiple_statements.sql
│   ├── regression/                    # 回归测试 (3个)
│   │   ├── 001_comment_spaces.sql
│   │   ├── 002_from_subquery_indent.sql
│   │   └── 003_internal_empty_lines.sql
│   ├── spark_specific/                # Spark特有 (4个)
│   │   ├── 01_partition_insert.sql
│   │   ├── 02_comment_spaces.sql
│   │   ├── 03_distribute_by.sql
│   │   └── 04_cache_table.sql
│   ├── window_functions/              # 窗口函数 (3个)
│   │   ├── 01_row_number_rank.sql
│   │   ├── 02_lag_lead_functions.sql
│   │   └── 03_window_frame.sql
│   ├── advanced_grouping/             # 高级聚合 (3个)
│   │   ├── 01_grouping_sets.sql
│   │   ├── 02_rollup_cube.sql
│   │   └── 03_filter_clause.sql
│   ├── complex_types/                 # 复杂数据类型 (3个)
│   │   ├── 01_array_explode.sql
│   │   ├── 02_map_struct.sql
│   │   └── 03_lateral_view.sql
│   ├── special_syntax/                # 特殊语法 (3个)
│   │   ├── 01_cluster_sort_distribute.sql
│   │   ├── 02_pivot.sql
│   │   └── 03_transform.sql
│   └── advanced_functions/             # 高级函数 (3个)
│       ├── 01_sequence_stack.sql
│       ├── 02_json_functions.sql
│       └── 03_lambda_functions.sql
├── run_tests_simple.py                # 简单测试脚本
├── quick_test.py                      # 快速测试脚本
└── run_tests.py                       # 详细测试脚本
```

## 使用场景

### 1. 开发时快速验证
```bash
# 修改代码后，快速检查核心功能
python quick_test.py
```

### 2. 提交前完整测试
```bash
# 运行全部测试用例
python run_tests_simple.py
```

### 3. 添加新功能时
```bash
# 在对应类别添加新的 .sql 测试文件
# 然后运行测试验证
python run_tests_simple.py
```

## 测试用例格式

每个测试文件遵循以下格式：

```sql
-- 测试: 测试名称
-- 预期: 预期结果描述
SELECT ...;
```

示例：
```sql
-- 测试: COMMENT空格保留
-- 预期: COMMENT '...' 内的空格完整保留
CREATE TABLE t (id STRING COMMENT 'ID          ');
```

## 当前测试状态

```
============================================================
Results: 39/39 passed
All tests passed!
============================================================
```

## 添加新测试的步骤

1. **确定测试类别**
   - basic: 基础功能
   - complex: 复杂场景
   - edge_cases: 边界情况
   - spark_specific: Spark特有
   - regression: 历史bug
   - window_functions: 窗口函数
   - advanced_grouping: 高级聚合
   - complex_types: 复杂数据类型
   - special_syntax: 特殊语法
   - advanced_functions: 高级函数

2. **创建测试文件**
   ```bash
   # 例如：添加新的边界测试
   echo "-- 测试: 超长SQL
   -- 预期: 正常处理不崩溃
   SELECT $(seq 1 100 | sed 's/.*/col&,/g') * FROM table;" > test_cases/edge_cases/06_very_long_sql.sql
   ```

3. **验证测试**
   ```bash
   python run_tests_simple.py
   ```

## 测试覆盖矩阵

| 功能 | 测试文件 | 状态 |
|------|----------|------|
| SELECT | basic/01_* | PASS |
| WHERE | basic/02_* | PASS |
| JOIN | basic/03_* | PASS |
| GROUP BY | basic/04_* | PASS |
| INSERT | basic/05_* | PASS |
| CREATE | basic/06_* | PASS |
| 子查询 | complex/01_*,02_*,03_* | PASS |
| CASE WHEN | complex/04_* | PASS |
| 多JOIN | complex/05_* | PASS |
| CTE | complex/06_* | PASS |
| 空SQL | edge_cases/01_* | PASS |
| 特殊字符 | edge_cases/04_* | PASS |
| 多语句 | edge_cases/05_* | PASS |
| PARTITION | spark_specific/01_* | PASS |
| COMMENT | spark_specific/02_* | PASS |
| DISTRIBUTE | spark_specific/03_* | PASS |
| CACHE | spark_specific/04_* | PASS |
| 窗口函数 | window_functions/* | PASS |
| ROW_NUMBER/RANK | window_functions/01_* | PASS |
| LAG/LEAD | window_functions/02_* | PASS |
| 窗口范围 | window_functions/03_* | PASS |
| GROUPING SETS | advanced_grouping/01_* | PASS |
| ROLLUP/CUBE | advanced_grouping/02_* | PASS |
| FILTER子句 | advanced_grouping/03_* | PASS |
| ARRAY/EXPLODE | complex_types/01_* | PASS |
| MAP/STRUCT | complex_types/02_* | PASS |
| LATERAL VIEW | complex_types/03_* | PASS |
| CLUSTER BY | special_syntax/01_* | PASS |
| PIVOT | special_syntax/02_* | PASS |
| TRANSFORM | special_syntax/03_* | PASS |
| SEQUENCE/STACK | advanced_functions/01_* | PASS |
| JSON函数 | advanced_functions/02_* | PASS |
| Lambda表达式 | advanced_functions/03_* | PASS |

## 回归测试说明

regression/ 目录包含曾经出现bug的SQL，用于防止bug重犯：

- `001_comment_spaces.sql` - COMMENT空格被删除
- `002_from_subquery_indent.sql` - FROM子查询未缩进
- `003_internal_empty_lines.sql` - SQL内部空行未剔除

## 新增测试类别说明 (v2.0)

### window_functions/ - 窗口函数测试
测试Spark SQL的窗口函数功能，包括：
- 排名函数：ROW_NUMBER(), RANK(), DENSE_RANK()
- 偏移函数：LAG(), LEAD()
- 窗口范围：ROWS BETWEEN, RANGE BETWEEN
- 取值函数：FIRST_VALUE(), LAST_VALUE()

### advanced_grouping/ - 高级聚合测试
测试高级GROUP BY功能：
- GROUPING SETS - 自定义聚合维度组合
- ROLLUP - 层级聚合
- CUBE - 全维度聚合
- FILTER 子句 - 聚合过滤

### complex_types/ - 复杂数据类型测试
测试Spark SQL的复杂数据类型：
- ARRAY<T> - 数组类型和explode函数
- MAP<K,V> - 映射类型和相关函数
- STRUCT<> - 结构体类型
- LATERAL VIEW - 展开操作

### special_syntax/ - 特殊语法测试
测试Spark SQL的特殊语法：
- CLUSTER BY - 分区排序
- SORT BY - 局部排序
- DISTRIBUTE BY - 数据分发
- PIVOT - 行列转换
- TRANSFORM - 脚本调用
- TABLESAMPLE - 数据采样

### advanced_functions/ - 高级函数测试
测试高级Spark SQL函数：
- sequence, stack - 数据生成函数
- to_json, from_json - JSON转换函数
- Lambda表达式 - transform, filter, aggregate等高阶函数

## 后续改进建议

1. **添加预期结果对比**
   - 为每个测试创建 .expected 文件
   - 对比格式化结果与预期

2. **性能测试**
   - 添加超大型SQL测试
   - 测量格式化时间

3. **错误处理测试**
   - 测试非法SQL的处理
   - 验证错误消息

4. **CI/CD集成**
   - 在提交代码时自动运行测试
   - GitHub Actions 工作流

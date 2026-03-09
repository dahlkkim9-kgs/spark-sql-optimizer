# SQL 格式化工具 - 测试用例库

## 测试用例结构

```
test_cases/
├── basic/              # 基础功能测试 (6个)
│   ├── 01_simple_select.sql
│   ├── 02_select_with_where.sql
│   ├── 03_select_with_joins.sql
│   ├── 04_select_with_group_by.sql
│   ├── 05_insert_select.sql
│   └── 06_create_table.sql
│
├── complex/            # 复杂场景测试 (6个)
│   ├── 01_nested_subquery.sql
│   ├── 02_double_nested_subquery.sql
│   ├── 03_not_in_subquery.sql
│   ├── 04_case_when.sql
│   ├── 05_multiple_joins.sql
│   └── 06_with_cte.sql
│
├── edge_cases/         # 边界情况测试 (5个)
│   ├── 01_empty_sql.sql
│   ├── 02_whitespace_only.sql
│   ├── 03_single_field.sql
│   ├── 04_special_characters.sql
│   └── 05_multiple_statements.sql
│
├── spark_specific/     # Spark SQL 特有功能 (4个)
│   ├── 01_partition_insert.sql
│   ├── 02_comment_spaces.sql
│   ├── 03_distribute_by.sql
│   └── 04_cache_table.sql
│
├── regression/         # 回归测试 (3个)
│   ├── 001_comment_spaces.sql
│   ├── 002_from_subquery_indent.sql
│   └── 003_internal_empty_lines.sql
│
├── window_functions/   # 窗口函数测试 (3个)
│   ├── 01_row_number_rank.sql
│   ├── 02_lag_lead_functions.sql
│   └── 03_window_frame.sql
│
├── advanced_grouping/  # 高级聚合测试 (3个)
│   ├── 01_grouping_sets.sql
│   ├── 02_rollup_cube.sql
│   └── 03_filter_clause.sql
│
├── complex_types/      # 复杂数据类型测试 (3个)
│   ├── 01_array_explode.sql
│   ├── 02_map_struct.sql
│   └── 03_lateral_view.sql
│
├── special_syntax/     # 特殊语法测试 (3个)
│   ├── 01_cluster_sort_distribute.sql
│   ├── 02_pivot.sql
│   └── 03_transform.sql
│
└── advanced_functions/ # 高级函数测试 (3个)
    ├── 01_sequence_stack.sql
    ├── 02_json_functions.sql
    └── 03_lambda_functions.sql
```

## 运行测试

### 运行所有测试
```bash
python run_tests_simple.py
```

### 运行单个测试文件
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from core.formatter_v4_fixed import format_sql_v4_fixed

with open('test_cases/basic/01_simple_select.sql', 'r') as f:
    sql = f.read()

result = format_sql_v4_fixed(sql)
print(result)
"
```

## 添加新测试

1. 在对应类别目录下创建 `.sql` 文件
2. 文件格式：
```sql
-- 测试: 测试名称
-- 预期: 预期结果描述
SELECT ...;
```

3. 运行测试验证

## 测试覆盖

| 类别 | 测试数 | 覆盖功能 |
|------|--------|----------|
| basic | 6 | SELECT, INSERT, CREATE, JOIN, WHERE, GROUP BY |
| complex | 6 | 嵌套子查询, CASE WHEN, CTE, 多表JOIN |
| edge_cases | 5 | 空SQL, 特殊字符, 多语句 |
| spark_specific | 4 | PARTITION, COMMENT, DISTRIBUTE BY, CACHE |
| regression | 3 | 历史bug修复验证 |
| window_functions | 3 | ROW_NUMBER, RANK, LAG, LEAD, 窗口范围 |
| advanced_grouping | 3 | GROUPING SETS, ROLLUP, CUBE, FILTER |
| complex_types | 3 | ARRAY, MAP, STRUCT, LATERAL VIEW |
| special_syntax | 3 | CLUSTER BY, SORT BY, PIVOT, TRANSFORM |
| advanced_functions | 3 | SEQUENCE, JSON函数, Lambda表达式 |

**总计**: 39个测试用例

## 当前状态

```
Results: 39/39 passed
All tests passed!
```

## 新增测试说明 (v2.0)

### 窗口函数测试
- ROW_NUMBER, RANK, DENSE_RANK 等排名函数
- LAG, LEAD 等偏移函数
- 窗口范围子句 (ROWS BETWEEN)

### 高级聚合测试
- GROUPING SETS 自定义聚合
- ROLLUP 层级聚合
- CUBE 全维度聚合
- FILTER 子句聚合过滤

### 复杂数据类型测试
- ARRAY 类型与 explode 函数
- MAP 类型与相关函数
- STRUCT 类型与 named_struct
- LATERAL VIEW 展开操作

### 特殊语法测试
- CLUSTER BY, SORT BY, DISTRIBUTE BY
- PIVOT 行列转换
- TRANSFORM 脚本调用
- TABLESAMPLE 采样

### 高级函数测试
- sequence, stack 生成函数
- to_json, from_json, get_json_object
- Lambda 表达式 (transform, filter, aggregate)

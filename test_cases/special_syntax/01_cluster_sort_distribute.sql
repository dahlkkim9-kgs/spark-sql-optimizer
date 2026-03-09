-- 测试: 特殊语法 - CLUSTER BY, SORT BY, DISTRIBUTE BY
-- 预期: 正确格式化这些特殊排序和分发子句
SELECT *
FROM sales_data
CLUSTER BY department;

SELECT *
FROM sales_data
DISTRIBUTE BY department
SORT BY amount DESC;

SELECT *
FROM large_table
TABLESAMPLE(10 PERCENT)
SEED(123);

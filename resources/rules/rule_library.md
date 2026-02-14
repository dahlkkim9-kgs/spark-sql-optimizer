# Spark SQL 优化规则库

## 高优先级规则 (HIGH)

### SELECT_STAR
- **问题**: 避免使用 SELECT *
- **原因**: 只查询需要的字段以减少网络传输和内存开销
- **建议**: 列出具体需要的字段名

### LIKE_LEADING_WILDCARD
- **问题**: LIKE 以通配符开头
- **原因**: 无法使用索引，性能较差
- **建议**: 考虑使用全文索引或修改查询逻辑

### CROSS_JOIN
- **问题**: 检测到笛卡尔积
- **原因**: CROSS JOIN 可能产生大量数据
- **建议**: 确保这是预期行为或添加JOIN条件

### JOIN_NO_CONDITION
- **问题**: JOIN缺少ON条件
- **原因**: 可能产生意外的笛卡尔积
- **建议**: 添加JOIN条件: JOIN table ON a.id = b.id

## 中优先级规则 (MEDIUM)

### IMPLICIT_CAST
- **问题**: 隐式类型转换
- **原因**: 可能导致性能问题和意外结果
- **建议**: 使用 CAST(字段 AS 类型) 进行显式转换

### OR_IN_WHERE
- **问题**: WHERE中多个OR条件
- **原因**: OR条件可能导致全表扫描
- **建议**: 考虑使用 IN 或 UNION ALL 重写

### HAVING_WHERE
- **问题**: HAVING子句中的条件
- **原因**: 可以在分组前过滤的条件应该下推到WHERE
- **建议**: 将可下推条件移到WHERE子句

### COUNT_DISTINCT_LARGE
- **问题**: COUNT(DISTINCT) 大数据量
- **原因**: 可能导致数据倾斜和性能问题
- **建议**: 考虑使用近似计数函数 approx_count_distinct

### SUBQUERY_DEEP
- **问题**: 深度嵌套子查询
- **原因**: 难以维护且性能较差
- **建议**: 使用CTE（WITH子句）重构

## 低优先级规则 (LOW)

### DISTINCT_ORDER_BY
- **问题**: DISTINCT + ORDER BY
- **原因**: 性能开销大
- **建议**: 考虑是否真的需要排序

### HARDCODED_DATE
- **问题**: 硬编码日期
- **原因**: 灵活性差，不易维护
- **建议**: 使用参数变量替代

### LIMIT_MISSING
- **问题**: ORDER BY无LIMIT
- **原因**: 大数据量可能导致内存溢出
- **建议**: 添加LIMIT限制返回行数

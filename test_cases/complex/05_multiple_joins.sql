-- 测试: 多表JOIN
-- 预期: 每个JOIN换行格式化
SELECT a.col1, b.col2, c.col3 FROM table1 a INNER JOIN table2 b ON a.id = b.id LEFT JOIN table3 c ON b.id = c.id;

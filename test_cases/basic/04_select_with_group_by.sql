-- 测试: GROUP BY 和聚合函数
-- 预期: GROUP BY子句格式化
SELECT department, COUNT(*) as cnt, SUM(salary) as total FROM employees GROUP BY department;

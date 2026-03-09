-- 测试: 高级聚合 - FILTER 子句
-- 预期: 正确格式化FILTER子句
SELECT department
     , SUM(salary) FILTER (WHERE age > 30) AS senior_salary
     , AVG(salary) FILTER (WHERE gender = 'F') AS female_avg
     , COUNT(*) FILTER (WHERE status = 'active') AS active_count
FROM employees
GROUP BY department;

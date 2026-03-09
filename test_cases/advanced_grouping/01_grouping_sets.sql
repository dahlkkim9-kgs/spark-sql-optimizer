-- 测试: 高级聚合 - GROUPING SETS
-- 预期: 正确格式化GROUPING SETS语法
SELECT city
     , department
     , SUM(salary) AS total_salary
FROM employees
GROUP BY GROUPING SETS ((city, department), (city), ());

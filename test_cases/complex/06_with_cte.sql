-- 测试: WITH AS (CTE)
-- 预期: WITH子句格式化，内部SELECT也被格式化
WITH cte AS (SELECT id, name FROM users WHERE active = 1) SELECT * FROM cte;

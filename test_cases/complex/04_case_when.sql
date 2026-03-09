-- 测试: CASE WHEN表达式
-- 预期: CASE WHEN换行，THEN/ELSE对齐
SELECT CASE WHEN age < 18 THEN 'minor' WHEN age >= 18 AND age < 60 THEN 'adult' ELSE 'senior' END AS age_group FROM users;

-- 测试: 特殊语法 - TRANSFORM 脚本
-- 预期: 正确格式化TRANSFORM语法
SELECT TRANSFORM (user_id, name)
USING 'python script.py'
AS (user_id INT, name STRING)
FROM users;

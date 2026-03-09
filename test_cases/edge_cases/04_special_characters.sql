-- 测试: 特殊字符和转义
-- 预期: 单引号、百分号等正确处理
SELECT * FROM users WHERE name LIKE '%test%' AND email LIKE 'a\_b@example.com' ESCAPE '\';

-- 测试: FROM子查询嵌套
-- 预期: 子查询缩进4个空格
SELECT * FROM (SELECT id, name FROM users WHERE age > 18) t;

-- 测试: NOT IN 子查询
-- 预期: NOT IN后的子查询正确缩进
SELECT * FROM users WHERE id NOT IN (SELECT id FROM deleted_users);

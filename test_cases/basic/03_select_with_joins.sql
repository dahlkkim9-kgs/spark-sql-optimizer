-- 测试: 多表JOIN
-- 预期: JOIN语句格式化，ON条件对齐
SELECT u.name, o.order_id FROM users u INNER JOIN orders o ON u.id = o.user_id;

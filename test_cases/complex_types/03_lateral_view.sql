-- 测试: 复杂数据类型 - LATERAL VIEW 多列展开
-- 预期: 正确格式化多LATERICOL VIEW
SELECT user_id
     , num
     , letter
FROM users
LATERAL VIEW explode(array(1, 2, 3)) t1 AS num
LATERAL VIEW explode(array('a', 'b', 'c')) t2 AS letter;

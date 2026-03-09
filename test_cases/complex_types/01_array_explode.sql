-- 测试: 复杂数据类型 - ARRAY 和 EXPLODE
-- 预期: 正确格式化ARRAY类型和EXPLODE函数
SELECT user_id
     , explode(array(1, 2, 3)) AS num
FROM users;

SELECT user_id
     , explode(split('a,b,c', ',')) AS tag
FROM users;

SELECT user_id
     , num
FROM users
LATERAL VIEW explode(array(1, 2, 3)) t AS num;

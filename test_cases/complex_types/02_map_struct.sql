-- 测试: 复杂数据类型 - MAP 和 STRUCT
-- 预期: 正确格式化MAP和STRUCT类型
SELECT user_id
     , map('a', 1, 'b', 2, 'c', 3) AS properties
     , map_keys(map('a', 1, 'b', 2)) AS keys
     , map_values(map('a', 1, 'b', 2)) AS values
FROM users;

SELECT user_id
     , named_struct('name', 'Alice', 'age', 30, 'city', 'NYC') AS user_info
     , struct(col1, col2).col1 AS first_col
FROM table1;

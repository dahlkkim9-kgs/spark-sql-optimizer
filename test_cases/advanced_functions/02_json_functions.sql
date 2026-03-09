-- 测试: 高级函数 - JSON 函数
-- 预期: 正确格式化to_json, from_json, get_json_object等函数
SELECT to_json(named_struct('a', 1, 'b', 2)) AS json_str
FROM table1;

SELECT to_json(map('a', named_struct('b', 1))) AS json_str
FROM table1;

SELECT to_json(array(map('a', 1), map('b', 2))) AS json_array
FROM table1;

SELECT get_json_object('{"a": 1, "b": 2}', '$.a') AS value_a
FROM table1;

SELECT from_json('{"name": "Alice", "age": 30}', 'STRUCT<name: STRING, age: INT>') AS user_struct
FROM table1;

SELECT json_tuple('{"a": 1, "b": 2}', 'a', 'b') AS (a, b)
FROM table1;

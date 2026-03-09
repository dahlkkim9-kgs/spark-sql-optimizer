-- 测试: 多语句SQL
-- 预期: 每个语句独立格式化，语句间有空行
DROP TABLE IF EXISTS test_temp;CREATE TABLE test_temp AS SELECT * FROM users;SELECT * FROM test_temp;

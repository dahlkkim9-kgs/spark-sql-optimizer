-- 测试: INSERT INTO ... SELECT
-- 预期: INSERT和SELECT都格式化
INSERT INTO table_target SELECT col1, col2 FROM table_source WHERE active = 1;

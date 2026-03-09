-- 测试: INSERT INTO ... PARTITION
-- 预期: PARTITION子句正确处理，SELECT格式化
INSERT INTO db.table PARTITION(dt='20240101') SELECT col1, col2 FROM source_table;

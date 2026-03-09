-- 测试: COMMENT中的空格必须保留
-- 预期: COMMENT '...' 内的空格完整保留
CREATE TABLE test (id STRING COMMENT 'ID            ', name STRING COMMENT 'NAME        ');

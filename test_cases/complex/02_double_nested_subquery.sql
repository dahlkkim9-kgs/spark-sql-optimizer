-- 测试: 双层嵌套子查询
-- 预期: 外层4空格，内层8空格缩进
SELECT * FROM (SELECT * FROM (SELECT a FROM t1) t2) t3;

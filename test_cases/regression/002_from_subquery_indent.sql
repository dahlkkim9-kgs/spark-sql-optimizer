-- 回归测试: FROM子查询缩进问题
-- 问题历史: FROM (SELECT ...) 中的子查询没有正确缩进
-- 修复版本: v4_fixed
INSERT INTO TABLE test SELECT a, b FROM (SELECT * FROM users WHERE age > 18) t;

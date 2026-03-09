-- 回归测试: SQL语句内部空行未剔除
-- 问题历史: SELECT和FROM之间、WHERE和GROUP BY之间有空行
-- 修复版本: v4_fixed
CREATE TABLE test AS SELECT a, b FROM source WHERE flag IN ('1', '2') GROUP BY a;

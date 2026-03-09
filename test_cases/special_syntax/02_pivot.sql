-- 测试: 特殊语法 - PIVOT 行列转换
-- 预期: 正确格式化PIVOT语法
SELECT *
FROM sales_data
PIVOT (
    SUM(amount)
    FOR product IN ('iPhone' AS iphone, 'Samsung' AS samsung, 'Xiaomi' AS xiaomi)
);

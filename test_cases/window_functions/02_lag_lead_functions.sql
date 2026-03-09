-- 测试: 窗口函数 - LAG, LEAD
-- 预期: 正确格式化LAG和LEAD函数
SELECT date
     , product
     , sales
     , LAG(sales, 1, 0) OVER (PARTITION BY product ORDER BY date) AS prev_sales
     , LEAD(sales, 1, 0) OVER (PARTITION BY product ORDER BY date) AS next_sales
FROM sales_data;

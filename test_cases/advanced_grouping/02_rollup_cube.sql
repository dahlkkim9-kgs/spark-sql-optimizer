-- 测试: 高级聚合 - ROLLUP 和 CUBE
-- 预期: 正确格式化ROLLUP和CUBE语法
SELECT country
     , province
     , city
     , COUNT(*) AS count
FROM locations
GROUP BY ROLLUP (country, province, city);

SELECT year
     , product
     , SUM(revenue) AS total_revenue
FROM sales
GROUP BY CUBE (year, product);

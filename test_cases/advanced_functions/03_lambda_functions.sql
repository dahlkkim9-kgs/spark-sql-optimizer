-- 测试: 高级函数 - Lambda 函数 (transform, filter, exists)
-- 预期: 正确格式化lambda表达式
SELECT user_id
     , transform(array(1, 2, 3), x -> x * 2) AS doubled
     , filter(array(1, 2, 3, 4, 5), x -> x % 2 = 0) AS evens
     , exists(array(1, 2, 3), x -> x > 2) AS has_gt_2
FROM users;

SELECT user_id
     , transform(array(1, NULL, 3), x -> coalesce(x, 0)) AS no_nulls
     , aggregate(array(1, 2, 3), 0, (acc, x) -> acc + x) AS total
FROM users;

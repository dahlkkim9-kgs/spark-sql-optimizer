-- 测试: 括号内的连续 OR/AND 条件换行
-- 预期: 括号内的连续 OR/AND 条件应该换行并缩进
SELECT *
FROM users
WHERE (status='active' OR status='pending' OR status='suspended')
  AND (type='premium' OR type='vip')
  AND age > 18;

-- 测试: 复杂嵌套括号内的 OR/AND
SELECT *
FROM orders
WHERE (status IN ('completed', 'pending')
        OR payment_status='paid'
        OR refund_requested=TRUE)
  AND amount > 100;

-- 测试: CASE WHEN 中括号内的 OR/AND
SELECT CASE
    WHEN (a=1 OR b=2 OR c=3)
         THEN 'low'
    WHEN (d=4 AND e=5 AND f=6)
         THEN 'high'
    ELSE 'medium'
END AS category
FROM table1;

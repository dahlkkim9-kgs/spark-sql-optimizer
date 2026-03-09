-- 测试: 窗口函数 - ROW_NUMBER, RANK, DENSE_RANK
-- 预期: 正确格式化窗口函数，OVER子句换行显示
SELECT employee_id
     , department
     , salary
     , ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num
     , RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank_num
     , DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dense_rank_num
FROM employees;

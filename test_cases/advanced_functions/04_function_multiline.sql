-- 测试智能函数格式化：简单函数保持单行
SELECT UPPER(name), LOWER(email)
FROM users;

-- 测试智能函数格式化：多参数函数换行
SELECT CONCAT(first_name, last_name, age, city) AS full_info
FROM customers;

-- 测试智能函数格式化：嵌套函数递归格式化
SELECT CONCAT(LPAD(id, 10, '0'), SUBSTRING(name, 1, 5)) AS formatted_id
FROM products;

-- 测试智能函数格式化：复杂嵌套
SELECT
    CONCAT(
        LPAD(a, 10, '0'),
        SUBSTRING(b, 1, 5),
        UPPER(c)
    ) AS result
FROM table1;

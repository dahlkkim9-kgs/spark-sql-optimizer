-- 测试: 高级函数 - SEQUENCE, STACK
-- 预期: 正确格式化SEQUENCE和STACK函数
SELECT explode(sequence(1, 100)) AS num
FROM dummy;

SELECT explode(sequence(0, 100, 20)) AS num
FROM dummy;

SELECT stack(2, 'M', 'F') AS sex
FROM dummy;

SELECT stack(3, 1, 'one', 2, 'two', 3, 'three') AS (id, name)
FROM dummy;

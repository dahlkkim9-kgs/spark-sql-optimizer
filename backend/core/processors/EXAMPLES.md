# SQL 格式化示例

本文档展示了 Spark SQL 优化工具支持的各种语法格式的输入输出示例。

## 集合操作 (Set Operations)

### UNION ALL

**输入**:
```sql
select a, b from t1 union all select c, d from t2
```

**输出** (keyword_case='upper'):
```sql
SELECT a
     , b
FROM t1
UNION ALL
SELECT c
     , d
FROM t2
```

### UNION

**输入**:
```sql
SELECT id FROM users WHERE status='active' UNION SELECT id FROM archived_users
```

**输出**:
```sql
SELECT id
FROM users
WHERE status = 'active'
UNION
SELECT id
FROM archived_users
```

### INTERSECT

**输入**:
```sql
select product_id from sales_2023 intersect select product_id from sales_2024
```

**输出**:
```sql
SELECT product_id
FROM sales_2023
INTERSECT
SELECT product_id
FROM sales_2024
```

### EXCEPT / MINUS

**输入**:
```sql
SELECT id FROM current EXCEPT SELECT id FROM previous
```

**输出**:
```sql
SELECT id
FROM current
EXCEPT
SELECT id
FROM previous
```

### 多重集合操作

**输入**:
```sql
select a from t1 union all select b from t2 union select c from t3 intersect select d from t4
```

**输出**:
```sql
SELECT a
FROM t1
UNION ALL
SELECT b
FROM t2
UNION
SELECT c
FROM t3
INTERSECT
SELECT d
FROM t4
```

### 带 JOIN 的集合操作

**输入**:
```sql
SELECT t1.a, t2.b FROM t1 JOIN t2 ON t1.id = t2.id UNION ALL SELECT t3.c, t4.d FROM t3 LEFT JOIN t4 ON t3.id = t4.id
```

**输出**:
```sql
SELECT t1.a
     , t2.b
FROM t1
INNER JOIN t2
    ON t1.id = t2.id
UNION ALL
SELECT t3.c
     , t4.d
FROM t3
LEFT JOIN t4
    ON t3.id = t4.id
```

## 窗口函数 (Window Functions)

### 基本 OVER 子句

**输入**:
```sql
SELECT ROW_NUMBER() OVER (ORDER BY date) as row_num, * FROM events
```

**输出**:
```sql
SELECT ROW_NUMBER() OVER (
                            ORDER BY date
                          ) AS row_num
     , *
FROM events
```

### PARTITION BY

**输入**:
```sql
SELECT department, employee, salary, RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rank FROM employees
```

**输出**:
```sql
SELECT department
     , employee
     , salary
     , RANK() OVER (
                   PARTITION BY department
                   ORDER BY salary DESC
                  ) AS rank
FROM employees
```

### 多列 PARTITION BY

**输入**:
```sql
SELECT product, region, sales, SUM(sales) OVER (PARTITION BY product, region ORDER BY month) as running_total FROM monthly_sales
```

**输出**:
```sql
SELECT product
     , region
     , sales
     , SUM(sales) OVER (
                       PARTITION BY product
                                   , region
                       ORDER BY month
                      ) AS running_total
FROM monthly_sales
```

### Window Frame (ROWS BETWEEN)

**输入**:
```sql
SELECT date, value, AVG(value) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as moving_avg FROM metrics
```

**输出**:
```sql
SELECT date
     , value
     , AVG(value) OVER (
                       ORDER BY date
                       ROWS BETWEEN 2 PRECEDING
                                    AND CURRENT ROW
                      ) AS moving_avg
FROM metrics
```

### 多个窗口函数

**输入**:
```sql
SELECT id, SUM(amount) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as total, AVG(amount) OVER (ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) as avg FROM transactions
```

**输出**:
```sql
SELECT id
     , SUM(amount) OVER (
                        ORDER BY date
                        ROWS BETWEEN UNBOUNDED PRECEDING
                                     AND CURRENT ROW
                       ) AS total
     , AVG(amount) OVER (
                        ORDER BY date
                        ROWS BETWEEN 1 PRECEDING
                                    AND 1 FOLLOWING
                       ) AS avg
FROM transactions
```

### LEAD/LAG 函数

**输入**:
```sql
SELECT employee, salary, LEAD(salary, 1) OVER (ORDER BY hire_date) as next_salary, LAG(salary, 1, 0) OVER (ORDER BY hire_date) as prev_salary FROM employees
```

**输出**:
```sql
SELECT employee
     , salary
     , LEAD(salary, 1) OVER (
                             ORDER BY hire_date
                            ) AS next_salary
     , LAG(salary, 1, 0) OVER (
                              ORDER BY hire_date
                             ) AS prev_salary
FROM employees
```

### Named Window

**输入**:
```sql
SELECT SUM(amount) OVER w as total, AVG(amount) OVER w as average FROM monthly_sales WINDOW w AS (PARTITION BY product ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
```

**输出**:
```sql
SELECT SUM(amount) OVER w AS total
     , AVG(amount) OVER w AS average
FROM monthly_sales
WINDOW w AS (
            PARTITION BY product
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING
                         AND CURRENT ROW
           )
```

## 数据操作 (Data Operations)

### MERGE INTO

**输入**:
```sql
MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET target.value = source.value
```

**输出**:
```sql
MERGE INTO target
USING source
ON target.id = source.id
WHEN MATCHED
    THEN UPDATE
         SET target.value = source.value
```

### MERGE with DELETE

**输入**:
```sql
MERGE INTO customers t USING updates s ON t.id = s.id WHEN MATCHED AND s.is_deleted = 1 THEN DELETE WHEN MATCHED THEN UPDATE SET t.name = s.name, t.email = s.email
```

**输出**:
```sql
MERGE INTO customers t
USING updates s
ON t.id = s.id
WHEN MATCHED
    AND s.is_deleted = 1
    THEN DELETE
WHEN MATCHED
    THEN UPDATE
         SET t.name = s.name
           , t.email = s.email
```

### MERGE with INSERT

**输入**:
```sql
MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET target.value = source.value WHEN NOT MATCHED THEN INSERT (id, value) VALUES (source.id, source.value)
```

**输出**:
```sql
MERGE INTO target
USING source
ON target.id = source.id
WHEN MATCHED
    THEN UPDATE
         SET target.value = source.value
WHEN NOT MATCHED
    THEN INSERT
         (id, value)
         VALUES (source.id, source.value)
```

### INSERT OVERWRITE

**输入**:
```sql
INSERT OVERWRITE TABLE sales_archive SELECT * FROM sales WHERE date < '2024-01-01'
```

**输出**:
```sql
INSERT OVERWRITE TABLE sales_archive
SELECT *
FROM sales
WHERE date < '2024-01-01'
```

### INSERT OVERWRITE with PARTITION

**输入**:
```sql
INSERT OVERWRITE TABLE partitions PARTITION (year='2024', month='01') SELECT id, amount, date FROM transactions WHERE year(date) = 2024 AND month(date) = 1
```

**输出**:
```sql
INSERT OVERWRITE TABLE partitions
PARTITION (year = '2024', month = '01')
SELECT id
     , amount
     , date
FROM transactions
WHERE year(date) = 2024
  AND month(date) = 1
```

## 高级转换 (Advanced Transforms)

### LATERAL VIEW EXPLODE

**输入**:
```sql
SELECT id, item FROM products LATERAL VIEW EXPLODE(items) exploded_items AS item
```

**输出**:
```sql
SELECT id
     , item
FROM products
LATERAL VIEW EXPLODE(items) exploded_items AS item
```

### LATERAL VIEW OUTER

**输入**:
```sql
SELECT user_id, tag FROM users LATERAL VIEW OUTER EXPLODE(tags) t AS tag
```

**输出**:
```sql
SELECT user_id
     , tag
FROM users
LATERAL VIEW OUTER EXPLODE(tags) t AS tag
```

### 多个 LATERAL VIEW

**输入**:
```sql
SELECT id, category, subcategory FROM items LATERAL VIEW EXPLODE(categories) c AS category LATERAL VIEW EXPLODE(subcategories) s AS subcategory
```

**输出**:
```sql
SELECT id
     , category
     , subcategory
FROM items
LATERAL VIEW EXPLODE(categories) c AS category
LATERAL VIEW EXPLODE(subcategories) s AS subcategory
```

### LATERAL VIEW JSON_TUPLE

**输入**:
```sql
SELECT id, json_tuple(data, 'name', 'age', 'city') as (n, a, c) FROM events
```

**输出**:
```sql
SELECT id
     , json_tuple(data, 'name', 'age', 'city') AS (n, a, c)
FROM events
LATERAL VIEW json_tuple(data, 'name', 'age', 'city') jt AS n
                                                              , a
                                                              , c
```

### CLUSTER BY

**输入**:
```sql
SELECT * FROM large_table CLUSTER BY id, date
```

**输出**:
```sql
SELECT *
FROM large_table
CLUSTER BY id
          , date
```

### DISTRIBUTE BY

**输入**:
```sql
SELECT key, value FROM source DISTRIBUTE BY key SORT BY value
```

**输出**:
```sql
SELECT key
     , value
FROM source
DISTRIBUTE BY key
SORT BY value
```

### PIVOT (基础支持)

**输入**:
```sql
SELECT * FROM sales PIVOT (SUM(amount) FOR month IN ('Jan', 'Feb', 'Mar'))
```

**输出**:
```sql
SELECT *
FROM sales
PIVOT (
    SUM(amount)
    FOR month IN ('Jan', 'Feb', 'Mar')
)
```

## 混合语法

### Window + Set Operations

**输入**:
```sql
SELECT dept, emp, RANK() OVER (PARTITION BY dept ORDER BY salary DESC) as rank FROM salaries WHERE year = 2024 UNION ALL SELECT dept, emp, RANK() OVER (PARTITION BY dept ORDER BY salary DESC) as rank FROM salaries WHERE year = 2023
```

**输出**:
```sql
SELECT dept
     , emp
     , RANK() OVER (
                   PARTITION BY dept
                   ORDER BY salary DESC
                  ) AS rank
FROM salaries
WHERE year = 2024
UNION ALL
SELECT dept
     , emp
     , RANK() OVER (
                   PARTITION BY dept
                   ORDER BY salary DESC
                  ) AS rank
FROM salaries
WHERE year = 2023
```

### LATERAL VIEW + Window

**输入**:
```sql
SELECT id, category, ROW_NUMBER() OVER (PARTITION BY id ORDER BY category) as rn FROM items LATERAL VIEW EXPLODE(categories) c AS category
```

**输出**:
```sql
SELECT id
     , category
     , ROW_NUMBER() OVER (
                         PARTITION BY id
                         ORDER BY category
                        ) AS rn
FROM items
LATERAL VIEW EXPLODE(categories) c AS category
```

## 注释保留

### 单行注释

**输入**:
```sql
-- Get active users
SELECT id, name
FROM users
WHERE status = 'active' -- Only active
```

**输出**:
```sql
-- Get active users
SELECT id
     , name
FROM users
WHERE status = 'active' -- Only active
```

### 多行注释

**输入**:
```sql
/*
 * Complex query to calculate
 * monthly revenue by department
 */
SELECT dept, SUM(amount) as revenue
FROM sales
GROUP BY dept
```

**输出**:
```sql
/*
 * Complex query to calculate
 * monthly revenue by department
 */
SELECT dept
     , SUM(amount) AS revenue
FROM sales
GROUP BY dept
```

### 在复杂语句中的注释

**输入**:
```sql
MERGE INTO target t -- Target table
USING source s -- Source table
ON t.id = s.id -- Join condition
WHEN MATCHED THEN -- Update if exists
UPDATE SET t.value = s.value
```

**输出**:
```sql
MERGE INTO target t -- Target table
USING source s -- Source table
ON t.id = s.id -- Join condition
WHEN MATCHED -- Update if exists
    THEN UPDATE
         SET t.value = s.value
```

## API 使用示例

### Python 请求

```python
import requests

response = requests.post('http://localhost:8000/api/format', json={
    'sql': 'SELECT a FROM t1 UNION ALL SELECT b FROM t2',
    'keyword_case': 'upper',
    'line_width': 120
})

result = response.json()
print(result['formatted_sql'])
```

### cURL 请求

```bash
curl -X POST http://localhost:8000/api/format \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT a FROM t1 UNION ALL SELECT b FROM t2",
    "keyword_case": "upper"
  }'
```

### JavaScript 请求

```javascript
const response = await fetch('http://localhost:8000/api/format', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    sql: 'SELECT a FROM t1 UNION ALL SELECT b FROM t2',
    keyword_case: 'upper'
  })
});

const result = await response.json();
console.log(result.formatted_sql);
```

## 性能考虑

### 大型 SQL 语句

对于包含数千行的复杂 SQL，格式化器仍然可以高效处理:

```sql
-- 100+ 列的 SELECT 语句
SELECT col1, col2, col3, ..., col100 FROM large_table
```

将正确对齐所有列。

### 嵌套子查询

支持深层嵌套的子查询，保持正确的缩进层级:

```sql
SELECT *
FROM (
  SELECT *
  FROM (
    SELECT * FROM inner_table
  ) t2
) t1
```

## 常见用例

### ETL 管道 SQL

```sql
INSERT OVERWRITE TABLE fact_sales
SELECT
    date_dim.date_key,
    product.product_key,
    customer.customer_key,
    sales.amount
FROM staging_sales sales
INNER JOIN dim_date date_dim ON sales.date = date_dim.date
INNER JOIN dim_product product ON sales.product_id = product.product_id
INNER JOIN dim_customer customer ON sales.customer_id = customer.customer_id
```

### 数据分析查询

```sql
SELECT
    department,
    employee,
    salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as salary_rank,
    AVG(salary) OVER (PARTITION BY department) as dept_avg_salary,
    salary - AVG(salary) OVER (PARTITION BY department) as diff_from_avg
FROM employees
WHERE status = 'active'
```

### 数据合并操作

```sql
MERGE INTO customer_master t
USING customer_updates s
ON t.customer_id = s.customer_id
WHEN MATCHED AND s.is_deleted = 1 THEN
    DELETE
WHEN MATCHED THEN
    UPDATE SET
        t.name = s.name,
        t.email = s.email,
        t.updated_at = s.updated_at
WHEN NOT MATCHED THEN
    INSERT (customer_id, name, email, created_at)
    VALUES (s.customer_id, s.name, s.email, s.created_at)
```

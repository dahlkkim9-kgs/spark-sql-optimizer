# Spark SQL 优化工具 - 开发指南

> Version: v1.0
> Last Updated: 2026-02-27

## 快速开始

### 核心功能

| 功能 | 模块 | 说明 |
|-----|------|------|
| SQL格式化 (V4) | `formatter_v4.py` | 支持注释保留的格式化器 |
| SQL格式化 (V3) | `formatter_v3.py` | 基础格式化器 |
| 注释保留 | `comment_preserver.py` | 提取和重新插入注释 |
| SQL静态分析 | `analyzer.py` | 检测性能问题 |
| 智能重写建议 | `rules/` | 优化规则库 |

### 推荐使用 V4 格式化器

```python
from core.formatter_v4 import format_sql_v4

sql = """SELECT id -- 主键
     , name -- 名称
FROM table1 -- 主表
WHERE status = 1 -- 有效状态
;"""

result = format_sql_v4(sql)
print(result)
```

输出:
```sql
SELECT
       id -- 主键
     , name -- 名称
FROM
      table1 -- 主表
WHERE
      status = 1 -- 有效状态
;
```

## 项目结构

```
backend/
├── core/
│   ├── formatter_v4.py      # V4格式化器 (推荐)
│   ├── formatter_v3.py      # V3格式化器
│   ├── comment_preserver.py # 注释保留模块
│   └── analyzer.py          # SQL分析器
├── api/
│   └── main.py              # FastAPI服务
└── tests/
    ├── test_formatter_v4.py
    ├── test_comment_preserver.py
    └── test_real_sql_comments.py
```

## 格式化器版本选择

| 版本 | 特点 | 使用场景 |
|-----|------|---------|
| V4 | 支持注释保留 | 生产环境SQL (推荐) |
| V3 | 基础格式化 | 无注释的简单SQL |

## API端点

### V4格式化 (带注释保留)

```
POST /format/v4
Content-Type: application/json

{
  "sql": "SELECT id -- comment FROM table"
}
```

### V3格式化 (基础)

```
POST /format
Content-Type: application/json

{
  "sql": "SELECT id FROM table"
}
```

## 测试

```bash
# 运行所有测试
cd backend
python -m pytest tests/ -v

# 运行V4相关测试
python -m pytest tests/test_formatter_v4.py tests/test_comment_preserver.py -v
```

## 开发指南

1. **添加新格式化规则**: 修改 `formatter_v3.py`
2. **改进注释处理**: 修改 `comment_preserver.py`
3. **添加测试**: 在 `tests/` 目录添加测试文件

## 相关文档

- [格式化器已知限制](./格式化器已知限制_20260214.md)
- [集成指南](../INTEGRATION_GUIDE.md)
- [项目结构](../PROJECT_STRUCTURE.md)

"""
FastAPI 主应用
Spark SQL优化工具的REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# 处理 PyInstaller 打包后的路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的环境
    # 获取可执行文件所在目录
    if hasattr(sys, '_MEIPASS'):
        # 数据文件被解压到的临时目录
        sys.path.insert(0, os.path.join(sys._MEIPASS, 'core'))
        sys.path.insert(0, sys._MEIPASS)
    else:
        # 备用方案
        script_dir = os.path.dirname(os.path.abspath(sys.executable))
        sys.path.insert(0, os.path.join(script_dir, 'core'))
else:
    # 开发环境
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.analyzer import StaticAnalyzer
from core.formatter_v4 import format_sql_v4


app = FastAPI(
    title="Spark SQL 优化工具 API",
    description="离线Spark SQL静态分析和优化建议",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 初始化分析器
analyzer = StaticAnalyzer()


# 数据模型
class SQLRequest(BaseModel):
    sql: str
    filename: Optional[str] = None


class Issue(BaseModel):
    rule: str
    severity: str
    message: str
    line: int
    suggestion: str


class AnalysisResult(BaseModel):
    file: Optional[str]
    original_sql: str
    optimized_sql: str
    issues: List[Issue]
    issue_count: int
    high_priority: int
    medium_priority: int
    low_priority: int


class FormatRequest(BaseModel):
    sql: str
    keyword_case: Optional[str] = "upper"  # upper, lower, capitalize
    indent: Optional[int] = 4
    comma_start: Optional[bool] = False
    semicolon: Optional[bool] = False


class FormatResult(BaseModel):
    original_sql: str
    formatted_sql: str


@app.get("/")
def read_root():
    """API根路径"""
    return {
        "name": "Spark SQL 优化工具",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalysisResult)
def analyze_sql(request: SQLRequest):
    """
    分析SQL并提供优化建议

    - **sql**: Spark SQL语句
    - **filename**: 可选的文件名
    """
    result = analyzer.analyze(request.sql, filename=request.filename)
    return result


@app.post("/analyze/file")
def analyze_file(file_path: str):
    """
    分析SQL文件

    - **file_path**: SQL文件的绝对路径
    """
    result = analyzer.analyze_file(file_path)
    return result


@app.post("/analyze/batch")
def analyze_batch(folder: str):
    """
    批量分析文件夹中的SQL文件

    - **folder**: 文件夹路径
    """
    results = analyzer.analyze_batch(folder)
    return {
        "total_files": len(results),
        "results": results
    }


@app.get("/rules")
def get_rules():
    """获取所有优化规则列表"""
    return {
        "rules": [
            {
                "name": rule["name"],
                "severity": rule["severity"],
                "description": rule["message"]
            }
            for rule in analyzer.rules
        ]
    }


@app.post("/format", response_model=FormatResult)
def format_sql(request: FormatRequest):
    """
    格式化SQL语句

    - **sql**: 原始SQL语句
    - **keyword_case**: 关键字大小写 (upper/lower/capitalize)
    - **indent**: 缩进空格数
    - **comma_start**: 逗号是否在行首
    - **semicolon**: 结尾是否添加分号
    """
    formatted = analyzer.format_sql(
        request.sql,
        keyword_case=request.keyword_case,
        indent=request.indent,
        comma_start=request.comma_start,
        semicolon=request.semicolon
    )
    return {
        "original_sql": request.sql,
        "formatted_sql": formatted
    }


@app.post("/format/v4")
async def format_sql_v4_endpoint(request: FormatRequest):
    """Format SQL with comment preservation and multi-statement support"""
    try:
        from core.formatter_v4 import _split_by_semicolon

        # 按分号分割SQL语句（保留括号和字符串）
        statements = _split_by_semicolon(request.sql)

        # 格式化每个语句
        formatted_statements = []
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:  # 忽略空语句
                formatted = format_sql_v4(stmt)
                formatted_statements.append(formatted)

        # 合并所有格式化结果，用空行分隔
        result = '\n\n'.join(formatted_statements)
        return {"formatted": result, "success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}


@app.post("/format/v4fixed")
async def format_sql_v4fixed_endpoint(request: FormatRequest):
    """Format SQL with v4_fixed - 修复注释中分号导致内容丢失的问题"""
    try:
        import re
        import sys

        # 强制重新加载模块
        for mod in list(sys.modules.keys()):
            if 'formatter' in mod:
                del sys.modules[mod]

        from core.formatter_v4_fixed import format_sql_v4_fixed

        # 使用 v4_fixed 版本格式化
        result = format_sql_v4_fixed(request.sql, keyword_case=request.keyword_case)

        # 后处理已移除 - formatter_v4_fixed 内部已正确处理 FROM 换行
        # 之前的后处理逻辑存在 bug，会导致 FROM 和表名连接在一起
        # 问题：parts[1] 包含了 FROM 前的缩进空格，但代码只保留了 FROM 关键字
        # 修复：依赖 formatter_v4_fixed 内部的 _protect_from_newline 和 _restore_from_newline

        return {"formatted": result, "success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}


@app.post("/format/v5")
async def format_sql_v5_endpoint(request: FormatRequest):
    """Format SQL with v5 - 支持高级语法（集合操作、窗口函数、MERGE、LATERAL VIEW等）"""
    try:
        import sys
        import os
        import re

        # 确保 core 目录在路径中
        core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        # 清除所有 formatter 相关模块缓存
        modules_to_remove = [k for k in sys.modules.keys()
                              if 'formatter' in k or 'parser' in k or 'processor' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # 直接导入各个组件
        from parser.sql_classifier import SQLClassifier
        from processors.set_operations import SetOperationsProcessor
        from processors.window_functions import WindowFunctionsProcessor
        from processors.data_operations import DataOperationsProcessor
        from processors.advanced_transforms import AdvancedTransformsProcessor
        from formatter_v4_fixed import format_sql_v4_fixed

        # 分类 SQL
        syntax_types = SQLClassifier.classify(request.sql)

        # 根据类型选择处理器
        if 'data_operations' in syntax_types:
            processor = DataOperationsProcessor()
            result = processor.process(request.sql, keyword_case=request.keyword_case or 'upper')
        elif 'set_operations' in syntax_types:
            processor = SetOperationsProcessor()
            result = processor.process(request.sql, keyword_case=request.keyword_case or 'upper')
        elif 'window_functions' in syntax_types:
            processor = WindowFunctionsProcessor()
            result = processor.process(request.sql, keyword_case=request.keyword_case or 'upper')
        elif 'advanced_transforms' in syntax_types:
            processor = AdvancedTransformsProcessor()
            result = processor.process(request.sql, keyword_case=request.keyword_case or 'upper')
        else:
            # 使用 v4_fixed 作为默认
            result = format_sql_v4_fixed(request.sql, keyword_case=request.keyword_case or 'upper')

        return {"formatted": result, "success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}


@app.post("/api/format-v5")
async def format_sql_v5_sqlglot_endpoint(request: FormatRequest):
    """v5 格式化 API (基于 sqlglot AST 解析)"""
    try:
        import sys
        import os

        # 确保 core 目录在路径中
        core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        from core.formatter_v5_sqlglot import format_sql_v5

        # 使用 v5 sqlglot 版本格式化
        formatted = format_sql_v5(request.sql, indent=request.indent or 4)

        return {
            "success": True,
            "formatted": formatted,
            "version": "v5-sqlglot"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)

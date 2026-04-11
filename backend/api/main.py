"""
FastAPI 主应用
Spark SQL优化工具的REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import socket
import webbrowser

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
from core.formatter_v4_fixed import format_sql_v4_fixed

# 版本信息
API_VERSION = "1.0.0"
FORMATTER_VERSION = "v5.0-20260324-sqlglot"
FORMATTER_FILE = "formatter_v5_sqlglot.py"

app = FastAPI(
    title="Spark SQL 优化工具 API",
    description="离线Spark SQL静态分析和优化建议",
    version=API_VERSION
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


class LegacyFormatOptions(BaseModel):
    keyword_case: Optional[str] = "upper"  # upper 或 lower


class LegacyFormatRequest(BaseModel):
    sql: str
    options: Optional[LegacyFormatOptions] = None
    # 兼容部分调用方直接传 keyword_case 的情况
    keyword_case: Optional[str] = None
    # 缩进空格数
    indent: Optional[int] = 4


@app.get("/")
def read_root():
    """单机版：返回前端页面；开发版：返回 API 信息"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，返回前端 index.html
        if hasattr(sys, '_MEIPASS'):
            static_dir = os.path.join(sys._MEIPASS, 'frontend', 'build')
        else:
            static_dir = os.path.join(os.path.dirname(sys.executable), 'frontend', 'build')
        index_path = os.path.join(static_dir, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {
        "name": "Spark SQL 优化工具",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查，返回服务状态和版本信息"""
    return {
        "status": "healthy",
        "service": "spark-sql-optimizer",
        "api_version": API_VERSION,
        "formatter_version": FORMATTER_VERSION,
        "formatter_file": FORMATTER_FILE
    }

@app.get("/api/health")
def health_check_api():
    """兼容旧前端的健康检查路径"""
    return health_check()


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
    """Format SQL with v5 - 使用 sqlglot AST 解析 + V4 格式化

    V5 架构：
    1. sqlglot 解析验证语法正确性
    2. V4 formatter 应用格式化风格

    优势：
    - 准确解析复杂嵌套、新语法
    - 保持 V4 风格一致性
    """
    try:
        import sys
        import os

        # 确保 core 目录在路径中
        core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        from core.formatter_v5_sqlglot import format_sql_v5

        # 使用 V5 sqlglot 版本格式化
        result = format_sql_v5(request.sql, indent=request.indent or 4)

        return {"formatted": result, "success": True, "version": "v5-sqlglot"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}

@app.post("/api/format")
async def format_sql_legacy_endpoint(request: LegacyFormatRequest):
    """
    主格式化端点（使用 V4 fixed）

    返回结构：
    { success: bool, formatted: str, original: str, error?: str, version?: str }

    版本信息：确保前端可以验证使用的格式化器版本
    """
    try:
        import re
        import sys

        # 强制重新加载模块
        for mod in list(sys.modules.keys()):
            if 'formatter' in mod:
                del sys.modules[mod]

        from core.formatter_v4_fixed import format_sql_v4_fixed

        keyword_case = (
            request.keyword_case
            or (request.options.keyword_case if request.options else None)
            or "upper"
        )

        # 使用 V4 fixed 版本格式化
        formatted = format_sql_v4_fixed(request.sql, keyword_case=keyword_case)

        return {
            "success": True,
            "formatted": formatted,
            "original": request.sql,
            "version": "v4-fixed",
            "formatter_file": "formatter_v4_fixed.py"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "original": request.sql}


@app.post("/api/format-v5")
async def format_sql_v5_sqlglot_endpoint(request: LegacyFormatRequest):
    """v5 格式化 API (基于 sqlglot AST 解析 + V4 列对齐)

    V5 架构：
    1. sqlglot 解析并基础格式化
    2. 将 /* */ 注释改回 -- 格式
    3. V4 列对齐后处理

    兼容旧前端返回结构
    """
    try:
        import sys
        import os

        # 确保 core 目录在路径中
        core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        from core.formatter_v5_sqlglot import format_sql_v5

        # 获取参数
        keyword_case = (
            request.keyword_case
            or (request.options.keyword_case if request.options else None)
            or "upper"
        )

        # 使用 V5 sqlglot 版本格式化
        formatted = format_sql_v5(request.sql, indent=request.indent or 4)

        return {
            "success": True,
            "formatted": formatted,
            "original": request.sql,
            "version": "v5-sqlglot",
            "formatter_file": "formatter_v5_sqlglot.py"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "original": request.sql
        }


# 挂载前端静态文件（单机版）
def _get_frontend_dir():
    """获取前端静态文件目录"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, 'frontend', 'build')
        else:
            return os.path.join(os.path.dirname(sys.executable), 'frontend', 'build')
    else:
        return os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'build')

_frontend_dir = _get_frontend_dir()
if os.path.isdir(_frontend_dir):
    # 挂载静态资源（JS/CSS/图片等），放在所有 API 路由之后
    app.mount("/static", StaticFiles(directory=os.path.join(_frontend_dir, 'static')), name="static")


def _find_free_port(start=8889, end=8900):
    """查找可用端口"""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start  # fallback


if __name__ == "__main__":
    import uvicorn

    is_frozen = getattr(sys, 'frozen', False)
    port = _find_free_port()

    if is_frozen:
        # 单机版：启动后自动打开浏览器，不启用 reload
        import threading
        url = f"http://127.0.0.1:{port}"
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        print(f"Spark SQL 优化工具启动中...")
        print(f"浏览器将自动打开: {url}")
        print(f"如未自动打开，请手动访问上述地址")
        uvicorn.run(app, host="127.0.0.1", port=port)
    else:
        # 开发版：启用热重载
        uvicorn.run("api.main:app", host="127.0.0.1", port=port, reload=True)

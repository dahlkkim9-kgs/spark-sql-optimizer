# -*- coding: utf-8 -*-
"""
Flask 后端服务 - 提供 SQL 格式化 API
"""
import sys
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
from formatter_v3 import format_sql_v3

app = Flask(__name__)
CORS(app)  # 允许跨域请求


@app.route('/api/format', methods=['POST'])
def format_sql():
    """
    SQL 格式化接口

    请求体 JSON:
    {
        "sql": "原始SQL语句",
        "options": {
            "keyword_case": "upper",  // upper 或 lower
            "semicolon_newline": true
        }
    }
    """
    try:
        data = request.get_json()
        sql = data.get('sql', '')
        options = data.get('options', {})

        if not sql:
            return jsonify({'error': 'SQL 语句不能为空'}), 400

        # 调用格式化器
        formatted_sql = format_sql_v3(sql, **options)

        return jsonify({
            'success': True,
            'formatted': formatted_sql,
            'original': sql
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'service': 'spark-sql-optimizer'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

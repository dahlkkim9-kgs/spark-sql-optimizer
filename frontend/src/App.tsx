import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import './App.css';
import { API_URLS } from './config';

interface Issue {
  rule: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  line: number;
  suggestion: string;
}

interface AnalysisResult {
  file?: string;
  original_sql: string;
  optimized_sql: string;
  issues: Issue[];
  issue_count: number;
  high_priority: number;
  medium_priority: number;
  low_priority: number;
}

interface FormatResponse {
  success: boolean;
  formatted: string;
  original: string;
  version?: string;
  formatter_file?: string;
}

function App() {
  const [sql, setSql] = useState('-- 输入你的Spark SQL\nSELECT * FROM table1 JOIN table2');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [formatterVersion, setFormatterVersion] = useState<string>('');

  const handleEditorWillMount = () => {
    // 配置 Monaco Editor
    return {
      // 禁用某些可能出错的功能
      automaticLayout: true,
    };
  };

  const handleEditorMount = (editor: any, monaco: any) => {
    console.log('Monaco Editor 加载成功');
    setEditorError(null);
  };

  const analyzeSQL = async () => {
    setLoading(true);
    setEditorError(null);
    try {
      // 调用后端API格式化SQL
      const response = await fetch(API_URLS.format, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: sql,
          options: {
            keyword_case: 'upper'
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // 调试：打印原始响应
      console.log('API Response:', data);
      console.log('Formatted SQL:', data.formatted);
      console.log('Formatted SQL (repr):', JSON.stringify(data.formatted));

      // 保存版本信息
      if (data.version) {
        setFormatterVersion(`${data.version} (${data.formatter_file || 'formatter_v5_sqlglot.py'})`);
      }

      if (!data.success) {
        throw new Error(data.error || '格式化失败');
      }

      // 转换为前端期望的格式
      setResult({
        original_sql: sql,
        optimized_sql: data.formatted,
        issues: [],
        issue_count: 0,
        high_priority: 0,
        medium_priority: 0,
        low_priority: 0
      });
    } catch (error) {
      console.error('格式化失败:', error);
      alert(`格式化失败: ${error}\n请确保后端服务已启动 (${API_URLS.format})`);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'HIGH': return '#ff4d4f';
      case 'MEDIUM': return '#ffad33';
      case 'LOW': return '#52c41a';
      default: return '#999';
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'HIGH': return '高';
      case 'MEDIUM': return '中';
      case 'LOW': return '低';
      default: return '未知';
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>⚡ Spark SQL 优化工具</h1>
        <p className="subtitle">离线静态分析 · 智能优化建议</p>
      </header>

      <main className="app-main">
        <div className="editor-section">
          <div className="section-header">
            <h2>SQL编辑器</h2>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => setSql('')}>
                清空
              </button>
              <button className="btn btn-primary" onClick={analyzeSQL} disabled={loading}>
                {loading ? '格式化中...' : '格式化SQL'}
              </button>
            </div>
          </div>
          <div className="editor-container">
            {editorError ? (
              <textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                style={{
                  width: '100%',
                  height: '400px',
                  fontFamily: 'monospace',
                  fontSize: '14px',
                  padding: '10px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
                placeholder="在此输入 SQL..."
              />
            ) : (
              <Editor
                height="400px"
                language="sql"
                theme="vs-dark"
                value={sql}
                onChange={(value) => setSql(value || '')}
                beforeMount={handleEditorWillMount}
                onMount={handleEditorMount}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  readOnly: false,
                  automaticLayout: true,
                }}
              />
            )}
          </div>
        </div>

        {result && (
          <div className="result-section">
            <div className="section-header">
              <h2>格式化结果</h2>
              <div className="stats">
                <span className="stat high">高: {result.high_priority}</span>
                <span className="stat medium">中: {result.medium_priority}</span>
                <span className="stat low">低: {result.low_priority}</span>
              </div>
            </div>

            <div className="issues-list">
              {result.issues.length === 0 ? (
                <div className="empty-state">
                  <p>🎉 未发现明显问题！SQL质量良好。</p>
                </div>
              ) : (
                result.issues.map((issue, index) => (
                  <div key={index} className="issue-card" style={{ borderLeftColor: getSeverityColor(issue.severity) }}>
                    <div className="issue-header">
                      <span className="issue-severity" style={{ backgroundColor: getSeverityColor(issue.severity) }}>
                        {getSeverityLabel(issue.severity)}
                      </span>
                      <span className="issue-rule">{issue.rule}</span>
                    </div>
                    <div className="issue-message">{issue.message}</div>
                    {issue.suggestion && (
                      <div className="issue-suggestion">
                        <strong>建议：</strong>{issue.suggestion}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {result.optimized_sql && result.optimized_sql !== result.original_sql && (
              <div className="optimized-section">
                <h3>格式化后的SQL</h3>
                {editorError ? (
                  <textarea
                    value={result.optimized_sql}
                    readOnly
                    style={{
                      width: '100%',
                      height: '200px',
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      padding: '10px',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                      marginBottom: '10px'
                    }}
                  />
                ) : (
                  <Editor
                    height="200px"
                    language="sql"
                    theme="vs-dark"
                    value={result.optimized_sql}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 12,
                      lineNumbers: 'on',
                      readOnly: true,
                      automaticLayout: true,
                    }}
                  />
                )}
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(result.optimized_sql);
                    alert('已复制到剪贴板');
                  }}
                >
                  复制格式化后的SQL
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>
          基于MIT许可协议的开源组件构建 | 离线版本
          {formatterVersion && <span className="version-badge"> | {formatterVersion}</span>}
        </p>
      </footer>
    </div>
  );
}

export default App;

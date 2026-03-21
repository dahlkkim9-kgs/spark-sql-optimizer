// 前端API配置 - 统一管理所有API地址

const API_BASE_URL = 'http://127.0.0.1:8889';

// API端点
const API_ENDPOINTS = {
  format: '/api/format',
  formatV5: '/api/format-v5',  // 新增: v5 sqlglot 格式化器
  analyze: '/analyze',
  health: '/health'
} as const;

// 格式化器版本选项
export const FORMATTER_VERSIONS = {
  V4: 'v4',
  V5: 'v5'
} as const;

export type FormatterVersion = typeof FORMATTER_VERSIONS[keyof typeof FORMATTER_VERSIONS];

// 导出具体URL，方便使用
export const API_URLS = {
  format: `${API_BASE_URL}${API_ENDPOINTS.format}`,
  formatV5: `${API_BASE_URL}${API_ENDPOINTS.formatV5}`,
  analyze: `${API_BASE_URL}${API_ENDPOINTS.analyze}`,
  health: `${API_BASE_URL}${API_ENDPOINTS.health}`
};

// 导出配置对象（如果需要）
export const API_CONFIG = {
  baseUrl: API_BASE_URL,
  endpoints: API_ENDPOINTS
};

// 根据版本获取格式化 URL
export function getFormatUrl(version: FormatterVersion = FORMATTER_VERSIONS.V4): string {
  return version === FORMATTER_VERSIONS.V5 ? API_URLS.formatV5 : API_URLS.format;
}

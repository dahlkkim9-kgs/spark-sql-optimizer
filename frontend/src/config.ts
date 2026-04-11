// 前端API配置 - 统一管理所有API地址

const API_BASE_URL = 'http://127.0.0.1:8889';

// 导出具体URL
export const API_URLS = {
  format: `${API_BASE_URL}/api/format-v5`,
  analyze: `${API_BASE_URL}/analyze`,
  health: `${API_BASE_URL}/health`
};

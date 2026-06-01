/**
 * AI Agent历史记录服务
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:16532';

// 获取token的辅助函数
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ==================== 类型定义 ====================

export interface AgentSession {
  id: string;
  title: string;
  message_count: number;
  last_message_at: string;
  created_at: string;
}

export interface AgentHistory {
  id: string;
  session_id: string;
  question: string;
  intent: Record<string, any>;
  data_summary?: Record<string, any>;
  insights?: string;
  report_markdown?: string;
  report_html?: string;
  extra_metadata?: Record<string, any>;
  created_at: string;
}

export interface SessionListResponse {
  total: number;
  items: AgentSession[];
}

export interface HistoryListResponse {
  total: number;
  items: AgentHistory[];
}

export interface StatisticsResponse {
  total_conversations: number;
  total_sessions: number;
  last_conversation_at: string | null;
}

// ==================== API Service ====================

class AgentHistoryService {
  /**
   * 获取会话列表
   */
  async getSessions(params?: {
    limit?: number;
    offset?: number;
  }): Promise<SessionListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/agent/history/sessions`, {
      params,
      headers: getAuthHeaders(),
    });
    return response.data;
  }

  /**
   * 获取对话历史
   */
  async getConversations(params?: {
    session_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<HistoryListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/agent/history/conversations`, {
      params,
      headers: getAuthHeaders(),
    });
    return response.data;
  }

  /**
   * 获取对话详情
   */
  async getConversationDetail(historyId: string): Promise<AgentHistory> {
    const response = await axios.get(
      `${API_BASE_URL}/api/agent/history/conversations/${historyId}`,
      {
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  }

  /**
   * 搜索对话历史
   */
  async searchConversations(params: {
    keyword: string;
    limit?: number;
  }): Promise<HistoryListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/agent/history/search`, {
      params,
      headers: getAuthHeaders(),
    });
    return response.data;
  }

  /**
   * 删除对话
   */
  async deleteConversation(historyId: string): Promise<{ success: boolean; message: string }> {
    const response = await axios.delete(
      `${API_BASE_URL}/api/agent/history/conversations/${historyId}`,
      {
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  }

  /**
   * 删除会话
   */
  async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await axios.delete(
      `${API_BASE_URL}/api/agent/history/sessions/${sessionId}`,
      {
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  }

  /**
   * 获取统计信息
   */
  async getStatistics(): Promise<StatisticsResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/agent/history/statistics`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  }
}

export default new AgentHistoryService();

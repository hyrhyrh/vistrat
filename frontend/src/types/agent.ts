/**
 * Agent相关TypeScript类型定义
 */

export type MessageRole = 'user' | 'assistant' | 'system';

export type StreamStage = 'intent' | 'query' | 'process' | 'analyze' | 'report' | 'completed' | 'error' | 'tool_call_start' | 'tool_call_result';

// 工具调用信息
export interface ToolCall {
  id: string;
  tool_name: string;
  tool_display_name: string;
  parameters: Record<string, any>;
  result?: Record<string, any>;
  success?: boolean;
  collapsed?: boolean;  // 是否折叠
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  reportMarkdown?: string;  // Markdown报告内容
  reportJson?: any;          // JSON报告数据
  metadata?: Record<string, any>;
  toolCalls?: ToolCall[];    // 工具调用列表
}

export interface StreamMessage {
  stage: StreamStage;
  message?: string;
  content?: string;
  data?: Record<string, any>;
}

export interface ChatHistory {
  messages: Message[];
  lastUpdated: Date;
}

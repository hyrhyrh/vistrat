import React, { useState, useRef, useEffect } from 'react';
import { Modal, Input, Button, Spin, Tabs, Tooltip, message as antMessage, Select, Collapse } from 'antd';
import { RobotOutlined, SendOutlined, LoadingOutlined, HistoryOutlined, MessageOutlined, AudioOutlined, AudioMutedOutlined, BulbOutlined, CopyOutlined, LikeOutlined, ThunderboltOutlined, DownOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import type { Message, StreamMessage as StreamMessageType, ToolCall } from '../../types/agent';
import HistoryPanel from './HistoryPanel';
import type { AgentHistory } from '../../services/agentHistoryService';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';
import './AgentDialog.css';

const { TextArea } = Input;

// LLM模型选项
const LLM_MODELS = [
  { value: 'deepseek', label: 'DeepSeek', icon: '⚡', description: '经济实惠 · 性能均衡', color: '#1890ff' },
  { value: 'claude', label: 'Claude Sonnet 4', icon: '🧠', description: '高精度 · 理解深入', color: '#722ed1' },
  // { value: 'qwen', label: 'Qwen3-Max', icon: '🚀', description: '最新模型 · 响应迅速', color: '#13c2c2' },
];

// 代码块组件 - 支持复制功能
const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';

  const handleCopy = async () => {
    // 去除开头和结尾的空白字符（包括换行符）
    const code = String(children).trim();
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      antMessage.error('复制失败');
    }
  };

  if (inline) {
    return <code className={className} {...props}>{children}</code>;
  }

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-block-language">{language || 'text'}</span>
        <Button
          type="text"
          size="small"
          icon={<CopyOutlined />}
          onClick={handleCopy}
          className="code-copy-button"
        >
          {copied ? '已复制' : '复制'}
        </Button>
      </div>
      <pre className={className}>
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    </div>
  );
};

// 工具调用展示组件
const ToolCallDisplay: React.FC<{ toolCall: ToolCall; onChange?: (collapsed: boolean) => void }> = ({ toolCall, onChange }) => {
  const [collapsed, setCollapsed] = useState(toolCall.collapsed ?? true);

  const toggleCollapse = () => {
    const newCollapsed = !collapsed;
    setCollapsed(newCollapsed);
    onChange?.(newCollapsed);
  };

  return (
    <div className="tool-call-container">
      <div className="tool-call-header" onClick={toggleCollapse}>
        <DownOutlined className={`tool-call-icon ${!collapsed ? 'expanded' : ''}`} />
        <span className="tool-call-title">{toolCall.tool_display_name}</span>
        {toolCall.success !== undefined && (
          <span className={`tool-call-status ${toolCall.success ? 'success' : 'error'}`}>
            {toolCall.success ? '✓ 成功' : '✗ 失败'}
          </span>
        )}
      </div>
      {!collapsed && (
        <div className="tool-call-content">
          <div className="tool-call-section">
            <div className="tool-call-section-title">查询参数</div>
            <pre className="tool-call-code">
              {JSON.stringify(toolCall.parameters, null, 2)}
            </pre>
          </div>
          {toolCall.result && (
            <div className="tool-call-section">
              <div className="tool-call-section-title">
                查询结果
                {toolCall.result.hits?.total && (
                  <span className="tool-call-result-count">
                    (找到 {typeof toolCall.result.hits.total === 'object' ? toolCall.result.hits.total.value : toolCall.result.hits.total} 条记录)
                  </span>
                )}
              </div>
              <pre className="tool-call-code">
                {JSON.stringify(toolCall.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// 智能建议列表
const SMART_SUGGESTIONS = [
  "今天有多少告警?",
  "最近一周的告警趋势如何?",
  "未戴安全帽的告警有多少?",
  "哪个区域的告警最多?",
  "告警处理效率如何?",
  "高危告警有哪些?",
  "本周告警比上周增加了多少?"
];

// ✅ 方案3：阶段化友好提示消息（用户可理解的阶段说明）
// 注意：'analyze'阶段用于流式输出LLM内容，不是进度提示，所以不在这里定义
const STAGE_MESSAGES: Record<string, string> = {
  'intent': '🤔 理解您的问题...',
  'query': '🔍 正在查询相关数据...',
  'process': '⚙️ 正在处理查询结果...',
  'report': '📝 正在生成报告...'
};

interface AgentDialogProps {
  visible: boolean;
  onClose: () => void;
}

const AgentDialog: React.FC<AgentDialogProps> = ({ visible, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: '您好!我是AI分析助手,很高兴为您服务。\n\n我可以帮您分析以下内容:\n- 告警数据统计和趋势\n- 安全隐患分析\n- 设备运行状态\n- 区域风险评估\n\n点击下方建议或输入您的问题开始对话吧!',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentProgress, setCurrentProgress] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [randomSuggestions, setRandomSuggestions] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('deepseek'); // 默认使用DeepSeek
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 提取最近的对话历史（最多5轮，10条消息）
  const getRecentHistory = () => {
    const MAX_HISTORY = 10; // 最多10条消息（5轮对话）
    const recentMessages = messages
      .filter(msg => msg.role !== 'system' && msg.id !== '0') // 排除系统消息和欢迎消息
      .slice(-MAX_HISTORY) // 只取最近的N条
      .map(msg => ({
        role: msg.role,
        content: msg.content
      }));
    return recentMessages;
  };

  // 录音Hook(百度AI语音识别)
  const {
    transcript,
    isRecording,
    isProcessing,
    error: speechError,
    startRecording,
    stopRecording,
    resetTranscript,
  } = useAudioRecorder({
    onTranscriptReceived: (text) => {
      setInputValue(text);
    },
    onError: (error) => {
      antMessage.error(error);
    },
  });

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentProgress]);

  // 初始化随机建议
  useEffect(() => {
    if (visible) {
      const shuffled = [...SMART_SUGGESTIONS].sort(() => 0.5 - Math.random());
      setRandomSuggestions(shuffled.slice(0, 4));
      setShowSuggestions(messages.length <= 1);
    }
  }, [visible, messages.length]);

  // ✅ 方案3：组件加载时从SessionStorage恢复历史记录
  useEffect(() => {
    if (visible) {
      const savedHistory = sessionStorage.getItem('agent_history');
      if (savedHistory) {
        try {
          const historyData = JSON.parse(savedHistory);
          if (historyData && historyData.length > 0) {
            const restoredMessages: Message[] = historyData.map((msg: any, index: number) => ({
              id: 'restored-' + index,
              role: msg.role,
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              toolCalls: msg.toolCalls
            }));
            // 只在首次打开对话框且只有欢迎消息时恢复
            setMessages(prev => {
              // 只有当前只有欢迎消息(id='0')时才恢复
              if (prev.length === 1 && prev[0].id === '0') {
                return [...prev, ...restoredMessages];
              }
              return prev;
            });
          }
        } catch (error) {
          console.error('恢复历史记录失败:', error);
        }
      }
    }
  }, [visible]); // 只依赖visible，避免重复恢复

  // ✅ 方案3：保存对话历史到SessionStorage（本地存储，刷新保留）
  useEffect(() => {
    const saveLocalHistory = () => {
      const historyData = messages
        .filter(msg => msg.role !== 'system' && msg.id !== '0' && !msg.id.startsWith('restored-')) // 排除系统消息、欢迎消息和已恢复的消息
        .slice(-50) // 只保留最近50条
        .map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp.toISOString(),
          toolCalls: msg.toolCalls
        }));
      sessionStorage.setItem('agent_history', JSON.stringify(historyData));
    };

    // 只有当有新消息时才保存
    if (messages.length > 1) {
      saveLocalHistory();
    }
  }, [messages]);

  // 复制消息内容
  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      antMessage.success('内容已复制到剪贴板');
    } catch (error) {
      antMessage.error('复制失败');
    }
  };

  // 选择智能建议 - 直接发送
  const handleSelectSuggestion = (suggestion: string) => {
    setShowSuggestions(false);

    // 生成消息ID
    const assistantMessageId = (Date.now() + 1).toString();

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: suggestion,
      timestamp: new Date()
    };

    // ✅ 立即创建空的assistant消息，显示loading状态
    const initialAssistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage, initialAssistantMessage]);
    setIsStreaming(true);
    setCurrentProgress('');

    // 提取历史对话（在添加当前消息前）
    const history = getRecentHistory();

    // 创建SSE连接，携带对话历史
    let url = `/api/agent/chat?question=${encodeURIComponent(suggestion)}&model=${selectedModel}`;
    if (history.length > 0) {
      url += `&history=${encodeURIComponent(JSON.stringify(history))}`;
    }
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    let currentAssistantMessage = '';
    // assistantMessageId 已在上面定义
    let hasCreatedAssistantMessage = true; // ✅ 已经创建了初始assistant消息
    let currentToolCalls: ToolCall[] = [];  // 跟踪工具调用

    eventSource.onmessage = (event) => {
      try {
        const data: StreamMessageType = JSON.parse(event.data);

        switch (data.stage) {
          case 'intent':
          case 'query':
          case 'process':
          case 'report':
            // ✅ 使用友好的阶段提示消息（用户可理解）
            setCurrentProgress(STAGE_MESSAGES[data.stage] || data.message || '');
            break;

          case 'tool_call_start':
            // 工具调用开始
            if (data.data) {
              const toolCall: ToolCall = {
                id: Date.now().toString() + Math.random(),
                tool_name: data.data.tool_name,
                tool_display_name: data.data.tool_display_name,
                parameters: data.data.parameters,
                collapsed: true
              };
              currentToolCalls.push(toolCall);

              // 如果还没有创建assistant消息,先创建
              if (!hasCreatedAssistantMessage) {
                setMessages(prev => [...prev, {
                  id: assistantMessageId,
                  role: 'assistant',
                  content: '',
                  timestamp: new Date(),
                  toolCalls: [...currentToolCalls]
                }]);
                hasCreatedAssistantMessage = true;
              } else {
                // 更新工具调用列表
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.toolCalls = [...currentToolCalls];
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'tool_call_result':
            // 工具调用结果
            if (data.data && currentToolCalls.length > 0) {
              const lastToolCall = currentToolCalls[currentToolCalls.length - 1];
              if (lastToolCall.tool_name === data.data.tool_name) {
                lastToolCall.result = data.data.result;
                lastToolCall.success = data.data.success;

                // 更新工具调用结果
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.toolCalls = [...currentToolCalls];
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'analyze':
            // 流式追加AI分析
            if (data.content) {
              // 🔥 紧急修复：过滤掉工具调用标记，这些不应该显示给用户
              if (data.content.includes('__TOOL_CALL_') ||
                  data.content.includes('tool__calls__') ||
                  data.content.includes('tool__call__')) {
                // 跳过包含工具调用标记的内容
                console.warn('过滤掉工具调用标记:', data.content.substring(0, 100));
                break;
              }

              currentAssistantMessage += data.content;

              if (!hasCreatedAssistantMessage) {
                // 第一次创建assistant消息
                setMessages(prev => [...prev, {
                  id: assistantMessageId,
                  role: 'assistant',
                  content: currentAssistantMessage,
                  timestamp: new Date()
                }]);
                hasCreatedAssistantMessage = true;
              } else {
                // 更新assistant消息内容
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.content = currentAssistantMessage;
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'completed':
            // 分析完成
            setCurrentProgress('');
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];

              // 如果还没有创建assistant消息(如不相关问题的情况)
              if (!hasCreatedAssistantMessage && data.data?.report_markdown) {
                newMessages.push({
                  id: assistantMessageId,
                  role: 'assistant',
                  content: data.data.report_markdown,
                  timestamp: new Date(),
                  reportMarkdown: data.data.report_markdown,
                  reportJson: data.data.report_json,
                  metadata: data.data.metadata
                });
              } else if (lastMsg && lastMsg.id === assistantMessageId && data.data) {
                // 更新已存在的assistant消息
                lastMsg.reportMarkdown = data.data.report_markdown;
                lastMsg.reportJson = data.data.report_json;
                lastMsg.metadata = data.data.metadata;
              }
              return newMessages;
            });
            eventSource.close();
            setIsStreaming(false);
            break;

          case 'error':
            setCurrentProgress('');
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'system',
              content: data.message || '分析失败',
              timestamp: new Date()
            }]);
            eventSource.close();
            setIsStreaming(false);
            break;
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE连接错误');
      eventSource.close();
      setIsStreaming(false);
      setCurrentProgress('');
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'system',
        content: '连接中断,请重试',
        timestamp: new Date()
      }]);
    };
  };

  // 发送消息
  const handleSendMessage = async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    // 生成消息ID
    const assistantMessageId = (Date.now() + 1).toString();

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date()
    };

    // ✅ 立即创建空的assistant消息，显示loading状态
    const initialAssistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage, initialAssistantMessage]);
    setInputValue('');
    resetTranscript(); // 清空语音识别结果
    setShowSuggestions(false); // 隐藏建议
    setIsStreaming(true);
    setCurrentProgress('');

    // 提取历史对话（在添加当前消息前）
    const history = getRecentHistory();

    // 创建SSE连接，携带对话历史
    let url = `/api/agent/chat?question=${encodeURIComponent(text)}&model=${selectedModel}`;
    if (history.length > 0) {
      url += `&history=${encodeURIComponent(JSON.stringify(history))}`;
    }
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    let currentAssistantMessage = '';
    // assistantMessageId 已在上面定义
    let hasCreatedAssistantMessage = true; // ✅ 已经创建了初始assistant消息
    let currentToolCalls: ToolCall[] = [];  // 跟踪工具调用

    eventSource.onmessage = (event) => {
      try {
        const data: StreamMessageType = JSON.parse(event.data);

        switch (data.stage) {
          case 'intent':
          case 'query':
          case 'process':
          case 'report':
            // ✅ 使用友好的阶段提示消息（用户可理解）
            setCurrentProgress(STAGE_MESSAGES[data.stage] || data.message || '');
            break;

          case 'tool_call_start':
            // 工具调用开始
            if (data.data) {
              const toolCall: ToolCall = {
                id: Date.now().toString() + Math.random(),
                tool_name: data.data.tool_name,
                tool_display_name: data.data.tool_display_name,
                parameters: data.data.parameters,
                collapsed: true
              };
              currentToolCalls.push(toolCall);

              // 如果还没有创建assistant消息,先创建
              if (!hasCreatedAssistantMessage) {
                setMessages(prev => [...prev, {
                  id: assistantMessageId,
                  role: 'assistant',
                  content: '',
                  timestamp: new Date(),
                  toolCalls: [...currentToolCalls]
                }]);
                hasCreatedAssistantMessage = true;
              } else {
                // 更新工具调用列表
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.toolCalls = [...currentToolCalls];
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'tool_call_result':
            // 工具调用结果
            if (data.data && currentToolCalls.length > 0) {
              const lastToolCall = currentToolCalls[currentToolCalls.length - 1];
              if (lastToolCall.tool_name === data.data.tool_name) {
                lastToolCall.result = data.data.result;
                lastToolCall.success = data.data.success;

                // 更新工具调用结果
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.toolCalls = [...currentToolCalls];
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'analyze':
            // 流式追加AI分析
            if (data.content) {
              // 🔥 紧急修复：过滤掉工具调用标记，这些不应该显示给用户
              if (data.content.includes('__TOOL_CALL_') ||
                  data.content.includes('tool__calls__') ||
                  data.content.includes('tool__call__')) {
                // 跳过包含工具调用标记的内容
                console.warn('过滤掉工具调用标记:', data.content.substring(0, 100));
                break;
              }

              currentAssistantMessage += data.content;

              if (!hasCreatedAssistantMessage) {
                // 第一次创建assistant消息
                setMessages(prev => [...prev, {
                  id: assistantMessageId,
                  role: 'assistant',
                  content: currentAssistantMessage,
                  timestamp: new Date()
                }]);
                hasCreatedAssistantMessage = true;
              } else {
                // 更新assistant消息内容
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.id === assistantMessageId) {
                    lastMsg.content = currentAssistantMessage;
                  }
                  return newMessages;
                });
              }
            }
            break;

          case 'completed':
            // 分析完成
            setCurrentProgress('');
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];

              // 如果还没有创建assistant消息(如不相关问题的情况)
              if (!hasCreatedAssistantMessage && data.data?.report_markdown) {
                newMessages.push({
                  id: assistantMessageId,
                  role: 'assistant',
                  content: data.data.report_markdown,
                  timestamp: new Date(),
                  reportMarkdown: data.data.report_markdown,
                  reportJson: data.data.report_json,
                  metadata: data.data.metadata
                });
              } else if (lastMsg && lastMsg.id === assistantMessageId && data.data) {
                // 更新已存在的assistant消息
                lastMsg.reportMarkdown = data.data.report_markdown;
                lastMsg.reportJson = data.data.report_json;
                lastMsg.metadata = data.data.metadata;
              }
              return newMessages;
            });
            eventSource.close();
            setIsStreaming(false);
            break;

          case 'error':
            setCurrentProgress('');
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'system',
              content: data.message || '分析失败',
              timestamp: new Date()
            }]);
            eventSource.close();
            setIsStreaming(false);
            break;
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE连接错误');
      eventSource.close();
      setIsStreaming(false);
      setCurrentProgress('');
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'system',
        content: '连接中断,请重试',
        timestamp: new Date()
      }]);
    };
  };

  // 清理SSE连接
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // 处理Enter键发送
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ✅ 方案3：处理粘贴时的多余换行符
  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text');
    // 清理多余的换行符（连续3个以上的换行符替换为2个）
    const cleanedText = pastedText.replace(/\n{3,}/g, '\n\n');
    const cursorPos = e.currentTarget.selectionStart;
    const newValue =
      inputValue.substring(0, cursorPos) +
      cleanedText +
      inputValue.substring(e.currentTarget.selectionEnd);
    setInputValue(newValue);
  };

  // 处理选择历史记录
  const handleSelectHistory = (history: AgentHistory) => {
    // 将历史记录加载到对话中
    const historyMessages: Message[] = [
      {
        id: 'history-user-' + history.id,
        role: 'user',
        content: history.question,
        timestamp: new Date(history.created_at)
      },
      {
        id: 'history-assistant-' + history.id,
        role: 'assistant',
        content: history.insights || '暂无分析结果',
        timestamp: new Date(history.created_at),
        reportMarkdown: history.report_markdown,
        reportJson: history.data_summary,
        metadata: history.extra_metadata
      }
    ];

    setMessages(prev => [...prev, ...historyMessages]);
    setActiveTab('chat');
  };

  // 处理选择会话
  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  // 处理语音输入按钮点击
  const handleVoiceInput = async () => {
    if (isRecording) {
      // 停止录音
      await stopRecording();
      antMessage.info('正在识别,请稍候...');
    } else {
      // 开始录音
      await startRecording();
      antMessage.success('开始录音,请说话... 完成后再次点击按钮');
    }
  };

  return (
    <Modal
      title={
        <div className="agent-dialog-header">
          <RobotOutlined className="agent-dialog-icon" />
          <span>AI分析助手</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width="75%"
      style={{ top: '5%' }}
      footer={null}
      styles={{
        body: {
          height: '80vh',
          padding: 0,
          display: 'flex',
          flexDirection: 'column'
        }
      }}
      destroyOnHidden
    >
      {/* 三段式布局容器 */}
      <div className="chat-dialog-wrapper">
        {/* 中间区域：Tabs + 可滚动内容 */}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          className="chat-tabs"
          items={[
            {
              key: 'chat',
              label: (
                <span>
                  <MessageOutlined />
                  对话
                </span>
              ),
              children: (
                <div className="messages-container">
          {/* 智能建议面板 */}
          {showSuggestions && randomSuggestions.length > 0 && (
            <div className="smart-suggestions-panel">
              <div className="suggestions-header">
                <BulbOutlined className="bulb-icon" />
                <span className="suggestions-title">智能建议</span>
              </div>
              <div className="suggestions-grid">
                {randomSuggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="suggestion-chip"
                    onClick={() => handleSelectSuggestion(suggestion)}
                  >
                    <span className="suggestion-text">{suggestion}</span>
                    <SendOutlined className="suggestion-send-icon" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-item message-${message.role}`}
            >
              <div className="message-avatar">
                {message.role === 'assistant' ? (
                  <div className={`ai-avatar ${isStreaming ? 'pulse' : ''}`}>
                    <RobotOutlined />
                  </div>
                ) : message.role === 'user' ? (
                  <div className="user-avatar">
                    <span>👤</span>
                  </div>
                ) : (
                  <div className="system-avatar">
                    <span>ℹ️</span>
                  </div>
                )}
              </div>
              <div className="message-content">
                {/* 工具调用展示 */}
                {message.toolCalls && message.toolCalls.length > 0 && (
                  <div className="tool-calls-list">
                    {message.toolCalls.map((toolCall) => (
                      <ToolCallDisplay
                        key={toolCall.id}
                        toolCall={toolCall}
                        onChange={(collapsed) => {
                          // 更新折叠状态
                          setMessages(prev => {
                            const newMessages = [...prev];
                            const msg = newMessages.find(m => m.id === message.id);
                            if (msg && msg.toolCalls) {
                              const tc = msg.toolCalls.find(t => t.id === toolCall.id);
                              if (tc) {
                                tc.collapsed = collapsed;
                              }
                            }
                            return newMessages;
                          });
                        }}
                      />
                    ))}
                  </div>
                )}
                <div className="message-text">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      code: CodeBlock
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  {/* 流式输出加载指示器 */}
                  {message.role === 'assistant' && isStreaming && message.id === messages[messages.length - 1]?.id && (
                    <span className="streaming-indicator">
                      <LoadingOutlined spin style={{ marginLeft: '8px', color: '#667eea' }} />
                    </span>
                  )}
                </div>
                {/* 消息操作按钮 */}
                {message.role === 'assistant' && message.id !== '0' && (
                  <div className="message-actions">
                    <Tooltip title="复制内容">
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => handleCopyMessage(message.content)}
                      />
                    </Tooltip>
                    <Tooltip title="有帮助">
                      <Button
                        type="text"
                        size="small"
                        icon={<LikeOutlined />}
                        onClick={() => antMessage.success('感谢您的反馈!')}
                      />
                    </Tooltip>
                  </div>
                )}
                {message.metadata && (
                  <div className="message-metadata">
                    <span className="metadata-time">
                      耗时: {message.metadata.elapsed_time_seconds?.toFixed(2)}秒
                    </span>
                    <span className="metadata-count">
                      数据量: {message.metadata.data_count}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* 进度提示 */}
          {currentProgress && (
            <div className="message-item message-system">
              <div className="message-avatar">
                <div className="loading-avatar">
                  <LoadingOutlined spin />
                </div>
              </div>
              <div className="message-content">
                <div className="message-text progress-text">
                  {currentProgress}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
                </div>
              ),
            },
          {
            key: 'history',
            label: (
              <span>
                <HistoryOutlined />
                历史记录
              </span>
            ),
            children: (
              <HistoryPanel
                onSelectHistory={handleSelectHistory}
                onSelectSession={handleSelectSession}
              />
            ),
          },
        ]}
        />

        {/* 底部固定区域：仅在chat标签时显示 */}
        {activeTab === 'chat' && (
          <div className="chat-footer">
            {/* AI模型选择区域 */}
            <div className="model-selector-row">
              <ThunderboltOutlined style={{ fontSize: '16px', color: '#1890ff' }} />
              <span style={{ fontSize: '14px', color: '#666', fontWeight: 500 }}>AI模型:</span>
              <Select
                value={selectedModel}
                onChange={setSelectedModel}
                style={{ width: 280 }}
                disabled={isStreaming}
                optionLabelProp="label"
                options={LLM_MODELS.map(model => ({
                  value: model.value,
                  label: `${model.icon} ${model.label}`,
                  title: model.description
                }))}
              />
              <span style={{ fontSize: '12px', color: '#999', marginLeft: 'auto' }}>
                {LLM_MODELS.find(m => m.value === selectedModel)?.description}
              </span>
            </div>

            {/* 输入操作区域 */}
            <div className="input-action-row">
              <div className="input-wrapper">
                <TextArea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  onPaste={handlePaste}
                  placeholder="输入问题,发送 [Enter] / 换行 [Shift+Enter]"
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  disabled={isStreaming}
                  className="input-textarea"
                />
              </div>
              <Tooltip title={
                isRecording
                  ? '停止录音并识别'
                  : isProcessing
                  ? '正在识别...'
                  : '开始语音输入(百度AI识别)'
              }>
                <Button
                  icon={
                    isProcessing
                      ? <LoadingOutlined spin />
                      : isRecording
                      ? <AudioMutedOutlined />
                      : <AudioOutlined />
                  }
                  onClick={handleVoiceInput}
                  disabled={isStreaming || isProcessing}
                  className={`voice-button ${isRecording ? 'listening' : ''}`}
                  danger={isRecording}
                  loading={isProcessing}
                />
              </Tooltip>
              <Button
                type="primary"
                icon={isStreaming ? <LoadingOutlined spin /> : <SendOutlined />}
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isStreaming}
                className="send-button"
              >
                {isStreaming ? '分析中...' : '发送'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default AgentDialog;

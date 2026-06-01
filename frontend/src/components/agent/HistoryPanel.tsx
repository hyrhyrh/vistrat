/**
 * AI Agent历史记录面板组件
 *
 * 功能:
 * - 显示会话列表
 * - 显示对话历史
 * - 搜索功能
 * - 删除操作
 * - 点击历史记录重新加载对话
 */
import React, { useState, useEffect } from 'react';
import {
  List,
  Input,
  Button,
  Empty,
  Spin,
  message,
  Popconfirm,
  Space,
  Typography,
  Tag,
  Tooltip,
  Divider,
} from 'antd';
import {
  HistoryOutlined,
  DeleteOutlined,
  SearchOutlined,
  MessageOutlined,
  ClockCircleOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import agentHistoryService, {
  AgentSession,
  AgentHistory,
} from '../../services/agentHistoryService';
import './HistoryPanel.css';

const { Text, Paragraph } = Typography;
const { Search } = Input;

interface HistoryPanelProps {
  onSelectHistory: (history: AgentHistory) => void;
  onSelectSession: (sessionId: string) => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  onSelectHistory,
  onSelectSession,
}) => {
  // 状态管理
  const [view, setView] = useState<'sessions' | 'conversations'>('sessions');
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [conversations, setConversations] = useState<AgentHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // 加载会话列表
  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await agentHistoryService.getSessions({ limit: 50 });
      setSessions(response.items);
    } catch (error: any) {
      message.error(`加载会话列表失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 加载对话历史
  const loadConversations = async (sessionId?: string) => {
    setLoading(true);
    try {
      const response = await agentHistoryService.getConversations({
        session_id: sessionId,
        limit: 100,
      });
      setConversations(response.items);
    } catch (error: any) {
      message.error(`加载对话历史失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 搜索对话
  const handleSearch = async (keyword: string) => {
    if (!keyword.trim()) {
      loadConversations(selectedSessionId || undefined);
      return;
    }

    setLoading(true);
    try {
      const response = await agentHistoryService.searchConversations({
        keyword,
        limit: 50,
      });
      setConversations(response.items);
      setView('conversations');
    } catch (error: any) {
      message.error(`搜索失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 删除会话
  const handleDeleteSession = async (sessionId: string) => {
    try {
      await agentHistoryService.deleteSession(sessionId);
      message.success('会话已删除');
      loadSessions();
    } catch (error: any) {
      message.error(`删除失败: ${error.message}`);
    }
  };

  // 删除对话
  const handleDeleteConversation = async (historyId: string) => {
    try {
      await agentHistoryService.deleteConversation(historyId);
      message.success('对话已删除');
      loadConversations(selectedSessionId || undefined);
    } catch (error: any) {
      message.error(`删除失败: ${error.message}`);
    }
  };

  // 选择会话
  const handleSelectSession = (session: AgentSession) => {
    setSelectedSessionId(session.id);
    setView('conversations');
    loadConversations(session.id);
    onSelectSession(session.id);
  };

  // 选择对话
  const handleSelectConversation = (history: AgentHistory) => {
    onSelectHistory(history);
  };

  // 返回会话列表
  const handleBackToSessions = () => {
    setView('sessions');
    setSelectedSessionId(null);
    setSearchKeyword('');
  };

  // 初始加载
  useEffect(() => {
    loadSessions();
  }, []);

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString();
  };

  // 渲染会话列表
  const renderSessions = () => (
    <div className="history-panel-content">
      <div className="history-panel-header">
        <Space>
          <FolderOpenOutlined style={{ fontSize: 18, color: '#1890ff' }} />
          <Text strong style={{ fontSize: 16 }}>对话会话</Text>
        </Space>
        <Tag color="blue">{sessions.length} 个会话</Tag>
      </div>

      <Spin spinning={loading}>
        {sessions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无会话记录"
            style={{ marginTop: 60 }}
          />
        ) : (
          <List
            className="history-list"
            dataSource={sessions}
            renderItem={(session) => (
              <List.Item
                key={session.id}
                className="history-list-item"
                onClick={() => handleSelectSession(session)}
                actions={[
                  <Popconfirm
                    title="确定删除此会话及所有对话?"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDeleteSession(session.id);
                    }}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={<MessageOutlined style={{ fontSize: 20, color: '#52c41a' }} />}
                  title={
                    <Text strong ellipsis style={{ maxWidth: 200 }}>
                      {session.title || '未命名会话'}
                    </Text>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {session.message_count} 条消息
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        <ClockCircleOutlined /> {formatTime(session.last_message_at || session.created_at)}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Spin>
    </div>
  );

  // 渲染对话历史
  const renderConversations = () => (
    <div className="history-panel-content">
      <div className="history-panel-header">
        <Space>
          <Button
            type="text"
            icon={<FolderOpenOutlined />}
            onClick={handleBackToSessions}
          >
            返回会话
          </Button>
        </Space>
      </div>

      <div style={{ padding: '0 16px 12px' }}>
        <Search
          placeholder="搜索对话..."
          allowClear
          enterButton={<SearchOutlined />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          onSearch={handleSearch}
        />
      </div>

      <Spin spinning={loading}>
        {conversations.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无对话记录"
            style={{ marginTop: 60 }}
          />
        ) : (
          <List
            className="history-list"
            dataSource={conversations}
            renderItem={(history) => (
              <List.Item
                key={history.id}
                className="history-list-item conversation-item"
                onClick={() => handleSelectConversation(history)}
                actions={[
                  <Popconfirm
                    title="确定删除此对话?"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDeleteConversation(history.id);
                    }}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={<HistoryOutlined style={{ fontSize: 18, color: '#1890ff' }} />}
                  title={
                    <Tooltip title={history.question}>
                      <Text ellipsis style={{ maxWidth: 220 }}>
                        {history.question}
                      </Text>
                    </Tooltip>
                  }
                  description={
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      {history.data_summary && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {history.data_summary.total_count || 0} 条数据
                        </Text>
                      )}
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        <ClockCircleOutlined /> {formatTime(history.created_at)}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Spin>
    </div>
  );

  return (
    <div className="history-panel">
      {view === 'sessions' ? renderSessions() : renderConversations()}
    </div>
  );
};

export default HistoryPanel;

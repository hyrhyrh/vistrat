import React from 'react';
import { RobotOutlined } from '@ant-design/icons';
import './AgentButton.css';

interface AgentButtonProps {
  onClick: () => void;
}

const AgentButton: React.FC<AgentButtonProps> = ({ onClick }) => {
  return (
    <div className="agent-button-container" onClick={onClick}>
      <div className="agent-icon">
        <RobotOutlined />
      </div>
      <div className="agent-text">AI分析助手</div>
    </div>
  );
};

export default AgentButton;

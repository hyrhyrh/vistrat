import React, { useMemo, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { List as AntList, Badge } from 'antd';

/**
 * 告警数据接口
 */
export interface Alert {
  id: string;
  video_name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  algorithm_name: string;
  template_name?: string;
  confidence: number;
  created_at: string;
  image_url?: string;
  frame_index: number;
  video_time: string;
}

interface VirtualAlertListProps {
  alerts: Alert[];
  onAlertClick: (alert: Alert) => void;
  formatTime: (timestamp: string | number) => string;
  height?: number;
  itemHeight?: number;
}

/**
 * 虚拟滚动告警列表组件
 * 使用react-window实现大数据量列表的高性能渲染
 */
const VirtualAlertList: React.FC<VirtualAlertListProps> = ({
  alerts,
  onAlertClick,
  formatTime,
  height = 600,
  itemHeight = 120,
}) => {
  // 单个告警项渲染函数
  const AlertItem = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const alert = alerts[index];

    return (
      <AntList.Item
        style={style}
        className={`alertItem priority${alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)} ${
          alert.description?.includes('安全帽') ? 'safetyHelmet' : ''
        } ${alert.description?.includes('反光衣') ? 'reflectiveVest' : ''}`}
        onClick={() => onAlertClick(alert)}
      >
        <div className="alertItemContent">
          {/* 左侧小图展示 */}
          <div className="alertThumbnail">
            {alert.image_url ? (
              <img
                src={alert.image_url}
                alt="告警截图"
                className="alertThumbImg"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  const placeholder = e.currentTarget.nextElementSibling as HTMLElement;
                  if (placeholder) placeholder.style.display = 'flex';
                }}
              />
            ) : null}
            <div
              className="alertThumbPlaceholder"
              style={{ display: alert.image_url ? 'none' : 'flex' }}
            >
              <div className="alertType">
                {alert.description?.includes('安全帽') && (
                  <span className="typeIcon safety">⛑️</span>
                )}
                {alert.description?.includes('反光衣') && (
                  <span className="typeIcon vest">🦸</span>
                )}
                {!alert.description?.includes('安全帽') &&
                  !alert.description?.includes('反光衣') && (
                    <span className="typeIcon general">⚠️</span>
                  )}
              </div>
            </div>
          </div>

          {/* 右侧文字内容 */}
          <div className="alertMain">
            <div className="alertInfo">
              <div className="alertTitle">
                {alert.template_name || alert.algorithm_name || '智能检测'}
              </div>
              <div className="alertDetails">
                <span className="location">{alert.video_name}</span>
                <span className="confidence">
                  置信度 {(alert.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="alertTime">{formatTime(alert.created_at)}</div>
            </div>
          </div>
          <div className="alertIndex">#{index + 1}</div>
        </div>
      </AntList.Item>
    );
  }, [alerts, onAlertClick, formatTime]);

  // 当告警数量少于10条时，不使用虚拟滚动（避免过度优化）
  const shouldUseVirtualScroll = alerts.length > 10;

  if (!shouldUseVirtualScroll) {
    // 少量数据直接渲染
    return (
      <AntList
        className="alertsList"
        dataSource={alerts}
        renderItem={(alert, index) => (
          <AntList.Item
            className={`alertItem priority${alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)} ${
              alert.description?.includes('安全帽') ? 'safetyHelmet' : ''
            } ${alert.description?.includes('反光衣') ? 'reflectiveVest' : ''}`}
            onClick={() => onAlertClick(alert)}
            style={{ cursor: 'pointer' }}
          >
            <div className="alertItemContent">
              <div className="alertThumbnail">
                {alert.image_url ? (
                  <img
                    src={alert.image_url}
                    alt="告警截图"
                    className="alertThumbImg"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      const placeholder = e.currentTarget.nextElementSibling as HTMLElement;
                      if (placeholder) placeholder.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="alertThumbPlaceholder"
                  style={{ display: alert.image_url ? 'none' : 'flex' }}
                >
                  <div className="alertType">
                    {alert.description?.includes('安全帽') && (
                      <span className="typeIcon safety">⛑️</span>
                    )}
                    {alert.description?.includes('反光衣') && (
                      <span className="typeIcon vest">🦸</span>
                    )}
                    {!alert.description?.includes('安全帽') &&
                      !alert.description?.includes('反光衣') && (
                        <span className="typeIcon general">⚠️</span>
                      )}
                  </div>
                </div>
              </div>

              <div className="alertMain">
                <div className="alertInfo">
                  <div className="alertTitle">
                    {alert.template_name || alert.algorithm_name || '智能检测'}
                  </div>
                  <div className="alertDetails">
                    <span className="location">{alert.video_name}</span>
                    <span className="confidence">
                      置信度 {(alert.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="alertTime">{formatTime(alert.created_at)}</div>
                </div>
              </div>
              <div className="alertIndex">#{index + 1}</div>
            </div>
          </AntList.Item>
        )}
      />
    );
  }

  // 大数据量使用虚拟滚动
  return (
    <List
      className="alertsList"
      height={height}
      itemCount={alerts.length}
      itemSize={itemHeight}
      width="100%"
      overscanCount={3}
    >
      {AlertItem}
    </List>
  );
};

export default VirtualAlertList;

import React, { useState, useEffect } from 'react';
import { Spin, Alert, Button } from 'antd';
import { ReloadOutlined, PauseCircleOutlined } from '@ant-design/icons';
import './MJPEGStatusOverlay.css';

interface MJPEGStatusOverlayProps {
  status: 'loading' | 'error' | 'paused' | 'hidden';
  connectionState?: string;
  retryCount?: number;
  maxRetries?: number;
  error?: string;
  lastErrorTime?: number;
  autoRetryEnabled?: boolean;
  onRetry?: () => void;
  onToggleAutoRetry?: (enabled: boolean) => void;
  width?: string | number;
  height?: string | number;
}

export const MJPEGStatusOverlay: React.FC<MJPEGStatusOverlayProps> = ({
  status,
  connectionState = 'connecting',
  retryCount = 0,
  maxRetries = 3,
  error,
  lastErrorTime,
  autoRetryEnabled = true,
  onRetry,
  onToggleAutoRetry,
  width = '100%',
  height = '100%'
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 监听全屏状态变化
  useEffect(() => {
    const checkFullscreen = () => {
      const fullscreen = !!(document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement);
      
      console.log('[MJPEGStatusOverlay] 全屏状态变化:', {
        previousState: isFullscreen,
        newState: fullscreen,
        fullscreenElement: document.fullscreenElement?.tagName || 'null'
      });
      
      setIsFullscreen(fullscreen);
    };

    // 监听全屏状态变化事件
    document.addEventListener('fullscreenchange', checkFullscreen);
    document.addEventListener('webkitfullscreenchange', checkFullscreen);
    document.addEventListener('mozfullscreenchange', checkFullscreen);
    document.addEventListener('MSFullscreenChange', checkFullscreen);

    // 初始检查
    checkFullscreen();

    return () => {
      document.removeEventListener('fullscreenchange', checkFullscreen);
      document.removeEventListener('webkitfullscreenchange', checkFullscreen);
      document.removeEventListener('mozfullscreenchange', checkFullscreen);
      document.removeEventListener('MSFullscreenChange', checkFullscreen);
    };
  }, []);

  if (status === 'hidden') {
    return null;
  }

  // 只使用基础CSS类名，不再使用fullscreen类，完全通过内联样式控制
  const containerClassName = 'mjpeg-status-overlay';

  // 基础样式 - 强制设置所有可能影响定位的样式
  const containerStyle: React.CSSProperties = {
    color: 'white',
    // 确保覆盖层尺寸正确
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
    // 强制设置定位样式
    position: isFullscreen ? 'fixed' : 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    // 强制清除所有可能影响定位的样式
    margin: 0,
    padding: 0,
    outline: 'none',
    // 居中样式
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    // 其他样式
    zIndex: isFullscreen ? 1000 : 10,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    boxSizing: 'border-box',
    transform: 'none'
  };
  

  if (status === 'loading') {
    return (
      <div className={containerClassName} style={containerStyle}>
        <div style={{ textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: '16px', fontSize: '16px' }}>
            {connectionState === 'connecting' && (
              <div>
                <div>正在连接MJPEG流...</div>
                {retryCount > 0 && (
                  <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
                    重连尝试 {retryCount}/{maxRetries}
                  </div>
                )}
                <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.5 }}>
                  超时时间: 20秒
                </div>
              </div>
            )}
            {connectionState === 'failed' && (
              <div style={{ color: '#ff4d4f' }}>连接失败</div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (status === 'paused') {
    return (
      <div className={containerClassName} style={containerStyle}>
        <div style={{ textAlign: 'center' }}>
          <PauseCircleOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
          <div style={{ fontSize: '18px', marginBottom: '4px' }}>视频播放已暂停</div>
          <div style={{ fontSize: '14px', opacity: 0.8 }}>
            MJPEG连接已断开，点击播放按钮重新连接
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error' && error) {
    return (
      <div className={containerClassName} style={containerStyle}>
        <div style={{ textAlign: 'center', maxWidth: '80%' }}>
          <Alert
            message={<span style={{ color: 'white', fontWeight: 'bold' }}>MJPEG流播放错误</span>}
            description={<span style={{ color: 'white' }}>{error}</span>}
            type="error"
            showIcon
            style={{
              marginBottom: '16px',
              backgroundColor: 'rgba(255, 77, 79, 0.1)',
              borderColor: '#ff4d4f',
              color: 'white'
            }}
            className="mjpeg-error-alert"
            action={
              retryCount < maxRetries && onRetry ? (
                <Button
                  type="primary"
                  danger
                  icon={<ReloadOutlined />}
                  onClick={onRetry}
                  size="small"
                >
                  重试连接 ({retryCount}/{maxRetries})
                </Button>
              ) : (
                <span style={{ fontSize: '12px', color: '#ff4d4f' }}>
                  已达到最大重试次数
                </span>
              )
            }
          />

          {/* 详细信息 */}
          {retryCount > 0 && (
            <div style={{ fontSize: '12px', color: '#ccc', marginTop: '12px' }}>
              <div>
                已尝试 {retryCount} 次重连
                {lastErrorTime && lastErrorTime > 0 && (
                  <span> · 最后失败时间: {new Date(lastErrorTime).toLocaleTimeString()}</span>
                )}
              </div>
              {onToggleAutoRetry && (
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '12px' }}>
                    <input
                      type="checkbox"
                      checked={autoRetryEnabled}
                      onChange={(e) => onToggleAutoRetry(e.target.checked)}
                      style={{ marginRight: '4px' }}
                    />
                    自动重连
                  </label>
                  {!autoRetryEnabled && (
                    <span style={{ color: '#faad14', fontSize: '11px' }}>已禁用</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
};

export default MJPEGStatusOverlay;
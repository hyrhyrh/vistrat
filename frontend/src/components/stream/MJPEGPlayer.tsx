import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Spin, Alert } from 'antd';
import styles from './MJPEGPlayer.module.css';
import MJPEGStatusOverlay from './MJPEGStatusOverlay';

interface MJPEGPlayerProps {
  rtspUrl: string;
  width?: number | string;
  height?: number | string;
  onError?: (hasError: boolean) => void;
  onConnectionStateChange?: (state: string) => void;
  autoPlay?: boolean;
  onRefresh?: () => void; // 暴露刷新功能
  isPaused?: boolean; // 外部暂停状态
}

export const MJPEGPlayer: React.FC<MJPEGPlayerProps> = ({
  rtspUrl,
  width = '100%',
  height = '400px',
  onError,
  onConnectionStateChange,
  autoPlay = true,
  onRefresh,
  isPaused = false,
}) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<string>('connecting');
  const [retryCount, setRetryCount] = useState(0);
  const [lastErrorTime, setLastErrorTime] = useState<number>(0);
  const [autoRetryEnabled, setAutoRetryEnabled] = useState(true);
  const [forceRefresh, setForceRefresh] = useState(0); // 用于强制刷新
  const retryCountRef = useRef(0);

  // 使用useRef避免回调函数重复创建
  const onConnectionStateChangeRef = useRef(onConnectionStateChange);
  const onErrorRef = useRef(onError);

  // 更新ref引用
  useEffect(() => {
    onConnectionStateChangeRef.current = onConnectionStateChange;
    onErrorRef.current = onError;
  });

  // 缓存回调函数引用，避免useEffect无限循环
  const handleConnectionChange = useCallback((state: string) => {
    setConnectionState(state);
    onConnectionStateChangeRef.current?.(state);
  }, []);

  const handleErrorChange = useCallback((hasError: boolean) => {
    onErrorRef.current?.(hasError);
  }, []);

  useEffect(() => {
    if (!rtspUrl || !autoPlay) return;

    // 只在URL变化时重置计数器，重连时保持计数器
    const isUrlChange = forceRefresh === 0;
    if (isUrlChange) {
      setRetryCount(0);
      retryCountRef.current = 0;
    }

    // 重置状态
    setLoading(true);
    setError(null);
    handleConnectionChange('connecting');

    // 智能URL编码：针对RTSP协议的特殊处理
    const smartEncodeUrl = (url: string): string => {
      try {
        console.log(`[MJPEG] 原始URL: ${url}`);
        
        // 对于RTSP URL，使用简单但有效的编码策略
        if (url.toLowerCase().startsWith('rtsp://')) {
          // 方法1: 完整URL编码，确保路径正确传输
          const encoded = encodeURIComponent(url);
          console.log(`[MJPEG] 编码后URL: ${encoded}`);
          return encoded;
        }
        
        // 非RTSP协议的情况
        return encodeURIComponent(url);
      } catch (e) {
        console.warn('[MJPEG] URL编码失败:', e);
        return encodeURIComponent(url);
      }
    };

    const mjpegUrl = `/api/mjpeg/stream/${smartEncodeUrl(rtspUrl)}`;
    const img = imgRef.current;
    if (!img) return;

    // 连接超时设置（分阶段）
    let connectTimeout: NodeJS.Timeout;
    let warningTimeout: NodeJS.Timeout;
    let finalTimeout: NodeJS.Timeout;

    // 连接状态管理
    let isConnected = false;
    let isAborted = false;

    // 图片加载事件（首帧加载完成）
    const handleLoad = () => {
      if (isAborted) return;

      console.log('[MJPEG] ✅ 首帧加载成功');
      isConnected = true;
      setLoading(false);
      setError(null);
      setRetryCount(0);
      retryCountRef.current = 0;
      handleConnectionChange('connected');
      handleErrorChange(false);

      // 清除所有超时
      clearTimeout(connectTimeout);
      clearTimeout(warningTimeout);
      clearTimeout(finalTimeout);
    };

    // 图片加载错误
    const handleError = (e: Event) => {
      if (isAborted || isConnected) return;

      console.error('[MJPEG] ❌ 流连接失败:', e);
      const currentTime = Date.now();
      setLastErrorTime(currentTime);

      // 清除超时
      clearTimeout(connectTimeout);
      clearTimeout(warningTimeout);
      clearTimeout(finalTimeout);

      // 立即增加重连计数
      const newRetryCount = retryCountRef.current + 1;
      retryCountRef.current = newRetryCount;
      setRetryCount(newRetryCount);

      if (autoRetryEnabled && newRetryCount <= 3) {
        console.log(`[MJPEG] 🔄 自动重连 (第${newRetryCount}次) 将在3秒后开始`);

        // 显示重连状态
        handleConnectionChange('connecting');

        // 3秒后自动重连
        setTimeout(() => {
          if (!isAborted) {
            console.log(`[MJPEG] 📡 执行自动重连 (第${newRetryCount}次)`);
            // 通过强制刷新触发重新连接
            setForceRefresh(prev => prev + 1);
          }
        }, 3000);
      } else {
        // 超过重试次数，标记为失败
        setLoading(false);
        setError(newRetryCount > 3 ? '连接失败次数过多，请检查RTSP流地址或网络连接' : 'MJPEG流连接失败');
        handleConnectionChange('failed');
        handleErrorChange(true);
      }
    };

    // 连接被中断
    const handleAbort = () => {
      if (isAborted) return;

      console.log('[MJPEG] ⚠️ 连接被中断');
      setLoading(false);
      handleConnectionChange('disconnected');
    };

    // 尝试连接
    const attemptConnection = () => {
      if (isAborted) return;

      const currentRetryCount = retryCountRef.current;
      console.log(`[MJPEG] 📡 尝试连接 (第${currentRetryCount + 1}次): ${rtspUrl}`);
      img.src = mjpegUrl;

      // 监听图片事件
      img.onload = handleLoad;
      img.onerror = handleError;
      img.onabort = handleAbort;
    };

    // 设置分阶段超时
    // 1. 10秒警告
    warningTimeout = setTimeout(() => {
      if (!isConnected && !isAborted) {
        console.warn('[MJPEG] ⚠️ 连接超时警告 - 10秒内未收到首帧');
      }
    }, 10000);

    // 2. 20秒超时，标记为失败并尝试重连
    finalTimeout = setTimeout(() => {
      if (!isConnected && !isAborted) {
        console.error('[MJPEG] ❌ 连接最终超时 - 20秒内未能建立连接');

        // 立即增加重连计数
        const newRetryCount = retryCountRef.current + 1;
        retryCountRef.current = newRetryCount;
        setRetryCount(newRetryCount);

        if (autoRetryEnabled && newRetryCount <= 3) {
          console.log(`[MJPEG] 🔄 连接超时自动重连 (第${newRetryCount}次) 将在3秒后开始`);

          // 显示重连状态
          handleConnectionChange('connecting');

          // 3秒后自动重连
          setTimeout(() => {
            if (!isAborted) {
              console.log(`[MJPEG] 📡 执行超时重连 (第${newRetryCount}次)`);
              // 通过强制刷新触发重新连接
              setForceRefresh(prev => prev + 1);
            }
          }, 3000);
        } else {
          // 超过重试次数，标记为失败
          setLoading(false);
          setError('连接超时：多次尝试均在20秒内未能建立MJPEG流连接');
          handleConnectionChange('failed');
          handleErrorChange(true);
        }
      }
    }, 20000);

    // 开始首次连接尝试
    attemptConnection();

    return () => {
      isAborted = true;

      // 清除所有超时
      clearTimeout(connectTimeout);
      clearTimeout(warningTimeout);
      clearTimeout(finalTimeout);

      if (img) {
        img.onload = null;
        img.onerror = null;
        img.onabort = null;
        // 清空src以停止流
        if (img.src.includes('/api/mjpeg/stream/')) {
          img.src = '';
        }
      }

      if (!isAborted) {
        handleConnectionChange('closed');
      }
    };
  }, [rtspUrl, autoPlay, forceRefresh]);

  // 确保retryCount状态同步
  useEffect(() => {
    retryCountRef.current = retryCount;
  }, [retryCount]);

  // URL变化时重置forceRefresh
  useEffect(() => {
    setForceRefresh(0);
  }, [rtspUrl]);

  // 重连功能
  const handleRetry = useCallback(() => {
    if (retryCount >= 3) {
      setError('连接失败次数过多，请检查RTSP流地址或网络连接');
      return;
    }

    const newRetryCount = retryCountRef.current + 1;
    console.log(`[MJPEG] 🔄 手动重连 (第${newRetryCount}次)`);
    retryCountRef.current = newRetryCount;
    setRetryCount(newRetryCount);
    setLoading(true);
    setError(null);
    handleConnectionChange('connecting');

    // 通过强制刷新触发重新连接
    setTimeout(() => {
      setForceRefresh(prev => prev + 1);
    }, 500);
  }, [rtspUrl, retryCount]);

  // 刷新功能 - 供外部调用
  const handleManualRefresh = useCallback(() => {
    console.log('[MJPEG] 🔄 手动刷新连接');
    setRetryCount(0);
    retryCountRef.current = 0;
    setLoading(true);
    setError(null);
    handleConnectionChange('connecting');

    // 触发刷新回调
    onRefresh?.();

    // 通过强制刷新触发重新连接
    setTimeout(() => {
      setForceRefresh(prev => prev + 1);
    }, 200);
  }, [rtspUrl, onRefresh]);

  // 暴露刷新方法给父组件
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).mjpegRefresh = handleManualRefresh;
    }
  }, [handleManualRefresh]);

  if (error) {
    return (
      <div className={styles.container} style={{ width, height }}>
        <MJPEGStatusOverlay
          status="error"
          error={error}
          retryCount={retryCount}
          maxRetries={3}
          lastErrorTime={lastErrorTime}
          autoRetryEnabled={autoRetryEnabled}
          onRetry={handleRetry}
          onToggleAutoRetry={setAutoRetryEnabled}
          width={width}
          height={height}
        />
      </div>
    );
  }

  return (
    <div className={styles.container} style={{ width, height }}>
      {/* 使用模块化状态组件 */}
      <MJPEGStatusOverlay
        status={
          isPaused ? 'paused' :
          (loading && autoPlay) ? 'loading' : 'hidden'
        }
        connectionState={connectionState}
        retryCount={retryCount}
        maxRetries={3}
        width={width}
        height={height}
      />

      <img
        ref={imgRef}
        className={`${styles.videoElement} ${loading ? styles.hiddenVideo : ''}`}
        alt="MJPEG视频流"
        crossOrigin="anonymous"
        onLoadStart={() => {
          // 图片开始加载
        }}
        onProgress={() => {
          // 图片数据加载中
        }}
      />

      {/* 连接状态指示器 */}
      <div
        className={`${styles.statusIndicator} ${styles[`status${connectionState.charAt(0).toUpperCase() + connectionState.slice(1)}`] || styles.statusDisconnected}`}
      >
        {connectionState === 'connected' && (
          <>● 已连接</>
        )}
        {connectionState === 'connecting' && (
          <>● 连接中{retryCount > 0 && ` (${retryCount}/3)`}</>
        )}
        {connectionState === 'failed' && (
          <>● 连接失败{retryCount > 0 && ` (${retryCount}次)`}</>
        )}
        {connectionState === 'disconnected' && (
          <>● 已断开</>
        )}
        {connectionState === 'closed' && (
          <>● 已关闭</>
        )}
      </div>

      {/* 调试信息 */}
      {process.env.NODE_ENV === 'development' && (
        <div className={styles.debugInfo}>
          <span className={styles.debugLine}>尺寸: {imgRef.current?.naturalWidth || 0}x{imgRef.current?.naturalHeight || 0}</span>
          <span className={styles.debugLine}>完整: {imgRef.current?.complete ? '是' : '否'}</span>
        </div>
      )}
    </div>
  );
};

export default MJPEGPlayer;
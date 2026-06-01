import React, { useEffect, useRef, useState } from 'react';
import flvjs from 'flv.js';
import { Button, Spin } from 'antd';
import {
  PlayCircleOutlined,
  PauseOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  VideoCameraOutlined,
  LoadingOutlined,
} from '@ant-design/icons';

interface FLVPlayerProps {
  url?: string;                    // 直接提供FLV URL（用于VideoComparisonPage）
  rtspUrl?: string;                // 提供RTSP URL自动转换为FLV（用于MJPEGPlayer替换）
  title?: string;
  width?: number | string;
  height?: number | string;
  autoPlay?: boolean;
  onError?: (hasError: boolean) => void;  // 错误回调（兼容MJPEGPlayer）
  simple?: boolean;                // 简洁模式：只显示video，不显示Card和控制按钮（用于页面嵌入）
}

/**
 * HTTP-FLV无损视频播放器组件
 *
 * 特性：
 * - 无损H.264视频传输
 * - 低延迟（1-3秒）
 * - 稳定可靠（flv.js成熟方案）
 * - 底部悬浮控制栏
 */
const FLVPlayer: React.FC<FLVPlayerProps> = ({
  url,
  rtspUrl,
  title,
  width = '100%',
  height = 600,
  autoPlay = true,
  onError,
  simple = false
}) => {
  // 构建实际使用的FLV URL
  const actualUrl = React.useMemo(() => {
    if (url) {
      return url;  // 直接使用提供的FLV URL
    } else if (rtspUrl) {
      // 从RTSP URL构建FLV URL
      return `/api/flv/stream/${encodeURIComponent(rtspUrl)}`;
    } else {
      console.error('[FLVPlayer] 必须提供url或rtspUrl之一');
      return '';
    }
  }, [url, rtspUrl]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const flvPlayerRef = useRef<flvjs.Player | null>(null);
  const hideControlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const handlersRef = useRef<{
    loadeddata?: () => void;
    canplay?: () => void;
    playing?: () => void;
  }>({});

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(true);

  useEffect(() => {
    console.log('[FLVPlayer] useEffect triggered, actualUrl:', actualUrl);
    console.log('[FLVPlayer] flvjs object:', flvjs);
    console.log('[FLVPlayer] videoRef.current:', videoRef.current);

    // 检查浏览器支持
    if (!flvjs.isSupported()) {
      console.error('[FLVPlayer] Browser NOT supported!');
      const errorMsg = '您的浏览器不支持FLV播放，请使用Chrome/Edge/Firefox浏览器';
      setError(errorMsg);
      setIsLoading(false);
      onError?.(true);
      return;
    }
    console.log('[FLVPlayer] Browser IS supported');

    if (videoRef.current && actualUrl) {
      console.log('[FLVPlayer] 开始初始化播放器:', actualUrl);
      console.log('[FLVPlayer] Video element:', videoRef.current);

      // 清空video元素的旧src（防止与新播放器冲突）
      if (videoRef.current.src) {
        console.log('[FLVPlayer] 清空旧的video src:', videoRef.current.src);
        videoRef.current.src = '';
        videoRef.current.load(); // 重置video元素
      }

      // 创建FLV播放器
      const flvPlayer = flvjs.createPlayer(
        {
          type: 'flv',
          url: actualUrl,
          isLive: true,
          hasAudio: false, // RTSP流通常无音频
        },
        {
          enableWorker: false,          // 禁用Worker（Vite兼容性问题）
          enableStashBuffer: false,     // 禁用缓存（降低延迟）
          stashInitialSize: 128,        // 初始缓存大小128KB
          autoCleanupSourceBuffer: true, // 自动清理缓存
          lazyLoad: false,              // 立即加载
          lazyLoadMaxDuration: 3,       // 最大缓冲3秒
          lazyLoadRecoverDuration: 1,   // 恢复缓冲1秒
        }
      );

      console.log('[FLVPlayer] FLV player created:', flvPlayer);

      flvPlayer.attachMediaElement(videoRef.current);
      console.log('[FLVPlayer] Media element attached');

      flvPlayer.load();
      console.log('[FLVPlayer] Stream loading started');

      // 监听加载完成（多个事件以确保loading状态被清除）
      const handleLoadedData = () => {
        console.log('[FLVPlayer] loadeddata事件: 视频数据加载完成');
        setIsLoading(false);
      };

      const handleCanPlay = () => {
        console.log('[FLVPlayer] canplay事件: 视频准备就绪');
        setIsLoading(false);
      };

      const handlePlaying = () => {
        console.log('[FLVPlayer] playing事件: 视频开始播放');
        setIsLoading(false);
        setIsPlaying(true);
      };

      // 保存到ref以便在清理时使用
      handlersRef.current = {
        loadeddata: handleLoadedData,
        canplay: handleCanPlay,
        playing: handlePlaying
      };

      videoRef.current.addEventListener('loadeddata', handleLoadedData);
      videoRef.current.addEventListener('canplay', handleCanPlay);
      videoRef.current.addEventListener('playing', handlePlaying);

      // 监听错误
      flvPlayer.on(flvjs.Events.ERROR, (errorType, errorDetail) => {
        console.error('[FLVPlayer] 播放错误:', errorType, errorDetail);

        let errorMsg = '';
        if (errorType === 'NetworkError') {
          errorMsg = '📡 网络连接失败\n\n可能原因：\n• RTSP地址错误或摄像头离线\n• 网络不通或防火墙阻止\n• 摄像头认证失败';
        } else if (errorType === 'MediaError') {
          errorMsg = '🎬 媒体解码失败\n\n可能原因：\n• 视频流格式不支持\n• 视频编码格式问题\n• 流数据损坏';
        } else {
          errorMsg = `⚠️ 播放错误: ${errorType}\n\n请检查视频源是否正常`;
        }

        setError(errorMsg);
        setIsPlaying(false);
        setIsLoading(false);
        onError?.(true);
      });

      flvPlayerRef.current = flvPlayer;

      // 尝试自动播放（现代浏览器可能会阻止）
      if (autoPlay) {
        setTimeout(() => {
          if (videoRef.current && flvPlayerRef.current) {
            videoRef.current.play()
              .then(() => {
                setIsPlaying(true);
                setError(null);
                onError?.(false);
                console.log('[FLVPlayer] 自动播放成功');
              })
              .catch((e) => {
                // 自动播放被阻止是正常的，不显示错误
                console.log('[FLVPlayer] 自动播放被浏览器阻止（这是正常的），请手动点击播放按钮');
                setIsPlaying(false);
              });
          }
        }, 1000);
      }
    }

    return () => {
      // 清理资源
      if (flvPlayerRef.current) {
        try {
          flvPlayerRef.current.pause();
          flvPlayerRef.current.unload();
          flvPlayerRef.current.detachMediaElement();
          flvPlayerRef.current.destroy();
          flvPlayerRef.current = null;
          console.log('[FLVPlayer] 播放器已清理');
        } catch (e) {
          console.error('[FLVPlayer] 清理失败:', e);
        }
      }

      // 清空video元素的src，防止blob URL泄漏
      if (videoRef.current) {
        const video = videoRef.current;
        // 使用ref中保存的handler函数
        if (handlersRef.current.loadeddata) {
          video.removeEventListener('loadeddata', handlersRef.current.loadeddata);
        }
        if (handlersRef.current.canplay) {
          video.removeEventListener('canplay', handlersRef.current.canplay);
        }
        if (handlersRef.current.playing) {
          video.removeEventListener('playing', handlersRef.current.playing);
        }
        video.src = '';
        video.load();
        console.log('[FLVPlayer] Video元素已重置');
      }

      // 清理定时器
      if (hideControlsTimeoutRef.current) {
        clearTimeout(hideControlsTimeoutRef.current);
      }
    };
  }, [actualUrl]);

  const handlePlay = () => {
    console.log('[FLVPlayer] handlePlay called');
    if (videoRef.current && flvPlayerRef.current) {
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            console.log('[FLVPlayer] ✅ 播放成功！');
            setIsPlaying(true);
            setError(null);
            onError?.(false);
          })
          .catch((e) => {
            console.error('[FLVPlayer] ❌ 播放失败:', e);
            const errorMsg = `播放失败: ${e.message}`;
            setError(errorMsg);
            onError?.(true);
          });
      }
    }
  };

  const handlePause = () => {
    if (flvPlayerRef.current && videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
      console.log('[FLVPlayer] 暂停播放');
    }
  };

  const handleReload = () => {
    if (flvPlayerRef.current && videoRef.current) {
      console.log('[FLVPlayer] 重新加载');
      setIsLoading(true);

      // 销毁旧播放器
      flvPlayerRef.current.pause();
      flvPlayerRef.current.unload();
      flvPlayerRef.current.detachMediaElement();
      flvPlayerRef.current.destroy();

      // 创建新播放器
      const newPlayer = flvjs.createPlayer(
        {
          type: 'flv',
          url: actualUrl,
          isLive: true,
          hasAudio: false,
        },
        {
          enableWorker: false,
          enableStashBuffer: false,
          stashInitialSize: 128,
          autoCleanupSourceBuffer: true,
        }
      );

      newPlayer.attachMediaElement(videoRef.current);
      newPlayer.load();

      newPlayer.on(flvjs.Events.ERROR, (errorType, errorDetail) => {
        console.error('[FLVPlayer] 播放错误:', errorType, errorDetail);
        setError(`播放错误: ${errorType} - ${errorDetail}`);
        setIsLoading(false);
      });

      flvPlayerRef.current = newPlayer;
      setError(null);

      setTimeout(() => {
        setIsLoading(false);
        handlePlay();
      }, 500);
    }
  };

  const handleFullscreen = () => {
    if (containerRef.current) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
    }
  };

  // 鼠标移动处理：显示控制栏
  const handleMouseMove = () => {
    setShowControls(true);

    // 清除之前的定时器
    if (hideControlsTimeoutRef.current) {
      clearTimeout(hideControlsTimeoutRef.current);
    }

    // 3秒后自动隐藏控制栏（仅在播放时）
    if (isPlaying) {
      hideControlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
  };

  // 鼠标离开处理
  const handleMouseLeave = () => {
    if (isPlaying) {
      setShowControls(false);
    }
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        position: 'relative',
        width: width,
        height: typeof height === 'number' ? `${height}px` : height,
        backgroundColor: '#000',
        borderRadius: simple ? 0 : 8,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* 标题栏（非simple模式） */}
      {!simple && title && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          padding: '12px 16px',
          background: 'linear-gradient(to bottom, rgba(0,0,0,0.7), transparent)',
          color: '#fff',
          fontSize: '14px',
          fontWeight: 500,
          zIndex: 2,
          pointerEvents: 'none',
        }}>
          {title}
          <span style={{ fontSize: 12, color: '#bbb', marginLeft: 8 }}>
            (HTTP-FLV)
          </span>
        </div>
      )}

      {/* 视频元素 */}
      <video
        ref={videoRef}
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: '#000',
          display: 'block',
          objectFit: 'contain'
        }}
        muted
      />

      {/* 加载占位符 */}
      {isLoading && !error && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 5
        }}>
          <div style={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 20,
            boxShadow: '0 4px 20px rgba(24, 144, 255, 0.4)',
          }}>
            <VideoCameraOutlined style={{ fontSize: 36, color: '#fff' }} />
          </div>
          <div style={{ textAlign: 'center' }}>
            <LoadingOutlined style={{ fontSize: 24, color: '#1890ff' }} spin />
            <div style={{ color: '#fff', fontSize: 14, marginTop: 12 }}>视频流加载中...</div>
          </div>
        </div>
      )}

      {/* 错误提示遮罩层 - 紧凑样式 */}
      {error && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          padding: '16px',
          textAlign: 'center',
          zIndex: 10
        }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>⚠️</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '8px', color: '#fff' }}>
            视频流播放失败
          </div>
          <div style={{
            fontSize: '11px',
            color: '#999',
            marginBottom: '12px',
            maxWidth: '90%',
            lineHeight: '1.4',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
          }}>
            {error}
          </div>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={handleReload}
            size="small"
            style={{ fontSize: '12px' }}
          >
            重新连接
          </Button>
        </div>
      )}

      {/* 底部悬浮控制栏 */}
      {!error && (
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '12px 16px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.85), rgba(0,0,0,0.6), transparent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          opacity: showControls ? 1 : 0,
          transition: 'opacity 0.3s ease',
          zIndex: 3,
          pointerEvents: showControls ? 'auto' : 'none',
        }}>
          {/* 左侧控制按钮 */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {isPlaying ? (
              <Button
                type="text"
                icon={<PauseOutlined />}
                onClick={handlePause}
                style={{ color: '#fff' }}
              />
            ) : (
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={handlePlay}
                style={{ color: '#1890ff' }}
              />
            )}
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={handleReload}
              style={{ color: '#fff' }}
            />
          </div>

          {/* 右侧控制按钮 */}
          <div>
            <Button
              type="text"
              icon={<FullscreenOutlined />}
              onClick={handleFullscreen}
              style={{ color: '#fff' }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FLVPlayer;

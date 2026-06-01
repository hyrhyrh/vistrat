/**
 * 音频录音Hook (使用MediaRecorder API)
 * 配合后端语音识别服务(百度AI)使用
 */
import { useState, useRef, useCallback } from 'react';

interface UseAudioRecorderReturn {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  transcript: string;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  resetTranscript: () => void;
}

interface UseAudioRecorderOptions {
  onTranscriptReceived?: (text: string) => void;
  onError?: (error: string) => void;
}

export const useAudioRecorder = (
  options: UseAudioRecorderOptions = {}
): UseAudioRecorderReturn => {
  const { onTranscriptReceived, onError } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // 开始录音
  const startRecording = useCallback(async () => {
    try {
      setError(null);

      // 检查浏览器支持
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const errorMsg = '您的浏览器不支持录音功能';
        setError(errorMsg);
        onError?.(errorMsg);
        return;
      }

      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1, // 单声道
          sampleRate: 16000, // 16kHz采样率(百度要求)
          echoCancellation: true, // 回声消除
          noiseSuppression: true, // 降噪
        },
      });

      streamRef.current = stream;

      // 创建MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm', // WebM格式
      });

      audioChunksRef.current = [];

      // 收集音频数据
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // 录音停止时处理
      mediaRecorder.onstop = async () => {
        await processAudio();
      };

      // 开始录音
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

      console.log('录音开始...');
    } catch (err: any) {
      console.error('启动录音失败:', err);

      let errorMsg = '启动录音失败';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorMsg = '麦克风权限被拒绝,请在浏览器设置中允许访问麦克风';
      } else if (err.name === 'NotFoundError') {
        errorMsg = '未检测到麦克风设备';
      } else if (err.name === 'NotReadableError') {
        errorMsg = '麦克风被其他应用占用';
      }

      setError(errorMsg);
      onError?.(errorMsg);
    }
  }, [onError]);

  // 停止录音
  const stopRecording = useCallback(async () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // 停止音频流
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      console.log('录音停止');
    }
  }, [isRecording]);

  // 处理音频(发送到后端识别)
  const processAudio = async () => {
    try {
      setIsProcessing(true);
      setError(null);

      // 合并音频块
      const audioBlob = new Blob(audioChunksRef.current, {
        type: 'audio/webm',
      });

      console.log('音频大小:', (audioBlob.size / 1024).toFixed(2), 'KB');

      // 创建FormData
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      // 发送到后端识别
      const response = await fetch('/api/speech/recognize', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '语音识别失败');
      }

      const result = await response.json();
      const text = result.text || '';

      if (!text) {
        throw new Error('未识别到语音内容,请重试');
      }

      console.log('识别结果:', text);

      setTranscript(text);
      onTranscriptReceived?.(text);
    } catch (err: any) {
      console.error('语音识别失败:', err);

      const errorMsg = err.message || '语音识别失败,请重试';
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setIsProcessing(false);
      audioChunksRef.current = [];
    }
  };

  // 重置转录文本
  const resetTranscript = useCallback(() => {
    setTranscript('');
    setError(null);
  }, []);

  return {
    isRecording,
    isProcessing,
    error,
    transcript,
    startRecording,
    stopRecording,
    resetTranscript,
  };
};

export default useAudioRecorder;

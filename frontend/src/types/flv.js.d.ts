/**
 * flv.js TypeScript类型声明
 * 用于生产环境构建时的类型支持
 */

declare module 'flv.js' {
  export interface MediaDataSource {
    type: string;
    url: string;
    isLive?: boolean;
    cors?: boolean;
    withCredentials?: boolean;
    hasAudio?: boolean;
    hasVideo?: boolean;
    duration?: number;
    filesize?: number;
    segments?: MediaSegment[];
  }

  export interface MediaSegment {
    duration: number;
    filesize?: number;
    url: string;
  }

  export interface Config {
    enableWorker?: boolean;
    enableStashBuffer?: boolean;
    stashInitialSize?: number;
    isLive?: boolean;
    lazyLoad?: boolean;
    lazyLoadMaxDuration?: number;
    lazyLoadRecoverDuration?: number;
    deferLoadAfterSourceOpen?: boolean;
    autoCleanupSourceBuffer?: boolean;
    autoCleanupMaxBackwardDuration?: number;
    autoCleanupMinBackwardDuration?: number;
    statisticsInfoReportInterval?: number;
    fixAudioTimestampGap?: boolean;
    accurateSeek?: boolean;
    seekType?: string;
    seekParamStart?: string;
    seekParamEnd?: string;
    rangeLoadZeroStart?: boolean;
    customSeekHandler?: any;
    reuseRedirectedURL?: boolean;
    referrerPolicy?: string;
  }

  export interface PlayerEventMap {
    [Events.ERROR]: (errorType: string, errorDetail: string, errorInfo?: any) => void;
    [Events.LOADING_COMPLETE]: () => void;
    [Events.RECOVERED_EARLY_EOF]: () => void;
    [Events.MEDIA_INFO]: (mediaInfo: any) => void;
    [Events.METADATA_ARRIVED]: (metadata: any) => void;
    [Events.SCRIPTDATA_ARRIVED]: (scriptData: any) => void;
    [Events.STATISTICS_INFO]: (statisticsInfo: any) => void;
  }

  export class Player {
    constructor(mediaDataSource: MediaDataSource, config?: Config);
    destroy(): void;
    attachMediaElement(mediaElement: HTMLMediaElement): void;
    detachMediaElement(): void;
    load(): void;
    unload(): void;
    play(): Promise<void>;
    pause(): void;
    type: string;
    buffered: TimeRanges;
    duration: number;
    volume: number;
    muted: boolean;
    currentTime: number;
    mediaInfo: any;
    statisticsInfo: any;
    on<K extends keyof PlayerEventMap>(event: K, listener: PlayerEventMap[K]): void;
    off<K extends keyof PlayerEventMap>(event: K, listener: PlayerEventMap[K]): void;
  }

  export enum Events {
    ERROR = 'error',
    LOADING_COMPLETE = 'loading_complete',
    RECOVERED_EARLY_EOF = 'recovered_early_eof',
    MEDIA_INFO = 'media_info',
    METADATA_ARRIVED = 'metadata_arrived',
    SCRIPTDATA_ARRIVED = 'scriptdata_arrived',
    STATISTICS_INFO = 'statistics_info',
  }

  export enum ErrorTypes {
    NETWORK_ERROR = 'NetworkError',
    MEDIA_ERROR = 'MediaError',
    OTHER_ERROR = 'OtherError',
  }

  export enum ErrorDetails {
    NETWORK_EXCEPTION = 'NetworkException',
    NETWORK_STATUS_CODE_INVALID = 'NetworkStatusCodeInvalid',
    NETWORK_TIMEOUT = 'NetworkTimeout',
    NETWORK_UNRECOVERABLE_EARLY_EOF = 'NetworkUnrecoverableEarlyEof',
    MEDIA_MSE_ERROR = 'MediaMSEError',
    MEDIA_FORMAT_ERROR = 'MediaFormatError',
    MEDIA_FORMAT_UNSUPPORTED = 'MediaFormatUnsupported',
    MEDIA_CODEC_UNSUPPORTED = 'MediaCodecUnsupported',
  }

  export function createPlayer(mediaDataSource: MediaDataSource, config?: Config): Player;
  export function isSupported(): boolean;
  export function getFeatureList(): {
    mseLivePlayback: boolean;
    mseLiveFlvPlayback: boolean;
    networkStreamIO: boolean;
    networkLoaderName: string;
    nativeMP4H264Playback: boolean;
    nativeWebmVP8Playback: boolean;
    nativeWebmVP9Playback: boolean;
  };

  export class FlvPlayer extends Player {
    constructor(mediaDataSource: MediaDataSource, config?: Config);
  }

  export class NativePlayer extends Player {
    constructor(mediaDataSource: MediaDataSource, config?: Config);
  }

  export class LoggingControl {
    static getConfig(): any;
    static applyConfig(config: any): void;
    static addLogListener(listener: (type: string, str: string) => void): void;
    static removeLogListener(listener: (type: string, str: string) => void): void;
  }
}

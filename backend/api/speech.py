"""
语音识别API
使用百度AI语音识别服务
"""
import io
import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from aip import AipSpeech
from pydub import AudioSegment
from config.settings import APIConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])


# ========== 百度AI配置 ==========

class BaiduSpeechConfig:
    """百度AI语音识别配置"""
    APP_ID = os.getenv("BAIDU_APP_ID", "")
    API_KEY = os.getenv("BAIDU_API_KEY", "")
    SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")

    @classmethod
    def is_configured(cls) -> bool:
        """检查是否已配置"""
        return bool(cls.APP_ID and cls.API_KEY and cls.SECRET_KEY)


# 初始化百度AI客户端
_baidu_client = None

def get_baidu_client() -> AipSpeech:
    """
    获取百度AI客户端(懒加载)

    Returns:
        AipSpeech: 百度语音识别客户端

    Raises:
        HTTPException: 未配置API密钥
    """
    global _baidu_client

    if not BaiduSpeechConfig.is_configured():
        raise HTTPException(
            status_code=503,
            detail="语音识别服务未配置,请设置BAIDU_APP_ID、BAIDU_API_KEY、BAIDU_SECRET_KEY环境变量"
        )

    if _baidu_client is None:
        _baidu_client = AipSpeech(
            BaiduSpeechConfig.APP_ID,
            BaiduSpeechConfig.API_KEY,
            BaiduSpeechConfig.SECRET_KEY
        )
        logger.info("百度AI语音识别客户端初始化成功")

    return _baidu_client


# ========== 音频处理工具 ==========

def convert_audio_to_wav(audio_data: bytes, source_format: str = "webm") -> bytes:
    """
    将音频转换为WAV格式(百度AI要求)

    Args:
        audio_data: 原始音频数据
        source_format: 源音频格式(webm/mp3/m4a等)

    Returns:
        bytes: WAV格式音频数据
    """
    try:
        # 从bytes创建AudioSegment
        audio = AudioSegment.from_file(
            io.BytesIO(audio_data),
            format=source_format
        )

        # 转换为WAV格式
        # 百度AI要求: 16kHz采样率,16bit,单声道
        audio = audio.set_frame_rate(16000)
        audio = audio.set_sample_width(2)  # 16bit
        audio = audio.set_channels(1)  # 单声道

        # 导出为WAV
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_data = wav_io.getvalue()

        logger.info(f"音频转换成功: {source_format} -> WAV, 大小: {len(wav_data)} bytes")

        return wav_data

    except Exception as e:
        logger.error(f"音频转换失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"音频格式转换失败: {str(e)}"
        )


# ========== 响应模型 ==========

class RecognitionResponse(BaseModel):
    """语音识别响应"""
    text: str
    confidence: float = 0.0
    message: str = "识别成功"


# ========== API端点 ==========

@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_speech(
    audio: UploadFile = File(..., description="音频文件(webm/wav/mp3等)")
):
    """
    语音识别端点

    Args:
        audio: 音频文件

    Returns:
        RecognitionResponse: 识别结果
    """
    try:
        # 读取音频文件
        audio_data = await audio.read()
        logger.info(f"收到音频文件: {audio.filename}, 大小: {len(audio_data)} bytes")

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="音频文件为空")

        # 检测文件格式
        filename = audio.filename or ""
        if filename.endswith(".webm"):
            source_format = "webm"
        elif filename.endswith(".wav"):
            source_format = "wav"
        elif filename.endswith(".mp3"):
            source_format = "mp3"
        else:
            # 默认尝试webm
            source_format = "webm"

        # 转换为WAV格式
        wav_data = convert_audio_to_wav(audio_data, source_format)

        # 获取百度AI客户端
        client = get_baidu_client()

        # 调用语音识别API
        result = client.asr(
            wav_data,
            'wav',
            16000,
            {
                'dev_pid': 1537,  # 1537: 普通话(支持简单的英文识别)
                'format': 'wav',
            }
        )

        logger.debug(f"百度AI识别结果: {result}")

        # 解析结果
        if result.get('err_no') == 0:
            # 识别成功
            text_list = result.get('result', [])
            text = ''.join(text_list) if text_list else ''

            if not text:
                raise HTTPException(
                    status_code=400,
                    detail="未识别到语音内容,请确保说话清晰并靠近麦克风"
                )

            logger.info(f"识别成功: {text}")

            return RecognitionResponse(
                text=text,
                confidence=1.0,
                message="识别成功"
            )
        else:
            # 识别失败
            err_msg = result.get('err_msg', '未知错误')
            err_no = result.get('err_no', -1)

            logger.error(f"百度AI识别失败: err_no={err_no}, err_msg={err_msg}")

            # 错误码映射
            error_messages = {
                3300: "输入参数不正确",
                3301: "音频质量过差",
                3302: "鉴权失败",
                3303: "语音服务器后端问题",
                3304: "用户的请求QPS超限制",
                3305: "用户的日pv（日请求量）超限制",
                3307: "语音服务器后端识别出错问题",
                3308: "音频过长",
                3309: "音频无效",
                3310: "音频时长过短",
                3311: "音频文件过大",
                3312: "音频格式不支持",
            }

            user_message = error_messages.get(err_no, f"识别失败: {err_msg}")

            raise HTTPException(
                status_code=400,
                detail=user_message
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"语音识别服务异常: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    语音识别服务健康检查

    Returns:
        dict: 健康状态
    """
    is_configured = BaiduSpeechConfig.is_configured()

    return {
        "status": "healthy" if is_configured else "not_configured",
        "service": "baidu_speech_recognition",
        "configured": is_configured,
        "message": "语音识别服务正常" if is_configured else "未配置API密钥"
    }

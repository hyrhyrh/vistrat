#!/bin/bash
# 验证 ffmpeg 在容器中是否正确安装

echo "========================================="
echo "验证 ffmpeg 安装"
echo "========================================="

# 检查 ffmpeg 命令是否存在
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg 命令已安装"
    echo ""
    echo "版本信息："
    ffmpeg -version | head -5
    echo ""
else
    echo "❌ ffmpeg 命令未找到"
    exit 1
fi

# 检查 ffprobe 命令（ffmpeg 套件的一部分）
if command -v ffprobe &> /dev/null; then
    echo "✅ ffprobe 命令已安装"
else
    echo "⚠️  ffprobe 命令未找到"
fi

echo ""
echo "========================================="
echo "测试 pydub 是否能找到 ffmpeg"
echo "========================================="

# 测试 Python 中 pydub 是否能正确使用 ffmpeg
python3 -c "
import sys
try:
    from pydub import AudioSegment
    from pydub.utils import which

    ffmpeg_path = which('ffmpeg')
    if ffmpeg_path:
        print(f'✅ pydub 可以找到 ffmpeg: {ffmpeg_path}')
        sys.exit(0)
    else:
        print('❌ pydub 无法找到 ffmpeg')
        sys.exit(1)
except ImportError as e:
    print(f'❌ pydub 未安装: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 测试失败: {e}')
    sys.exit(1)
"

exit_code=$?
echo ""
if [ $exit_code -eq 0 ]; then
    echo "========================================="
    echo "✅ 所有检查通过！"
    echo "========================================="
else
    echo "========================================="
    echo "❌ 检查失败，请检查 ffmpeg 安装"
    echo "========================================="
fi

exit $exit_code

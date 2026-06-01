#!/usr/bin/env python3
"""
测试帧质量检测器
验证能否正确过滤问题图片（1.jpg, 2.jpg, 3.jpg）并通过正常图片（4.jpg）
"""

import sys
import cv2
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.frame_quality_checker import frame_quality_checker

def test_image_quality(image_path: str):
    """测试单张图片的质量"""
    print(f"\n{'='*80}")
    print(f"测试图片: {image_path}")
    print(f"{'='*80}")

    # 读取图片
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"❌ 无法读取图片: {image_path}")
        return None

    print(f"✅ 图片尺寸: {frame.shape[1]}x{frame.shape[0]}")

    # 测试标准模式
    print("\n【标准模式检测】")
    metrics_standard = frame_quality_checker.check_frame_quality(
        frame, verbose=True, enable_strict_mode=False
    )
    print(f"  - 清晰度: {metrics_standard.sharpness:.2f}")
    print(f"  - 亮度: {metrics_standard.brightness:.2f}")
    print(f"  - 对比度: {metrics_standard.contrast:.2f}")
    print(f"  - 质量分数: {metrics_standard.quality_score:.2f}")
    print(f"  - 是否清晰: {'✅ 通过' if metrics_standard.is_clear else '❌ 不通过'}")

    # 测试严格模式
    print("\n【严格模式检测】")
    metrics_strict = frame_quality_checker.check_frame_quality(
        frame, verbose=True, enable_strict_mode=True
    )
    print(f"  - 清晰度: {metrics_strict.sharpness:.2f}")
    print(f"  - 亮度: {metrics_strict.brightness:.2f}")
    print(f"  - 对比度: {metrics_strict.contrast:.2f}")
    print(f"  - 质量分数: {metrics_strict.quality_score:.2f}")
    print(f"  - 是否清晰: {'✅ 通过' if metrics_strict.is_clear else '❌ 不通过'}")

    # 灰色帧检测
    print("\n【灰色帧检测】")
    is_gray = frame_quality_checker.detect_gray_frame(frame)
    print(f"  - 是否为灰色帧: {'❌ 是（解码失败）' if is_gray else '✅ 否'}")

    # 局部质量检测
    print("\n【局部质量检测】")
    local_ok, min_score = frame_quality_checker.check_local_quality(frame)
    print(f"  - 局部质量: {'✅ 通过' if local_ok else '❌ 不通过'}")
    print(f"  - 最低块分数: {min_score:.2f}")

    # 综合结论
    print("\n【综合结论】")
    should_pass = metrics_strict.is_clear and not is_gray and local_ok
    print(f"  ➜ 该帧{'✅ 应该被使用' if should_pass else '❌ 应该被过滤'}")

    return metrics_strict

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("视频帧质量检测器测试")
    print("="*80)

    # 测试图片路径
    test_images = [
        ("/root/project/vistrat/1.jpg", "问题图片1：部分清晰部分模糊"),
        ("/root/project/vistrat/2.jpg", "问题图片2：灰色模糊"),
        ("/root/project/vistrat/3.jpg", "问题图片3：灰色模糊"),
        ("/root/project/vistrat/4.jpg", "正常图片：清晰可见"),
    ]

    results = {}

    for image_path, description in test_images:
        if not os.path.exists(image_path):
            print(f"\n⚠️ 图片不存在: {image_path}")
            continue

        print(f"\n\n{'#'*80}")
        print(f"# {description}")
        print(f"{'#'*80}")

        metrics = test_image_quality(image_path)
        if metrics:
            results[os.path.basename(image_path)] = metrics

    # 输出汇总
    print("\n\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    print(f"\n{'图片':<15} {'清晰度':<10} {'对比度':<10} {'质量分数':<10} {'结果':<10}")
    print("-" * 80)

    expected_results = {
        "1.jpg": False,  # 应该被过滤
        "2.jpg": False,  # 应该被过滤
        "3.jpg": False,  # 应该被过滤
        "4.jpg": True,   # 应该通过
    }

    all_correct = True
    for img_name, metrics in results.items():
        should_pass = metrics.is_clear
        expected = expected_results.get(img_name, False)
        is_correct = (should_pass == expected)

        status = "✅ 正确" if is_correct else "❌ 错误"
        if not is_correct:
            all_correct = False

        print(
            f"{img_name:<15} "
            f"{metrics.sharpness:<10.2f} "
            f"{metrics.contrast:<10.2f} "
            f"{metrics.quality_score:<10.2f} "
            f"{status:<10}"
        )

    print("=" * 80)

    if all_correct:
        print("\n🎉 所有测试通过！质量检测器工作正常。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查质量检测参数。")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
详细调试帧质量检测
分析1.jpg和4.jpg的块清晰度分布，找到合适的阈值
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_block_quality(image_path: str, grid_size: int = 4):
    """详细分析图片的块质量分布"""
    print(f"\n{'='*80}")
    print(f"分析图片: {image_path}")
    print(f"{'='*80}")

    frame = cv2.imread(image_path)
    if frame is None:
        print(f"❌ 无法读取图片")
        return

    # 转为灰度图
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    block_h = h // grid_size
    block_w = w // grid_size

    print(f"图片尺寸: {w}x{h}")
    print(f"块大小: {block_w}x{block_h}")
    print(f"\n块清晰度分布 (4x4网格):")
    print("-" * 80)

    block_sharpness_values = []
    block_contrast_values = []

    for i in range(grid_size):
        row_values = []
        for j in range(grid_size):
            y1, y2 = i * block_h, (i + 1) * block_h
            x1, x2 = j * block_w, (j + 1) * block_w
            block = gray[y1:y2, x1:x2]

            # 计算清晰度
            laplacian = cv2.Laplacian(block, cv2.CV_64F)
            sharpness = laplacian.var()
            block_sharpness_values.append(sharpness)

            # 计算对比度
            contrast = np.std(block)
            block_contrast_values.append(contrast)

            row_values.append(sharpness)

        # 打印这一行的清晰度值
        print(f"第{i+1}行: {' '.join([f'{v:8.2f}' for v in row_values])}")

    # 统计信息
    max_sharpness = max(block_sharpness_values)
    min_sharpness = min(block_sharpness_values)
    mean_sharpness = np.mean(block_sharpness_values)
    std_sharpness = np.std(block_sharpness_values)

    print("\n" + "-" * 80)
    print(f"清晰度统计:")
    print(f"  最大值: {max_sharpness:.2f}")
    print(f"  最小值: {min_sharpness:.2f}")
    print(f"  平均值: {mean_sharpness:.2f}")
    print(f"  标准差: {std_sharpness:.2f}")
    print(f"  差异倍数: {max_sharpness / (min_sharpness + 1):.2f}倍")

    # 检查低质量块数量（使用不同阈值）
    thresholds = [50, 100, 150, 200, 300]
    print(f"\n低质量块统计 (总共{grid_size*grid_size}块):")
    for threshold in thresholds:
        low_count = sum(1 for v in block_sharpness_values if v < threshold)
        ratio = low_count / len(block_sharpness_values) * 100
        print(f"  阈值{threshold:>3}: {low_count:>2}块 ({ratio:>5.1f}%)")

    return {
        'max': max_sharpness,
        'min': min_sharpness,
        'mean': mean_sharpness,
        'std': std_sharpness,
        'ratio': max_sharpness / (min_sharpness + 1),
        'values': block_sharpness_values
    }

def main():
    print("\n" + "="*80)
    print("详细块质量分析")
    print("="*80)

    # 分析问题图片和正常图片
    images = [
        ("/root/project/vistrat/1.jpg", "问题图片1：部分模糊"),
        ("/root/project/vistrat/4.jpg", "正常图片4：清晰"),
    ]

    results = {}
    for image_path, description in images:
        print(f"\n{'#'*80}")
        print(f"# {description}")
        print(f"{'#'*80}")
        stats = analyze_block_quality(image_path)
        if stats:
            results[description] = stats

    # 对比分析
    if len(results) == 2:
        print("\n\n" + "="*80)
        print("对比分析 - 找到区分阈值")
        print("="*80)

        problem = results["问题图片1：部分模糊"]
        normal = results["正常图片4：清晰"]

        print(f"\n1. 最低块清晰度对比:")
        print(f"   问题图片: {problem['min']:.2f}")
        print(f"   正常图片: {normal['min']:.2f}")
        print(f"   ➜ 建议阈值: {(problem['min'] + normal['min']) / 2:.2f}")

        print(f"\n2. 清晰度差异倍数对比:")
        print(f"   问题图片: {problem['ratio']:.2f}倍")
        print(f"   正常图片: {normal['ratio']:.2f}倍")
        print(f"   ➜ 建议阈值: {(problem['ratio'] + normal['ratio']) / 2:.2f}倍")

        print(f"\n3. 清晰度标准差对比:")
        print(f"   问题图片: {problem['std']:.2f}")
        print(f"   正常图片: {normal['std']:.2f}")

if __name__ == "__main__":
    main()

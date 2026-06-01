import React, { useEffect, useRef, useState, useCallback } from 'react'
import type { DetectionObject, ImageSize, AlertSeverity } from '../../types'

// 严重程度颜色映射（与后端 backend/analysis/services/annotation_service.py 保持一致）
export const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  critical: '#9b59b6', // 紫
  high: '#e74c3c',     // 红
  medium: '#e67e22',   // 橙
  low: '#f1c40f',      // 黄
  info: '#2ecc71'      // 绿
}

export interface BoundingBoxOverlayProps {
  imageUrl: string
  detectionObjects?: DetectionObject[]
  imageSize?: ImageSize
  width?: number | string
  height?: number | string
  showLabels?: boolean
  onClick?: () => void
  alt?: string
  style?: React.CSSProperties
  objectFit?: React.CSSProperties['objectFit']
}

/**
 * 在图片上叠加绘制 bounding box 的组件
 * - 使用 canvas 叠加在 img 之上
 * - 坐标映射：原图像素 -> 显示尺寸
 * - 使用 ResizeObserver 监听容器尺寸变化，自动重绘
 */
const BoundingBoxOverlay: React.FC<BoundingBoxOverlayProps> = ({
  imageUrl,
  detectionObjects,
  imageSize,
  width,
  height,
  showLabels = true,
  onClick,
  alt = '告警图片',
  style,
  objectFit = 'contain'
}) => {
  const imgRef = useRef<HTMLImageElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  // natural 尺寸作为坐标基准的降级方案（当 imageSize 未提供时）
  const [naturalSize, setNaturalSize] = useState<ImageSize | null>(null)

  const hasDetections = Array.isArray(detectionObjects) && detectionObjects.length > 0

  // 绘制 bounding box
  const drawBoxes = useCallback(() => {
    const img = imgRef.current
    const canvas = canvasRef.current
    if (!img || !canvas) return
    if (!hasDetections) return

    // 使用实际渲染尺寸作为 canvas DOM 尺寸，避免模糊
    const displayWidth = img.clientWidth
    const displayHeight = img.clientHeight
    if (displayWidth === 0 || displayHeight === 0) return

    // 坐标基准：优先使用显式传入的 imageSize，否则用 natural 尺寸
    const baseWidth = imageSize?.width ?? naturalSize?.width ?? img.naturalWidth
    const baseHeight = imageSize?.height ?? naturalSize?.height ?? img.naturalHeight
    if (!baseWidth || !baseHeight) return

    // 设置 canvas DOM 尺寸 = 显示尺寸（1:1 像素映射，避免 DPR 缩放模糊）
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(displayWidth * dpr)
    canvas.height = Math.round(displayHeight * dpr)
    canvas.style.width = `${displayWidth}px`
    canvas.style.height = `${displayHeight}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, displayWidth, displayHeight)

    const scaleX = displayWidth / baseWidth
    const scaleY = displayHeight / baseHeight

    detectionObjects!.forEach(obj => {
      const color = SEVERITY_COLORS[obj.severity] ?? SEVERITY_COLORS.info
      const drawX = obj.bbox.x * scaleX
      const drawY = obj.bbox.y * scaleY
      const drawW = obj.bbox.width * scaleX
      const drawH = obj.bbox.height * scaleY

      // 框
      ctx.lineWidth = 2
      ctx.strokeStyle = color
      ctx.strokeRect(drawX, drawY, drawW, drawH)

      if (showLabels) {
        const text = `${obj.label} ${Math.round(obj.confidence * 100)}%`
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
        const metrics = ctx.measureText(text)
        const padX = 4
        const padY = 2
        const labelH = 16
        const labelW = metrics.width + padX * 2
        // 标签优先画在框上方，若越界则画在框内顶部
        let labelY = drawY - labelH
        if (labelY < 0) labelY = drawY
        const labelX = Math.max(0, drawX)

        // 半透明背景（同色 + alpha）
        ctx.fillStyle = hexToRgba(color, 0.85)
        ctx.fillRect(labelX, labelY, labelW, labelH)

        // 白字
        ctx.fillStyle = '#ffffff'
        ctx.textBaseline = 'middle'
        ctx.fillText(text, labelX + padX, labelY + labelH / 2)
      }
    })
  }, [detectionObjects, hasDetections, imageSize, naturalSize, showLabels])

  // img 加载完成：记录 natural 尺寸 + 首次绘制
  const handleImgLoad = () => {
    const img = imgRef.current
    if (!img) return
    setNaturalSize({ width: img.naturalWidth, height: img.naturalHeight })
    // 下一帧绘制，确保布局已完成
    requestAnimationFrame(drawBoxes)
  }

  // ResizeObserver 监听 img 尺寸变化，重绘 canvas
  useEffect(() => {
    const img = imgRef.current
    if (!img || !hasDetections) return
    const observer = new ResizeObserver(() => {
      drawBoxes()
    })
    observer.observe(img)
    return () => {
      observer.disconnect()
    }
  }, [drawBoxes, hasDetections])

  // detectionObjects / imageSize 变化时重绘
  useEffect(() => {
    if (hasDetections) {
      drawBoxes()
    }
  }, [drawBoxes, hasDetections])

  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-block',
        width,
        height,
        cursor: onClick ? 'pointer' : undefined,
        ...style
      }}
      onClick={onClick}
    >
      <img
        ref={imgRef}
        src={imageUrl}
        alt={alt}
        onLoad={handleImgLoad}
        style={{
          width: width ?? '100%',
          height: height ?? '100%',
          objectFit,
          display: 'block'
        }}
      />
      {hasDetections && (
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            pointerEvents: 'none'
          }}
        />
      )}
    </div>
  )
}

// 工具：十六进制色 + alpha -> rgba
function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace('#', '')
  const bigint = parseInt(
    clean.length === 3
      ? clean.split('').map(c => c + c).join('')
      : clean,
    16
  )
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export { BoundingBoxOverlay }
export default BoundingBoxOverlay

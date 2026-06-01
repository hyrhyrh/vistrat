import React from 'react'
import { describe, it, expect, beforeAll, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import BoundingBoxOverlay, { SEVERITY_COLORS } from './BoundingBoxOverlay'
import type { DetectionObject } from '../../types'

// jsdom 不提供 ResizeObserver，补一个空实现
beforeAll(() => {
  if (!(globalThis as any).ResizeObserver) {
    ;(globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
})

const sampleObjects: DetectionObject[] = [
  {
    label: '未戴安全帽工人',
    confidence: 0.87,
    bbox: { x: 10, y: 20, width: 100, height: 200 },
    severity: 'high'
  }
]

describe('BoundingBoxOverlay', () => {
  it('无 detectionObjects 时不渲染 canvas', () => {
    const { container } = render(
      <BoundingBoxOverlay imageUrl="/test.jpg" />
    )
    expect(container.querySelector('canvas')).toBeNull()
    expect(container.querySelector('img')).not.toBeNull()
  })

  it('空数组时也不渲染 canvas', () => {
    const { container } = render(
      <BoundingBoxOverlay imageUrl="/test.jpg" detectionObjects={[]} />
    )
    expect(container.querySelector('canvas')).toBeNull()
  })

  it('有 detectionObjects 时渲染 canvas', () => {
    const { container } = render(
      <BoundingBoxOverlay
        imageUrl="/test.jpg"
        detectionObjects={sampleObjects}
        imageSize={{ width: 1920, height: 1080 }}
      />
    )
    expect(container.querySelector('canvas')).not.toBeNull()
  })

  it('onClick 触发', () => {
    const onClick = vi.fn()
    const { container } = render(
      <BoundingBoxOverlay imageUrl="/test.jpg" onClick={onClick} />
    )
    const wrapper = container.firstChild as HTMLElement
    fireEvent.click(wrapper)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('imageSize 缺省时走 natural size 降级路径（img.onLoad 触发后仍能渲染）', () => {
    const { container } = render(
      <BoundingBoxOverlay
        imageUrl="/test.jpg"
        detectionObjects={sampleObjects}
      />
    )
    const img = container.querySelector('img') as HTMLImageElement
    // jsdom 下 naturalWidth/Height 通常为 0，模拟 load 事件不应抛错
    Object.defineProperty(img, 'naturalWidth', { value: 1920, configurable: true })
    Object.defineProperty(img, 'naturalHeight', { value: 1080, configurable: true })
    fireEvent.load(img)
    expect(container.querySelector('canvas')).not.toBeNull()
  })

  it('SEVERITY_COLORS 与后端约定一致', () => {
    expect(SEVERITY_COLORS.critical).toBe('#9b59b6')
    expect(SEVERITY_COLORS.high).toBe('#e74c3c')
    expect(SEVERITY_COLORS.medium).toBe('#e67e22')
    expect(SEVERITY_COLORS.low).toBe('#f1c40f')
    expect(SEVERITY_COLORS.info).toBe('#2ecc71')
  })
})

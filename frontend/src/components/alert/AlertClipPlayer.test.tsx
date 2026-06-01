import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import AlertClipPlayer from './AlertClipPlayer'

describe('AlertClipPlayer', () => {
  it('clipStatus=pending 时显示生成中占位', () => {
    const { getByTestId, queryByTestId } = render(
      <AlertClipPlayer clipStatus="pending" />
    )
    expect(getByTestId('clip-player-pending')).toBeTruthy()
    expect(queryByTestId('clip-player-video')).toBeNull()
  })

  it('clipStatus=ready + clipUrl 时渲染 <video> 且 src 正确', () => {
    const url = 'https://minio.example/clip/abc.mp4'
    const { getByTestId } = render(
      <AlertClipPlayer clipStatus="ready" clipUrl={url} poster="/p.jpg" />
    )
    const video = getByTestId('clip-player-video') as HTMLVideoElement
    expect(video).toBeTruthy()
    expect(video.tagName.toLowerCase()).toBe('video')
    expect(video.getAttribute('src')).toBe(url)
    expect(video.getAttribute('poster')).toBe('/p.jpg')
  })

  it('clipStatus=failed 时显示错误占位并有重试按钮', () => {
    const { getByTestId, getByText } = render(
      <AlertClipPlayer clipStatus="failed" />
    )
    expect(getByTestId('clip-player-failed')).toBeTruthy()
    expect(getByText('重试')).toBeTruthy()
  })

  it('clipStatus=skipped 时显示"未生成片段"占位', () => {
    const { getByTestId, getByText } = render(
      <AlertClipPlayer clipStatus="skipped" />
    )
    expect(getByTestId('clip-player-skipped')).toBeTruthy()
    expect(getByText('该告警未生成视频片段')).toBeTruthy()
  })

  it('clipStatus=ready 但无 clipUrl 时降级为 pending 视觉', () => {
    const { getByTestId, queryByTestId } = render(
      <AlertClipPlayer clipStatus="ready" />
    )
    expect(getByTestId('clip-player-pending')).toBeTruthy()
    expect(queryByTestId('clip-player-video')).toBeNull()
  })

  it('<video> onError 触发 onPlayError 回调并切换为 failed 视觉', () => {
    const onPlayError = vi.fn()
    const { getByTestId } = render(
      <AlertClipPlayer
        clipStatus="ready"
        clipUrl="https://minio.example/bad.mp4"
        onPlayError={onPlayError}
      />
    )
    const video = getByTestId('clip-player-video')
    fireEvent.error(video)
    expect(onPlayError).toHaveBeenCalledTimes(1)
    // 错误后应重渲染为 failed 占位
    expect(getByTestId('clip-player-failed')).toBeTruthy()
  })
})

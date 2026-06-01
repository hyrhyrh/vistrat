import React from 'react'
import { Modal } from 'antd'
import HLSPlayer from './HLSPlayer'

interface StreamPlayerModalProps {
  open: boolean
  onCancel: () => void
  stream: { name?: string; hls_url?: string | null } | null
}

const StreamPlayerModal: React.FC<StreamPlayerModalProps> = ({ open, onCancel, stream }) => {
  return (
    <Modal
      title={stream?.name || '视频播放'}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
      destroyOnClose
    >
      {stream?.hls_url ? (
        <HLSPlayer url={stream.hls_url} />
      ) : (
        <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
          视频源离线
        </div>
      )}
    </Modal>
  )
}

export default StreamPlayerModal

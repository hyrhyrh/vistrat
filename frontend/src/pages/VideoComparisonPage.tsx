import React, { useState } from 'react';
import { Card, Row, Col, Space, Alert, Statistic, Tag } from 'antd';
import {
  CheckCircleOutlined,
  ThunderboltOutlined,
  RocketOutlined
} from '@ant-design/icons';
import MJPEGPlayer from '@/components/stream/MJPEGPlayer';
import FLVPlayer from '@/components/stream/FLVPlayer';

/**
 * 视频播放方案对比页面
 *
 * 用于验证HTTP-FLV vs MJPEG画质差异
 */
const VideoComparisonPage: React.FC = () => {
  const rtspUrl = 'rtsp://192.168.1.100/ch1';

  // MJPEG URL
  const mjpegUrl = `/api/mjpeg/stream/${encodeURIComponent(rtspUrl)}`;

  // HTTP-FLV URL
  const flvUrl = `/api/flv/stream/${encodeURIComponent(rtspUrl)}`;

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题 */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 28 }}>
              <RocketOutlined style={{ color: '#1890ff', marginRight: 12 }} />
              视频播放方案对比验证
            </h1>
            <p style={{ margin: '8px 0 0 0', color: '#666', fontSize: 16 }}>
              MJPEG vs HTTP-FLV 画质与性能对比测试
            </p>
          </div>

          {/* 对比说明 */}
          <Alert
            message="对比测试说明"
            description={
              <div>
                <p><strong>测试目标：</strong>验证HTTP-FLV方案是否达到VLC级别画质</p>
                <p><strong>测试方法：</strong>同时播放两个视频流，观察以下方面：</p>
                <ul>
                  <li><strong>清晰度</strong>：钢管、栏杆细节是否清晰</li>
                  <li><strong>文字</strong>：时间戳、水印是否锐利</li>
                  <li><strong>运动</strong>：移动物体是否有拖影/模糊</li>
                  <li><strong>稳定性</strong>：是否出现乱码、灰屏</li>
                </ul>
                <p><strong>预期结果：</strong>HTTP-FLV画质应与VLC完全一致（⭐⭐⭐⭐⭐），MJPEG可能出现模糊（⭐⭐）</p>
              </div>
            }
            type="info"
            showIcon
          />

          {/* 技术方案对比 */}
          <Row gutter={16}>
            <Col span={12}>
              <Card
                title={
                  <Space>
                    <Tag color="orange">旧方案</Tag>
                    <span>MJPEG</span>
                  </Space>
                }
                size="small"
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Statistic
                    title="架构"
                    value="OpenCV解码 + JPEG重编码"
                    valueStyle={{ fontSize: 14 }}
                  />
                  <Statistic
                    title="质量损失"
                    value="4重损失"
                    valueStyle={{ fontSize: 14, color: '#ff4d4f' }}
                    suffix="（PPS错误 + JPEG压缩 + 降帧 + 过滤）"
                  />
                  <Statistic
                    title="帧率"
                    value="15 FPS"
                    valueStyle={{ fontSize: 14 }}
                  />
                  <Statistic
                    title="预期画质"
                    value="⭐⭐"
                    valueStyle={{ fontSize: 14 }}
                  />
                </Space>
              </Card>
            </Col>

            <Col span={12}>
              <Card
                title={
                  <Space>
                    <Tag color="green">新方案</Tag>
                    <span>HTTP-FLV</span>
                  </Space>
                }
                size="small"
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Statistic
                    title="架构"
                    value="FFmpeg封装 + MSE解码"
                    valueStyle={{ fontSize: 14 }}
                  />
                  <Statistic
                    title="质量损失"
                    value="零损失"
                    valueStyle={{ fontSize: 14, color: '#52c41a' }}
                    prefix={<CheckCircleOutlined />}
                    suffix="（原生H.264直传）"
                  />
                  <Statistic
                    title="帧率"
                    value="25 FPS"
                    valueStyle={{ fontSize: 14, color: '#52c41a' }}
                    prefix={<ThunderboltOutlined />}
                  />
                  <Statistic
                    title="预期画质"
                    value="⭐⭐⭐⭐⭐"
                    valueStyle={{ fontSize: 14, color: '#52c41a' }}
                  />
                </Space>
              </Card>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* 并排对比播放器 */}
      <Row gutter={24}>
        {/* MJPEG播放器 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <Tag color="orange">旧方案</Tag>
                <span>MJPEG播放器</span>
              </Space>
            }
            extra={<Tag color="warning">可能出现模糊</Tag>}
          >
            {/* 注意：需要确保MJPEGPlayer组件存在 */}
            {/* 如果不存在，可以直接使用img标签 */}
            <img
              src={mjpegUrl}
              style={{
                width: '100%',
                height: 600,
                backgroundColor: '#000',
                display: 'block',
                objectFit: 'contain'
              }}
              alt="MJPEG Stream"
            />
            <div style={{ marginTop: 16, padding: '12px', backgroundColor: '#fff7e6', borderRadius: 4 }}>
              <p style={{ margin: 0, fontSize: 12, color: '#d46b08' }}>
                <strong>观察要点：</strong>可能出现局部模糊、JPEG压缩伪影、细节丢失
              </p>
            </div>
          </Card>
        </Col>

        {/* HTTP-FLV播放器 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <Tag color="green">新方案</Tag>
                <span>HTTP-FLV播放器</span>
              </Space>
            }
            extra={
              <Space>
                <Tag color="success" icon={<CheckCircleOutlined />}>无损传输</Tag>
                <Tag color="processing">原生H.264</Tag>
              </Space>
            }
          >
            <FLVPlayer
              url={flvUrl}
              title=""
              height={600}
              autoPlay={false}
            />
            <div style={{ marginTop: 16, padding: '12px', backgroundColor: '#f6ffed', borderRadius: 4 }}>
              <p style={{ margin: 0, fontSize: 12, color: '#52c41a' }}>
                <strong>观察要点：</strong>画质应与VLC完全一致，清晰锐利，无压缩伪影
              </p>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 验收标准 */}
      <Card style={{ marginTop: 24 }} title="验收标准">
        <Row gutter={16}>
          <Col span={8}>
            <Card size="small" title="画质对比">
              <ul style={{ paddingLeft: 20, margin: 0 }}>
                <li>HTTP-FLV应无模糊现象</li>
                <li>钢管、栏杆边缘锐利</li>
                <li>文字清晰可辨</li>
                <li>无块状JPEG伪影</li>
              </ul>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="稳定性对比">
              <ul style={{ paddingLeft: 20, margin: 0 }}>
                <li>HTTP-FLV无乱码/灰屏</li>
                <li>连续播放无卡顿</li>
                <li>色彩还原准确</li>
                <li>帧率稳定流畅</li>
              </ul>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="性能对比">
              <ul style={{ paddingLeft: 20, margin: 0 }}>
                <li>HTTP-FLV延迟1-3秒</li>
                <li>网络速度稳定</li>
                <li>丢帧率 &lt; 1%</li>
                <li>浏览器CPU占用正常</li>
              </ul>
            </Card>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default VideoComparisonPage;

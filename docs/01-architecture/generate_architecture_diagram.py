#!/usr/bin/env python3
"""
AI智能视频监控预警系统架构图生成脚本
使用matplotlib和自定义绘图函数生成分层架构图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_architecture_diagram():
    """创建系统架构图"""
    
    # 创建图形和轴
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # 定义颜色方案
    colors = {
        'frontend': '#a8edea',
        'presentation': '#ffecd2', 
        'business': '#a8edea',
        'service': '#d299c2',
        'data': '#89f7fe',
        'infrastructure': '#fbc2eb',
        'side': '#ff9a9e',
        'border': '#4CAF50'
    }
    
    # 标题
    title_box = FancyBboxPatch(
        (0.5, 11), 9, 0.8,
        boxstyle="round,pad=0.1",
        facecolor=colors['business'],
        edgecolor=colors['border'],
        linewidth=2
    )
    ax.add_patch(title_box)
    ax.text(5, 11.4, 'AI智能视频监控预警系统 - 企业级架构图', 
            ha='center', va='center', fontsize=20, fontweight='bold')
    
    # 层级定义
    layers = [
        {
            'name': '前端UI',
            'y': 9.5,
            'height': 1.2,
            'color': colors['frontend'],
            'components': [
                'React 18\n前端框架',
                'TypeScript 5.0\n类型检查', 
                'Ant Design 5.0\nUI组件库',
                'Vite 4.0\n构建工具',
                'WebSocket\n实时通信'
            ]
        },
        {
            'name': '展示层', 
            'y': 8,
            'height': 1.2,
            'color': colors['presentation'],
            'components': [
                '视频监控界面\n实时画面展示',
                '告警管理中心\n异常事件处理',
                '分析结果查询\n历史数据检索',
                '提示词管理\nAI模板配置',
                '系统监控\n性能指标'
            ]
        },
        {
            'name': '业务层',
            'y': 6.5, 
            'height': 1.2,
            'color': colors['business'],
            'components': [
                '视频管理\n文件上传处理',
                '流媒体服务\nRTSP/MJPEG',
                'AI分析引擎\n智能检测',
                '告警服务\n实时推送', 
                '用户认证\n权限管理',
                'API网关\nFastAPI'
            ]
        },
        {
            'name': '服务层',
            'y': 5,
            'height': 1.2, 
            'color': colors['service'],
            'components': [
                '视频处理器\nOpenCV 4.8+',
                'AI模型选择器\n智能调度',
                '存储服务\n文件管理',
                '缓存服务\nRedis缓存',
                '消息队列\n异步处理',
                '健康检查\n监控服务'
            ]
        },
        {
            'name': '数据层',
            'y': 3.5,
            'height': 1.2,
            'color': colors['data'], 
            'components': [
                'PostgreSQL 16\n主数据库',
                'Elasticsearch 8.11\n搜索引擎',
                'MinIO 对象存储\n文件存储',
                'Redis 7\n缓存数据库',
                '本地文件系统\n临时存储'
            ]
        },
        {
            'name': '运行环境',
            'y': 2,
            'height': 1.2,
            'color': colors['infrastructure'],
            'components': [
                'Docker容器\n服务隔离',
                'Docker Compose\n服务编排', 
                'Nginx反向代理\n负载均衡',
                'Linux服务器\n运行环境',
                '云平台\n部署选择'
            ]
        }
    ]
    
    # 绘制层级
    for layer in layers:
        # 层级标签背景
        label_box = FancyBboxPatch(
            (0.2, layer['y']), 1.2, layer['height'],
            boxstyle="round,pad=0.05",
            facecolor='#f8f9fa',
            edgecolor='#e9ecef',
            linewidth=1
        )
        ax.add_patch(label_box)
        
        # 层级标签文字
        ax.text(0.8, layer['y'] + layer['height']/2, layer['name'], 
                ha='center', va='center', fontsize=14, fontweight='bold')
        
        # 组件框
        component_width = 1.5
        component_spacing = 0.1
        start_x = 1.6
        
        for i, component in enumerate(layer['components']):
            x = start_x + i * (component_width + component_spacing)
            
            # 组件背景框
            comp_box = FancyBboxPatch(
                (x, layer['y'] + 0.1), component_width, layer['height'] - 0.2,
                boxstyle="round,pad=0.05",
                facecolor=layer['color'],
                edgecolor=colors['border'],
                linewidth=1.5
            )
            ax.add_patch(comp_box)
            
            # 组件文字
            lines = component.split('\n')
            if len(lines) == 2:
                ax.text(x + component_width/2, layer['y'] + layer['height']/2 + 0.15, 
                        lines[0], ha='center', va='center', fontsize=11, fontweight='bold')
                ax.text(x + component_width/2, layer['y'] + layer['height']/2 - 0.15,
                        lines[1], ha='center', va='center', fontsize=9, color='#666')
            else:
                ax.text(x + component_width/2, layer['y'] + layer['height']/2,
                        component, ha='center', va='center', fontsize=11, fontweight='bold')
        
        # 绘制向下箭头（最后一层除外）
        if layer != layers[-1]:
            arrow_x = 5
            arrow_y = layer['y'] - 0.3
            ax.annotate('', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_y + 0.4),
                        arrowprops=dict(arrowstyle='->', lw=2, color=colors['border']))
    
    # 侧边组件
    side_components = ['权限控制', '日志记录', '监控告警']
    side_x = 8.8
    
    for i, comp in enumerate(side_components):
        side_y = 9 - i * 3
        side_box = FancyBboxPatch(
            (side_x, side_y), 0.8, 2,
            boxstyle="round,pad=0.05", 
            facecolor=colors['side'],
            edgecolor='#e91e63',
            linewidth=1.5
        )
        ax.add_patch(side_box)
        ax.text(side_x + 0.4, side_y + 1, comp, 
                ha='center', va='center', fontsize=11, fontweight='bold',
                rotation=90)
    
    # 添加技术栈说明
    tech_stack_text = """
    核心技术栈：
    • 前端：React 18 + TypeScript 5.0 + Ant Design 5.0 + Vite 4.0
    • 后端：FastAPI 0.115+ + Python 3.9+ + OpenCV 4.8+ + Uvicorn
    • AI模型：通义千问VL-Max + Moonshot-v1 + 向量数据库RAG
    • 数据存储：PostgreSQL 16 + Elasticsearch 8.11 + Redis 7 + MinIO
    • 部署运维：Docker + Docker Compose + Nginx + Linux + 云平台
    • 通信协议：HTTP/HTTPS + WebSocket + MJPEG + RTSP
    """
    
    ax.text(0.5, 0.8, tech_stack_text, fontsize=10, va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='#f8f9fa', alpha=0.8))
    
    # 设置图表属性
    plt.tight_layout()
    plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    
    return fig

def save_diagram(fig, filename='architecture_diagram'):
    """保存架构图为多种格式"""
    formats = ['png', 'svg', 'pdf']
    
    for fmt in formats:
        filepath = f'./docs/{filename}.{fmt}'
        fig.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"架构图已保存: {filepath}")

if __name__ == "__main__":
    print("正在生成AI智能视频监控预警系统架构图...")
    
    # 创建架构图
    fig = create_architecture_diagram()
    
    # 保存图表
    save_diagram(fig)
    
    # 显示图表
    plt.show()
    
    print("架构图生成完成！")
"""
提示词加载器
负责从配置或模板文件加载提示词
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from config.settings import PathConfig


logger = logging.getLogger(__name__)


class PromptLoader:
    """提示词加载器"""
    
    def __init__(self):
        self._templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载提示词模板"""
        try:
            if PathConfig.TEMPLATES_FILE.exists():
                with open(PathConfig.TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                    
                # 按类型组织模板
                for template in templates:
                    template_type = template.get('type')
                    if template.get('is_active', False):
                        self._templates[template_type] = template['content']
                        
            # 设置默认模板
            self._set_default_templates()
            
            logger.info(f"提示词模板加载完成: {len(self._templates)} 个")
            
        except Exception as e:
            logger.error(f"提示词模板加载失败: {e}")
            self._set_default_templates()
    
    def _set_default_templates(self):
        """设置默认提示词模板"""
        if 'video' not in self._templates:
            self._templates['video'] = """你是一个安全监控人员，正在分析最新的监控画面，请把你看到的行为和视频内容描述出来，从开始到结束的内容请都描述出来。
输出简洁一点，不要输出第一张画面、第二章画面，只需简洁的描述即可。"""

        if 'detect' not in self._templates:
            self._templates['detect'] = """[系统角色] 你是监控人员，正在分析最新的监控文本，并决定现在是否需要将现在的内容告知同事或者领导。

[历史上下文]
{Recursive_summary}

[当前时段] {current_time}
最新视频段描述：{latest_description}

请阅读上面的视频内容，判断当前视频是否存在以下异常情况，注意是当前的视频内容。
[分析要求]
异常情况1：
   - 人员聚集冲突
   - 异常物品出现
   - 违反安全规程操作
   - 自然灾害
   - 潜在危害
   - 违反交通规则（行人、摩托车、汽车等不遵守交规）
异常情况2
   - 宠物逃跑
   - 东西被盗或被人移动
   - 人员跌倒、摔倒等。
   - 小孩爬到高处
   等常识类异常情况

下面是输出格式要求：
如果没有明显异常情况，则不需要提醒或者预警，那么请直接输出：无异常状况。
如果描述中存在上述异常行为则输出：请注意，出现了xx的情况，需要即时处理或知晓。（xx为具体的异常情况，需要具体描述）
请出现任何异常情况都需要提醒。
输出简洁一点，不要过于繁琐，需要简洁的描述即可。"""

        if 'summary' not in self._templates:
            self._templates['summary'] = """[系统角色] 您将接收到一系列按时间顺序排列的监控视频描述。请根据以下要求，将这些描述内容整合为一篇连贯的总结：

[历史上下文]
{histroy}

只需要逐步描述开始发生了什么，中间发生了什么、最后发生了什么。
请在整合信息后，直接输出内容，请输出简洁一点，不要超过200字。"""

    def get_video_prompt(self) -> str:
        """获取视频描述提示词"""
        return self._templates.get('video', '')
    
    def get_detect_prompt(self) -> str:
        """获取异常检测提示词"""
        return self._templates.get('detect', '')
    
    def get_summary_prompt(self) -> str:
        """获取历史总结提示词"""
        return self._templates.get('summary', '')
    
    def reload_templates(self):
        """重新加载提示词模板"""
        self._templates.clear()
        self._load_templates()
        logger.info("提示词模板已重新加载")


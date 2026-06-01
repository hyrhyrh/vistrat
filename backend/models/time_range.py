"""
时间范围数据模型
用于封装视频分析中的时间戳参数，减少数据泥团问题
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class TimeRange:
    """时间范围数据类"""
    start_time: str
    end_time: str
    
    @classmethod
    def from_timestamps(cls, timestamps: Tuple[str, str]) -> 'TimeRange':
        """从时间戳元组创建TimeRange实例"""
        return cls(start_time=timestamps[0], end_time=timestamps[1])
    
    def to_timestamps(self) -> Tuple[str, str]:
        """转换为时间戳元组"""
        return (self.start_time, self.end_time)
    
    def format_chinese(self) -> str:
        """格式化为中文时间描述"""
        try:
            start_parts = self.start_time.split('-')
            end_parts = self.end_time.split('-')
            
            if len(start_parts) >= 6 and len(end_parts) >= 6:
                year, month, day, hour, minute, second = start_parts[:6]
                end_hour, end_minute, end_second = end_parts[3:6]
                
                am_pm = "上午" if int(hour) < 12 else "下午"
                hour_12 = hour if hour == '12' else str(int(hour) % 12)
                
                return (f"{year}年{int(month)}月{int(day)}日{am_pm}{hour_12}点"
                       f"（{hour}时）{int(minute)}分{int(second)}秒 - "
                       f"{int(end_hour)}时{int(end_minute)}分{int(end_second)}秒")
        except Exception:
            pass
        
        return f"{self.start_time} - {self.end_time}"
    
    def duration_seconds(self) -> Optional[float]:
        """计算时间范围的持续时间（秒）"""
        try:
            start_dt = datetime.strptime(self.start_time, "%Y-%m-%d-%H-%M-%S")
            end_dt = datetime.strptime(self.end_time, "%Y-%m-%d-%H-%M-%S")
            return (end_dt - start_dt).total_seconds()
        except ValueError:
            return None
    
    def __str__(self) -> str:
        return f"{self.start_time} - {self.end_time}"
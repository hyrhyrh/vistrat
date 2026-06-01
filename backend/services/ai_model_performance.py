"""
AI模型性能监控和统计服务
专门负责模型性能数据的收集、分析和持久化
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

from models.ai_model_types import ModelType, ModelPerformance, PromptCategory
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


class ModelPerformanceTracker:
    """模型性能跟踪器"""
    
    def __init__(self, data_file: str = "data/model_performance.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.performance_data: Dict[ModelType, ModelPerformance] = {}
        self._load_performance_data()
    
    def _load_performance_data(self):
        """从文件加载性能数据"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for model_type_str, perf_data in data.items():
                    model_type = ModelType(model_type_str)
                    performance = ModelPerformance(
                        model_type=model_type,
                        success_count=perf_data.get('success_count', 0),
                        total_count=perf_data.get('total_count', 0),
                        avg_response_time=perf_data.get('avg_response_time', 0.0),
                        avg_confidence=perf_data.get('avg_confidence', 0.0),
                        last_updated=perf_data.get('last_updated')
                    )
                    
                    # 恢复分类性能数据
                    category_perf = perf_data.get('category_performance', {})
                    for cat_str, score in category_perf.items():
                        try:
                            category = PromptCategory(cat_str)
                            performance.category_performance[category] = score
                        except ValueError:
                            continue
                    
                    self.performance_data[model_type] = performance
                
                logger.info(f"加载了 {len(self.performance_data)} 个模型的性能数据")
        except Exception as e:
            logger.error(f"加载性能数据失败: {e}")
    
    def _save_performance_data(self):
        """保存性能数据到文件"""
        try:
            data = {}
            for model_type, performance in self.performance_data.items():
                category_perf = {
                    cat.value: score 
                    for cat, score in performance.category_performance.items()
                }
                
                data[model_type.value] = {
                    'success_count': performance.success_count,
                    'total_count': performance.total_count,
                    'avg_response_time': performance.avg_response_time,
                    'avg_confidence': performance.avg_confidence,
                    'category_performance': category_perf,
                    'last_updated': performance.last_updated
                }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug("性能数据已保存")
        except Exception as e:
            logger.error(f"保存性能数据失败: {e}")
    
    def record_model_usage(self, model_type: ModelType, success: bool, 
                          response_time: float, confidence: float, 
                          category: PromptCategory):
        """记录模型使用情况"""
        if model_type not in self.performance_data:
            self.performance_data[model_type] = ModelPerformance(model_type=model_type)
        
        performance = self.performance_data[model_type]
        performance.update_performance(success, response_time, confidence, category)
        
        # 异步保存数据
        self._save_performance_data()
        
        logger.debug(f"记录模型 {model_type.value} 使用情况: 成功={success}, "
                    f"响应时间={response_time:.2f}s, 置信度={confidence:.2f}")
    
    def get_model_performance(self, model_type: ModelType) -> Optional[ModelPerformance]:
        """获取模型性能数据"""
        return self.performance_data.get(model_type)
    
    def get_best_model_for_category(self, category: PromptCategory) -> Optional[ModelType]:
        """获取某类别下性能最佳的模型"""
        best_model = None
        best_score = 0.0
        
        for model_type, performance in self.performance_data.items():
            if category in performance.category_performance:
                score = performance.category_performance[category]
                # 结合成功率和分类性能
                weighted_score = score * performance.success_rate
                
                if weighted_score > best_score:
                    best_score = weighted_score
                    best_model = model_type
        
        return best_model
    
    def get_performance_summary(self) -> Dict:
        """获取性能总结"""
        summary = {
            'total_models': len(self.performance_data),
            'models': {}
        }
        
        for model_type, performance in self.performance_data.items():
            summary['models'][model_type.value] = {
                'success_rate': performance.success_rate,
                'avg_response_time': performance.avg_response_time,
                'avg_confidence': performance.avg_confidence,
                'total_requests': performance.total_count,
                'last_updated': performance.last_updated
            }
        
        return summary
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧的性能数据"""
        cutoff_date = now() - timedelta(days=days)
        
        for model_type, performance in list(self.performance_data.items()):
            if performance.last_updated:
                try:
                    last_update = datetime.fromisoformat(performance.last_updated.replace('Z', '+00:00'))
                    if last_update < cutoff_date:
                        # 重置但保留基础结构
                        performance.success_count = 0
                        performance.total_count = 0
                        performance.avg_response_time = 0.0
                        performance.avg_confidence = 0.0
                        performance.category_performance.clear()
                        performance.last_updated = None
                        logger.info(f"重置了过期的性能数据: {model_type.value}")
                except Exception as e:
                    logger.warning(f"处理过期数据时出错: {e}")
        
        self._save_performance_data()
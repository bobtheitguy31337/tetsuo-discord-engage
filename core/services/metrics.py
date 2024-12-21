from typing import Dict

class MetricsService:
    """Core service for tracking metrics across platforms"""
    def __init__(self):
        self.previous_metrics: Dict[str, float] = {}
        
    def get_trend_indicator(self, metric: str, current: float) -> str:
        """Get trend indicator for any metric"""
        previous = self.previous_metrics.get(metric)
        if previous is None:
            return "➖"
        elif current > previous:
            return "↗️"
        elif current < previous:
            return "↘️"
        else:
            return "➖"
            
    def update_metric(self, metric: str, value: float):
        """Update stored metric value"""
        self.previous_metrics[metric] = value
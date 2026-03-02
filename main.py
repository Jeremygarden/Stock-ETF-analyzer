"""
ETF轮动系统主程序
美股行业ETF + 新兴市场 + 期权对冲型ETF 轮动策略
"""

import os
import sys
from datetime import datetime
import json

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_data import ETFDataFetcher
from rotator import ETFRotator
from notifier import SignalNotifier
from config import ETF_CONFIG, STRATEGY_CONFIG


class ETFRotationSystem:
    def __init__(self):
        self.data_fetcher = ETFDataFetcher()
        self.rotator = ETFRotator()
        self.notifier = SignalNotifier()
        
    def run(self):
        """执行完整的轮动分析流程"""
        print(f"\n{'='*50}")
        print(f"ETF轮动系统启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")
        
        # 1. 获取ETF数据
        print("[1/4] 正在获取ETF数据...")
        etf_data = self.data_fetcher.fetch_all_etfs()
        
        # 2. 计算动量信号
        print("[2/4] 正在计算动量信号...")
        signals = self.rotator.calculate_signals(etf_data)
        
        # 3. 生成轮动建议
        print("[3/4] 正在生成轮动建议...")
        recommendations = self.rotator.generate_recommendations(signals)
        
        # 4. 输出信号
        print("[4/4] 正在输出信号...")
        self.notifier.send_signals(recommendations)
        
        # 保存结果到文件
        self._save_results(etf_data, signals, recommendations)
        
        print(f"\n✅ 轮动分析完成!")
        return recommendations
    
    def _save_results(self, etf_data, signals, recommendations):
        """保存结果到JSON文件"""
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存完整数据
        result = {
            'timestamp': datetime.now().isoformat(),
            'etf_data': etf_data,
            'signals': signals,
            'recommendations': recommendations
        }
        
        with open(f'{output_dir}/signals_{timestamp}.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        # 保存最新结果链接
        with open(f'{output_dir}/latest.json', 'w') as f:
            json.dump(result, f, indent=2)


def main():
    system = ETFRotationSystem()
    system.run()


if __name__ == '__main__':
    main()

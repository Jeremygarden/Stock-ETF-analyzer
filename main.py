"""
ETF轮动系统主程序 (v2.0)
- 基础轮动模式
- 高级多因子模式
- 回测模式
"""

import os
import sys
from datetime import datetime
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_data import ETFDataFetcher
from advanced_rotator import AdvancedETFRotator
from backtest import ETFBacktester
from notifier import SignalNotifier
from config import ETF_CONFIG


def run_rotation(mode='advanced'):
    """运行轮动分析"""
    print(f"\n{'='*60}")
    print(f"ETF轮动系统 v2.0 - {mode}模式")
    print(f"{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 获取ETF数据
    print("[1/4] 正在获取ETF数据...")
    fetcher = ETFDataFetcher()
    etf_data = fetcher.fetch_all_etfs()
    
    # 获取历史数据用于相关性计算
    all_tickers = list(etf_data.keys())
    price_history = fetcher.fetch_price_history(all_tickers, days=90)
    
    # 2. 计算信号
    print("[2/4] 正在计算多因子信号...")
    rotator = AdvancedETFRotator()
    signals = rotator.calculate_advanced_signals(etf_data, price_history)
    
    # 3. 生成建议
    print("[3/4] 正在生成轮动建议...")
    recommendations = rotator.generate_advanced_recommendations(signals, etf_data, price_history)
    
    # 4. 输出信号
    print("[4/4] 正在输出信号...")
    notifier = SignalNotifier()
    notifier.send_signals_v2(recommendations)
    
    # 保存结果
    save_results(recommendations, 'rotation')
    
    print(f"\n✅ 轮动分析完成!")
    return recommendations


def run_backtest(etf_pool=None, strategy='advanced'):
    """运行回测"""
    if etf_pool is None:
        from config import ETF_CONFIG
        all_etfs = {}
        all_etfs.update(ETF_CONFIG['sector_etfs'])
        all_etfs.update(ETF_CONFIG['emerging_etfs'])
        all_etfs.update(ETF_CONFIG['option_income_etfs'])
        etf_pool = list(all_etfs.keys())
    
    print(f"\n{'='*60}")
    print(f"ETF回测模式")
    print(f"{'='*60}")
    
    backtester = ETFBacktester(initial_capital=100000)
    
    # 对比所有策略
    results = backtester.compare_strategies(
        etf_pool,
        start_date=datetime(2024, 1, 1),
        end_date=datetime.now()
    )
    
    # 保存结果
    backtester.save_results('output/backtest_results.json')
    
    return results


def save_results(data, prefix='signals'):
    """保存结果到文件"""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(f'{output_dir}/{prefix}_{timestamp}.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    with open(f'{output_dir}/latest.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF轮动系统')
    parser.add_argument('--mode', choices=['rotation', 'backtest', 'both'], 
                       default='rotation', help='运行模式')
    parser.add_argument('--strategy', default='advanced', 
                       help='回测策略 (momentum/dual_momentum/risk_parity/advanced)')
    
    args = parser.parse_args()
    
    if args.mode in ['rotation', 'both']:
        run_rotation()
    
    if args.mode in ['backtest', 'both']:
        run_backtest(strategy=args.strategy)


if __name__ == '__main__':
    main()

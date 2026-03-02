"""
ETF轮动系统主程序 (v3.0)
专业版 - 多因子模型 + 专业数据源
"""

import os
import sys
from datetime import datetime
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_source import ETFDataSource, FactorModel
from factor_analysis import FactorAnalyzer, generate_factor_report
from advanced_rotator import AdvancedETFRotator
from backtest import ETFBacktester
from backtest_metrics import AdvancedBacktestMetrics, print_advanced_report
from notifier import SignalNotifier
from config import ETF_CONFIG


def run_professional_rotation():
    """运行专业版轮动分析"""
    print(f"\n{'='*70}")
    print(f"ETF轮动系统 v3.0 - 专业因子模型版")
    print(f"{'='*70}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 准备ETF列表
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    all_etfs.update(ETF_CONFIG['benchmark_etfs'])
    etf_tickers = list(all_etfs.keys())
    
    # 2. 获取专业数据
    print("[1/5] 正在获取专业数据...")
    ds = ETFDataSource()
    etf_data = ds.fetch_market_data(etf_tickers)
    
    # 3. 计算因子
    print("[2/5] 正在计算因子...")
    fm = FactorModel()
    factor_matrix = fm.calculate_factors(etf_data)
    
    # 4. 因子分析
    print("[3/5] 正在分析因子有效性...")
    fa = FactorAnalyzer()
    
    # 计算因子相关性矩阵
    factor_corr = fa.factor_correlation_matrix(factor_matrix)
    print(f"\n因子相关性:\n{factor_corr.round(2)}")
    
    # 5. 生成信号
    print("[4/5] 正在生成轮动信号...")
    rotator = AdvancedETFRotator()
    
    # 转换数据格式
    simple_data = {}
    for ticker, data in etf_data.items():
        if data.get('success'):
            pf = data.get('price_factors', {})
            simple_data[ticker] = {
                'ticker': ticker,
                'name': all_etfs.get(ticker, {}).get('name', ''),
                'category': all_etfs.get(ticker, {}).get('category', ''),
                'current_price': list(pf.values())[0] if pf else 0,
                'return_5d': pf.get('momentum_5d', 0),
                'return_20d': pf.get('momentum_20d', 0),
                'return_60d': pf.get('momentum_60d', 0),
                'volatility_20d': pf.get('volatility_20d', 0),
                'volume_change': pf.get('volume_ratio', 0),
            }
    
    signals = rotator.calculate_advanced_signals(simple_data)
    recommendations = rotator.generate_advanced_recommendations(signals, simple_data)
    
    # 6. 输出信号
    print("[5/5] 正在输出信号...")
    notifier = SignalNotifier()
    notifier.send_signals_v2(recommendations)
    
    # 保存结果
    save_results({
        'etf_data': etf_data,
        'factor_matrix': factor_matrix.to_dict(),
        'factor_correlations': factor_corr.to_dict(),
        'recommendations': recommendations
    }, 'professional')
    
    print(f"\n✅ 专业分析完成!")
    return recommendations


def run_factor_analysis():
    """运行因子有效性分析"""
    print(f"\n{'='*70}")
    print(f"因子有效性分析")
    print(f"{'='*70}\n")
    
    # 获取数据
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    etf_tickers = list(all_etfs.keys())
    
    ds = ETFDataSource()
    etf_data = ds.fetch_market_data(etf_tickers)
    
    # 计算因子
    fm = FactorModel()
    factor_matrix = fm.calculate_factors(etf_data)
    
    # 因子分析
    fa = FactorAnalyzer()
    
    # 因子相关性
    print("\n📊 因子相关性矩阵:")
    corr = fa.factor_correlation_matrix(factor_matrix)
    print(corr.round(3))
    
    # 正交化
    print("\n🔧 因子正交化...")
    orthogonalized = fa.factor_neutralization(factor_matrix)
    print("因子正交化完成")
    
    # 保存分析结果
    save_results({
        'factor_matrix': factor_matrix.to_dict(),
        'factor_correlations': corr.to_dict(),
        'orthogonalized': orthogonalized.to_dict()
    }, 'factor_analysis')
    
    return factor_matrix


def save_results(data, prefix='signals'):
    """保存结果"""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 转换numpy类型
    def convert(obj):
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif pd.api.is_categorical_dtype(obj):
            return obj.tolist()
        return obj
    
    import numpy as np
    import pandas as pd
    
    with open(f'{output_dir}/{prefix}_{timestamp}.json', 'w') as f:
        json.dump(data, f, indent=2, default=convert)
    
    with open(f'{output_dir}/latest.json', 'w') as f:
        json.dump(data, f, indent=2, default=convert)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF轮动系统 v3.0')
    parser.add_argument('--mode', 
                       choices=['rotation', 'factor', 'backtest', 'backtest-advanced'], 
                       default='rotation', 
                       help='运行模式')
    parser.add_argument('--strategy', 
                       default='dual_momentum', 
                       help='回测策略')
    
    args = parser.parse_args()
    
    if args.mode == 'rotation':
        run_professional_rotation()
    elif args.mode == 'factor':
        run_factor_analysis()
    elif args.mode == 'backtest':
        run_backtest(strategy=args.strategy)
    elif args.mode == 'backtest-advanced':
        run_advanced_backtest(strategy=args.strategy)


if __name__ == '__main__':
    main()

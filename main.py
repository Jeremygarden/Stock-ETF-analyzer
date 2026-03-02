"""
ETF轮动系统主程序 (v3.1)
24因子专业版
"""

import os
import sys
from datetime import datetime
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from twenty_four_factors import TwentyFourFactorModel
from backtest import ETFBacktester
from backtest_metrics import AdvancedBacktestMetrics, print_advanced_report
from notifier import SignalNotifier
from config import ETF_CONFIG


def run_24factor_analysis():
    """运行24因子分析"""
    print(f"\n{'='*70}")
    print(f"ETF轮动系统 v3.1 - 24因子专业版")
    print(f"{'='*70}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 准备ETF列表
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    all_etfs.update(ETF_CONFIG['benchmark_etfs'])
    etf_tickers = list(all_etfs.keys())
    
    # 2. 计算24因子
    print("[1/3] 正在计算24个量化因子...")
    model = TwentyFourFactorModel()
    factor_matrix = model.calculate_factor_matrix(etf_tickers)
    
    # 3. 数据处理
    print("[2/3] 正在处理因子数据...")
    
    # 去除无效因子列
    valid_cols = [c for c in factor_matrix.columns 
                 if c not in ['ticker', 'error', 'success'] and factor_matrix[c].notna().sum() > 5]
    factor_matrix = factor_matrix[valid_cols]
    
    # 去极值
    factor_matrix = model.winsorize_factors(factor_matrix)
    
    # 标准化
    std_matrix = model.standardize_factors(factor_matrix)
    
    # 生成综合得分
    composite_scores = model.generate_composite_score(factor_matrix)
    
    # 4. 输出结果
    print("[3/3] 正在输出信号...\n")
    
    # 因子分类汇总
    print("="*70)
    print("📊 24因子分析报告")
    print("="*70)
    
    # 因子统计
    print(f"\n📈 因子覆盖: {len(valid_cols)}/{len(model.factor_names)}")
    
    # 动量因子
    momentum_cols = [c for c in valid_cols if 'momentum' in c and 'vol' not in c]
    if momentum_cols:
        print(f"\n🔥 动量因子 ({len(momentum_cols)}个):")
        for c in momentum_cols:
            valid_data = factor_matrix[c].dropna()
            if len(valid_data) > 0:
                best_etf = valid_data.idxmax()
                best_val = valid_data.max()
                print(f"   {c}: {best_etf} ({best_val:+.1f}%)")
    
    # 价值因子
    value_cols = [c for c in valid_cols if c in ['dividend_yield', 'earnings_yield', 'book_value', 'cashflow']]
    if value_cols:
        print(f"\n💰 价值因子 ({len(value_cols)}个):")
        for c in value_cols:
            valid_data = factor_matrix[c].dropna()
            if len(valid_data) > 0:
                best_etf = valid_data.idxmax()
                best_val = valid_data.max()
                print(f"   {c}: {best_etf} ({best_val:.2f})")
    
    # 质量因子
    quality_cols = [c for c in valid_cols if c in ['roe', 'roa', 'gross_margin', 'net_margin', 'asset_turnover']]
    if quality_cols:
        print(f"\n✅ 质量因子 ({len(quality_cols)}个):")
        for c in quality_cols:
            valid_data = factor_matrix[c].dropna()
            if len(valid_data) > 0:
                best_etf = valid_data.idxmax()
                best_val = valid_data.max()
                print(f"   {c}: {best_etf} ({best_val:.1f}%)")
    
    # 波动率因子
    vol_cols = [c for c in valid_cols if 'volatil' in c]
    if vol_cols:
        print(f"\n📉 低波动因子 ({len(vol_cols)}个):")
        for c in vol_cols:
            valid_data = factor_matrix[c].dropna()
            if len(valid_data) > 0:
                best_etf = valid_data.idxmin()  # 低波动最好
                best_val = valid_data.min()
                print(f"   {c}: {best_etf} ({best_val:.1f}%)")
    
    # Top ETF推荐
    print(f"\n🏆 综合因子得分 Top 10:")
    print("-"*50)
    top_etfs = composite_scores.sort_values(ascending=False).head(10)
    for i, (ticker, score) in enumerate(top_etfs.items(), 1):
        cat = all_etfs.get(ticker, {}).get('category', '')
        print(f"  {i:2d}. {ticker:<6} ({cat:<8}) 综合分: {score:+.3f}")
    
    # 推荐持仓
    print(f"\n📋 建议持仓 (Top 5):")
    holdings = top_etfs.head(5)
    for ticker, score in holdings.items():
        weight = 1.0 / len(holdings)
        print(f"  {ticker}: {weight*100:.1f}%")
    
    print("\n" + "="*70)
    
    # 保存结果
    save_results({
        'factor_matrix': factor_matrix.to_dict(),
        'standardized': std_matrix.to_dict(),
        'composite_scores': composite_scores.to_dict(),
        'top_etfs': composite_scores.sort_values(ascending=False).head(10).to_dict()
    }, '24factor')
    
    return factor_matrix


def save_results(data, prefix='signals'):
    """保存结果"""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(f'{output_dir}/{prefix}_{timestamp}.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    with open(f'{output_dir}/latest.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF轮动系统 v3.1')
    parser.add_argument('--mode', 
                       choices=['factor24', 'factor', 'rotation', 'backtest'], 
                       default='factor24', 
                       help='运行模式')
    parser.add_argument('--strategy', 
                       default='dual_momentum', 
                       help='回测策略')
    
    args = parser.parse_args()
    
    if args.mode == 'factor24':
        run_24factor_analysis()
    elif args.mode == 'factor':
        run_factor_analysis()
    elif args.mode == 'rotation':
        run_professional_rotation()
    elif args.mode == 'backtest':
        run_backtest(strategy=args.strategy)


if __name__ == '__main__':
    main()

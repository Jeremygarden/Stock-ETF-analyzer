"""
ETF轮动系统主程序 (v4.0)
支持双策略选择:
- 策略一: 长期动量策略 (基本面+技术面)
- 策略二: 短期机会策略 (纯技术面)
"""

import os
import sys
from datetime import datetime
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dual_strategy import DualStrategyModel, calculate_portfolio_scores
from config import ETF_CONFIG


def run_dual_strategy(strategy: int = 1):
    """运行双策略分析"""
    print(f"\n{'='*70}")
    print(f"ETF轮动系统 v4.0 - {'策略一(长期动量)' if strategy == 1 else '策略二(短期机会)'}")
    print(f"{'='*70}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 准备ETF列表
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    all_etfs.update(ETF_CONFIG['benchmark_etfs'])
    etf_tickers = list(all_etfs.keys())
    
    # 2. 计算得分
    print(f"[1/2] 正在计算{len(etf_tickers)}个ETF的因子和得分...")
    results_df = calculate_portfolio_scores(etf_tickers, strategy=strategy)
    
    # 3. 输出结果
    print(f"\n[2/2] 输出结果...\n")
    
    model = DualStrategyModel(strategy=strategy)
    factor_list = model.get_recommended_factors()
    
    # 打印配置
    print("="*70)
    strategy_name = "策略一(长期动量)" if strategy == 1 else "策略二(短期机会)"
    print(f"📊 {strategy_name} - 因子配置")
    print("="*70)
    
    for group, config in model.factor_config.items():
        print(f"\n【{config['description']}】权重: {config['weight']*100:.0f}%")
        print(f"   因子: {', '.join(config['factors'])}")
    
    # 打印结果
    print(f"\n{'='*70}")
    print(f"🏆 ETF排名 (按综合得分)")
    print("="*70)
    
    # 简化显示列
    display_cols = ['ticker', 'composite_score', 'risk_level', 'recommendation']
    display_cols += [c for c in results_df.columns if c in factor_list[:4]]
    
    print(f"\n{'代码':<8} {'得分':<8} {'风险':<8} {'建议':<10} {'主要因子':<30}")
    print("-"*70)
    
    for _, row in results_df.head(10).iterrows():
        # 获取主要因子
        main_factors = []
        for f in ['ret_20d', 'rsi_14', 'cci', 'vol_20']:
            if f in row and pd.notna(row[f]):
                main_factors.append(f"{f}={row[f]}")
        
        cat = all_etfs.get(row['ticker'], {}).get('category', '')[:6]
        print(f"{row['ticker']:<8} {row['composite_score']:>7.1f} {row['risk_level']:<8} {row['recommendation']:<10} {cat}")
    
    # 风险统计
    print(f"\n⚠️ 风险统计:")
    risk_counts = results_df['risk_level'].value_counts()
    for level, count in risk_counts.items():
        print(f"   {level}: {count}个")
    
    # 推荐持仓
    print(f"\n📋 建议持仓 (Top 5, 排除HIGH风险):")
    ok_holdings = results_df[results_df['risk_level'] != 'HIGH'].head(5)
    for _, row in ok_holdings.iterrows():
        weight = 1.0 / len(ok_holdings)
        print(f"   {row['ticker']}: {weight*100:.1f}% (得分:{row['composite_score']:.1f})")
    
    print("\n" + "="*70)
    
    # 保存结果
    save_results(results_df.to_dict(), f'strategy{strategy}')
    
    return results_df


def compare_strategies():
    """对比两个策略"""
    print(f"\n{'='*70}")
    print(f"📊 策略对比分析")
    print(f"{'='*70}\n")
    
    # 运行两个策略
    result1 = run_dual_strategy(strategy=1)
    result2 = run_dual_strategy(strategy=2)
    
    # 对比
    print(f"\n{'='*70}")
    print(f"📈 策略对比结果")
    print(f"{'='*70}")
    
    print(f"\n{'指标':<20} {'策略一':<15} {'策略二':<15}")
    print("-"*50)
    
    # Top1
    top1_1 = result1.iloc[0]['ticker'] if len(result1) > 0 else 'N/A'
    top1_2 = result2.iloc[0]['ticker'] if len(result2) > 0 else 'N/A'
    print(f"{'Top1推荐':<20} {top1_1:<15} {top1_2:<15}")
    
    # 平均得分
    avg1 = result1['composite_score'].mean()
    avg2 = result2['composite_score'].mean()
    print(f"{'平均得分':<20} {avg1:<15.1f} {avg2:<15.1f}")
    
    # 高风险数量
    high1 = (result1['risk_level'] == 'HIGH').sum()
    high2 = (result2['risk_level'] == 'HIGH').sum()
    print(f"{'高风险数量':<20} {high1:<15} {high2:<15}")


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
    
    parser = argparse.ArgumentParser(description='ETF轮动系统 v4.0')
    parser.add_argument('--mode', 
                       choices=['strategy1', 'strategy2', 'compare'], 
                       default='strategy1', 
                       help='运行模式')
    
    args = parser.parse_args()
    
    if args.mode == 'strategy1':
        run_dual_strategy(strategy=1)
    elif args.mode == 'strategy2':
        run_dual_strategy(strategy=2)
    elif args.mode == 'compare':
        compare_strategies()


if __name__ == '__main__':
    main()

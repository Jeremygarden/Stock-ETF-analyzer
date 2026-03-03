"""
优化诊断工具 - 逐步输出优化结果
"""
import os, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from strategy_engine import DualStrategyModel
from config import ETF_CONFIG


def get_all_tickers():
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    all_etfs.update(ETF_CONFIG['benchmark_etfs'])
    return list(all_etfs.keys()), all_etfs


def collect_all_factors(tickers):
    """收集所有ETF的原始因子"""
    model = DualStrategyModel(strategy=1)
    all_data = []
    
    for ticker in tickers:
        print(f"  采集 {ticker}...")
        factors = model.calculate_all_factors(ticker)
        if factors.get('success'):
            all_data.append(factors)
        time.sleep(0.2)
    
    return all_data


def step1_zscore_diagnosis(all_data):
    """第1步: 诊断因子量纲问题，展示Z-score标准化前后对比"""
    print("\n" + "="*70)
    print("📊 第1步: 因子Z-score标准化诊断")
    print("="*70)
    
    # 关键因子列表
    key_factors = [
        'ret_1d', 'ret_5d', 'ret_20d', 'ret_60d',
        'vol_20', 'rsi_14', 'cci', 'bb_pos', 'mfi',
        'kurt_20', 'skew_20', 'atr_ratio', 'vol_ratio',
        'earnings_yield', 'roe', 'net_margin'
    ]
    
    # 构建DataFrame
    rows = []
    for d in all_data:
        row = {'ticker': d['ticker']}
        for f in key_factors:
            row[f] = d.get(f, np.nan)
        rows.append(row)
    
    df = pd.DataFrame(rows).set_index('ticker')
    
    # 1. 原始值统计
    print("\n【原始值统计】")
    print(f"{'因子':<16} {'最小值':>10} {'最大值':>10} {'均值':>10} {'标准差':>10} {'量纲问题'}")
    print("-"*70)
    
    for col in df.columns:
        vals = df[col].dropna()
        if len(vals) > 0:
            mn, mx = vals.min(), vals.max()
            mean, std = vals.mean(), vals.std()
            # 判断量纲问题
            issue = ""
            if abs(mx - mn) > 100:
                issue = "⚠️ 范围过大"
            elif std < 0.01:
                issue = "⚠️ 方差过小"
            elif abs(mean) > 50:
                issue = "⚠️ 均值偏移"
            else:
                issue = "✅ OK"
            print(f"{col:<16} {mn:>10.2f} {mx:>10.2f} {mean:>10.2f} {std:>10.2f} {issue}")
    
    # 2. Z-score标准化
    print("\n【Z-score标准化后】")
    df_z = (df - df.mean()) / df.std()
    
    print(f"\n{'因子':<16} {'最小值':>10} {'最大值':>10} {'均值':>10} {'标准差':>10}")
    print("-"*60)
    for col in df_z.columns:
        vals = df_z[col].dropna()
        if len(vals) > 0:
            print(f"{col:<16} {vals.min():>10.2f} {vals.max():>10.2f} {vals.mean():>10.2f} {vals.std():>10.2f}")
    
    # 3. 标准化前后排名对比 (以ret_60d为例)
    print("\n【标准化前后排名对比 - ret_60d (6个月收益)】")
    print(f"{'ETF':<8} {'原始值':>10} {'Z-score':>10} {'原始排名':>10} {'Z排名':>10}")
    print("-"*50)
    
    raw_rank = df['ret_60d'].rank(ascending=False)
    z_rank = df_z['ret_60d'].rank(ascending=False)
    
    for ticker in df.index[:10]:
        raw = df.loc[ticker, 'ret_60d']
        z = df_z.loc[ticker, 'ret_60d']
        if pd.notna(raw):
            print(f"{ticker:<8} {raw:>10.2f} {z:>10.2f} {int(raw_rank[ticker]):>10} {int(z_rank[ticker]):>10}")
    
    return df, df_z


def step2_fix_adx(all_data):
    """第2步: 修复ADX计算"""
    print("\n" + "="*70)
    print("🔧 第2步: ADX计算修复")
    print("="*70)
    
    print("\n【当前ADX值 (简化版 - 用波动率代理)】")
    print(f"{'ETF':<8} {'当前ADX':>10} {'问题'}")
    print("-"*40)
    
    adx_values = []
    for d in all_data:
        adx = d.get('adx', 0)
        adx_values.append(adx)
        issue = ""
        if adx < 15:
            issue = "⚠️ 异常低"
        elif adx > 40:
            issue = "⚠️ 异常高"
        else:
            issue = "✅"
        print(f"{d['ticker']:<8} {adx:>10.1f} {issue}")
    
    print(f"\n  均值: {np.mean(adx_values):.1f}")
    print(f"  标准差: {np.std(adx_values):.1f}")
    print(f"\n  问题: 当前ADX用波动率代理，所有值集中在18-22之间")
    print(f"  修复: 改用真正的ADX公式 (DM+/DM-/DX/ADX)")


def step3_correlation(all_data):
    """第3步: 因子相关性矩阵"""
    print("\n" + "="*70)
    print("🔗 第3步: 因子相关性分析")
    print("="*70)
    
    key_factors = [
        'ret_5d', 'ret_20d', 'ret_60d', 'momentum_accel',
        'vol_20', 'rsi_14', 'cci', 'bb_pos', 'mfi',
        'kurt_20', 'skew_20', 'atr_ratio',
        'earnings_yield', 'roe', 'net_margin'
    ]
    
    rows = []
    for d in all_data:
        row = {}
        for f in key_factors:
            row[f] = d.get(f, np.nan)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    corr = df.corr()
    
    # 找出高相关性对 (>0.7)
    print("\n【高相关因子对 (|r| > 0.7) — 可能重复计数】")
    print(f"{'因子A':<18} {'因子B':<18} {'相关系数':>10} {'建议'}")
    print("-"*65)
    
    high_corr_pairs = []
    for i in range(len(corr.columns)):
        for j in range(i+1, len(corr.columns)):
            r = corr.iloc[i, j]
            if abs(r) > 0.7 and not np.isnan(r):
                a, b = corr.columns[i], corr.columns[j]
                action = "⚠️ 考虑合并或删一个" if abs(r) > 0.85 else "🟡 观察"
                print(f"{a:<18} {b:<18} {r:>10.3f} {action}")
                high_corr_pairs.append((a, b, r))
    
    if not high_corr_pairs:
        print("  ✅ 未发现高相关因子对")
    
    # 低相关性因子 (独立信息源)
    print("\n【低相关因子对 (|r| < 0.2) — 提供独立信息】")
    low_count = 0
    for i in range(len(corr.columns)):
        for j in range(i+1, len(corr.columns)):
            r = corr.iloc[i, j]
            if abs(r) < 0.2 and not np.isnan(r):
                low_count += 1
    print(f"  共 {low_count} 对因子相关性低于0.2，说明因子池多样性{'良好' if low_count > 20 else '一般'}")
    
    return corr


def step4_risk_parity_weights(all_data):
    """第4步: 风险平价持仓权重"""
    print("\n" + "="*70)
    print("⚖️ 第4步: 风险平价 vs 等权持仓对比")
    print("="*70)
    
    # 取Top 5 ETF
    model = DualStrategyModel(strategy=1)
    scores = []
    for d in all_data:
        result = model.calculate_strategy_score(d)
        scores.append({
            'ticker': d['ticker'],
            'score': result['composite_score'],
            'vol': d.get('vol_20', 20)
        })
    
    scores_df = pd.DataFrame(scores).sort_values('score', ascending=False)
    top5 = scores_df.head(5)
    
    # 等权
    equal_weights = {row['ticker']: 20.0 for _, row in top5.iterrows()}
    
    # 风险平价: 权重 = 1/波动率，然后归一化
    inv_vols = []
    for _, row in top5.iterrows():
        vol = max(row['vol'], 5)  # 防止除零
        inv_vols.append(1.0 / vol)
    
    total_inv = sum(inv_vols)
    rp_weights = {}
    for i, (_, row) in enumerate(top5.iterrows()):
        rp_weights[row['ticker']] = round(inv_vols[i] / total_inv * 100, 1)
    
    print("\n【Top 5 持仓权重对比】")
    print(f"{'ETF':<8} {'得分':>8} {'波动率%':>10} {'等权%':>8} {'风险平价%':>10} {'差异'}")
    print("-"*60)
    
    for _, row in top5.iterrows():
        t = row['ticker']
        eq = equal_weights[t]
        rp = rp_weights[t]
        diff = "↑" if rp > eq else "↓"
        print(f"{t:<8} {row['score']:>8.1f} {row['vol']:>10.1f} {eq:>8.1f} {rp:>10.1f} {diff}")
    
    # 组合波动率估算
    eq_port_vol = sum(row['vol'] * 0.2 for _, row in top5.iterrows())
    rp_port_vol = sum(row['vol'] * rp_weights[row['ticker']]/100 for _, row in top5.iterrows())
    
    print(f"\n  等权组合加权波动率: {eq_port_vol:.1f}%")
    print(f"  风险平价加权波动率: {rp_port_vol:.1f}%")
    print(f"  波动率降低: {(1 - rp_port_vol/eq_port_vol)*100:.1f}%")


if __name__ == '__main__':
    tickers, etf_map = get_all_tickers()
    
    print("正在采集22个ETF的因子数据...")
    all_data = collect_all_factors(tickers)
    print(f"✅ 成功采集 {len(all_data)} 个ETF\n")
    
    # 第1步
    df, df_z = step1_zscore_diagnosis(all_data)
    
    # 第2步
    step2_fix_adx(all_data)
    
    # 第3步
    corr = step3_correlation(all_data)
    
    # 第4步
    step4_risk_parity_weights(all_data)
    
    print("\n" + "="*70)
    print("✅ 诊断完成！等待决策...")
    print("="*70)

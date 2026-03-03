"""
ETF基本面数据模块
================

通过两种方式获取ETF基本面数据:
1. funds_data.equity_holdings → PE/PB/PS (直接)
2. top_holdings穿透 → ROE/Earnings Growth (逐股加权)

缓存策略:
- 本地JSON缓存，每周自动更新
- 缓存路径: etf-rotator/cache/fundamentals.json
- 过期时间: 7天

Author: Financer AI
Date: 2026-03-03
"""

import os
import json
import time
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'fundamentals.json')
CACHE_EXPIRY_DAYS = 7  # 每周更新


def load_cache() -> Dict:
    """加载缓存"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_cache(data: Dict):
    """保存缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def is_cache_valid(cache_entry: Dict) -> bool:
    """检查缓存是否在有效期内"""
    if not cache_entry or 'updated_at' not in cache_entry:
        return False
    
    updated = datetime.fromisoformat(cache_entry['updated_at'])
    return (datetime.now() - updated) < timedelta(days=CACHE_EXPIRY_DAYS)


def get_etf_fundamentals(ticker: str, force_refresh: bool = False) -> Dict:
    """
    获取单只ETF的基本面数据
    
    流程:
    1. 检查缓存 → 有效则直接返回
    2. 获取ETF整体指标 (PE/PB/PS)
    3. 穿透Top10持仓计算加权ROE/Earnings Growth
    4. 写入缓存
    
    Args:
        ticker: ETF代码
        force_refresh: 强制刷新
        
    Returns:
        Dict: 基本面数据
    """
    cache = load_cache()
    
    # 检查缓存
    if not force_refresh and ticker in cache and is_cache_valid(cache[ticker]):
        print(f"  {ticker}: 使用缓存 (更新于 {cache[ticker]['updated_at'][:10]})")
        return cache[ticker]
    
    print(f"  {ticker}: 获取基本面数据...")
    result = {
        'ticker': ticker,
        'updated_at': datetime.now().isoformat(),
        'source': 'yfinance',
    }
    
    try:
        etf = yf.Ticker(ticker)
        fd = etf.funds_data
        
        # ===== 层1: ETF整体指标 =====
        try:
            eq = fd.equity_holdings
            if eq is not None and not eq.empty:
                # equity_holdings格式: index=指标名, columns=[ETF名, Category Average]
                for idx in eq.index:
                    val = eq.iloc[eq.index.get_loc(idx), 0]  # 第一列是ETF自身
                    if pd.notna(val):
                        val = float(val)
                        if 'Earnings' in idx and 'Price' in idx:
                            result['pe_ratio'] = round(1/val if val > 0 else 0, 2)
                            result['earnings_yield'] = round(val * 100, 2)
                        elif 'Book' in idx and 'Price' in idx:
                            result['pb_ratio'] = round(1/val if val > 0 else 0, 2)
                        elif 'Sales' in idx and 'Price' in idx:
                            result['ps_ratio'] = round(1/val if val > 0 else 0, 2)
                        elif 'Cashflow' in idx and 'Price' in idx:
                            result['pcf_ratio'] = round(1/val if val > 0 else 0, 2)
                        elif 'Earnings Growth' in idx:
                            result['earnings_growth_3y'] = round(val * 100, 2)
        except Exception as e:
            result['equity_holdings_error'] = str(e)
        
        # ===== 层2: Top Holdings 穿透 =====
        try:
            th = fd.top_holdings
            if th is not None and not th.empty:
                holdings_list = []
                weighted_roe = 0
                weighted_eg = 0
                weighted_margin = 0
                total_weight = 0
                
                for symbol, row in th.head(10).iterrows():
                    weight = row['Holding Percent']
                    holding = {
                        'symbol': symbol,
                        'name': row.get('Name', ''),
                        'weight': round(weight * 100, 2),
                    }
                    
                    try:
                        stock = yf.Ticker(symbol)
                        info = stock.info
                        
                        roe = info.get('returnOnEquity')
                        eg = info.get('earningsGrowth')
                        margin = info.get('profitMargins')
                        pe = info.get('trailingPE')
                        
                        if roe is not None:
                            holding['roe'] = round(roe * 100, 2)
                            weighted_roe += roe * 100 * weight
                        if eg is not None:
                            holding['earnings_growth'] = round(eg * 100, 2)
                            weighted_eg += eg * 100 * weight
                        if margin is not None:
                            holding['net_margin'] = round(margin * 100, 2)
                            weighted_margin += margin * 100 * weight
                        if pe is not None:
                            holding['pe'] = round(pe, 2)
                        
                        total_weight += weight
                        
                    except Exception as e:
                        holding['error'] = str(e)
                    
                    holdings_list.append(holding)
                    time.sleep(0.3)  # 限速
                
                result['top_holdings'] = holdings_list
                result['holdings_coverage'] = round(total_weight * 100, 1)
                
                # 加权平均 (按持仓权重归一化)
                if total_weight > 0:
                    result['weighted_roe'] = round(weighted_roe / total_weight, 2)
                    result['weighted_earnings_growth'] = round(weighted_eg / total_weight, 2)
                    result['weighted_net_margin'] = round(weighted_margin / total_weight, 2)
                
        except Exception as e:
            result['holdings_error'] = str(e)
        
        # ===== 层3: 行业分布 =====
        try:
            sw = fd.sector_weightings
            if sw:
                result['sector_weightings'] = {k: round(v, 4) for k, v in sw.items() if v > 0}
        except:
            pass
        
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False
    
    # 写入缓存
    cache[ticker] = result
    save_cache(cache)
    
    return result


def get_fundamental_factors(ticker: str, force_refresh: bool = False) -> Dict:
    """
    获取用于策略计算的基本面因子
    
    返回标准化的因子字典，可直接用于strategy_engine
    
    Args:
        ticker: ETF代码
        force_refresh: 强制刷新
        
    Returns:
        Dict: {earnings_yield, roe, net_margin, earnings_growth}
    """
    data = get_etf_fundamentals(ticker, force_refresh)
    
    factors = {}
    
    # 优先用ETF整体指标
    if 'earnings_yield' in data:
        factors['earnings_yield'] = data['earnings_yield']
    
    # 穿透数据补充
    if 'weighted_roe' in data:
        factors['roe'] = data['weighted_roe']
    
    if 'weighted_net_margin' in data:
        factors['net_margin'] = data['weighted_net_margin']
    
    if 'weighted_earnings_growth' in data:
        factors['earnings_growth'] = data['weighted_earnings_growth']
    elif 'earnings_growth_3y' in data:
        factors['earnings_growth'] = data['earnings_growth_3y']
    
    return factors


def refresh_all_etfs(tickers: List[str]):
    """
    批量刷新所有ETF的基本面数据
    
    适合cron定期调用
    """
    print(f"\n{'='*60}")
    print(f"🔄 批量刷新ETF基本面数据")
    print(f"{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ETF数量: {len(tickers)}\n")
    
    success = 0
    failed = 0
    cached = 0
    
    for ticker in tickers:
        result = get_etf_fundamentals(ticker)
        if result.get('success'):
            if 'weighted_roe' in result:
                success += 1
                print(f"  ✅ {ticker}: EY={result.get('earnings_yield', 'N/A')}%, "
                      f"ROE={result.get('weighted_roe', 'N/A')}%, "
                      f"EG={result.get('weighted_earnings_growth', 'N/A')}%")
            else:
                cached += 1
        else:
            failed += 1
            print(f"  ❌ {ticker}: {result.get('error', 'Unknown')}")
    
    print(f"\n完成: ✅{success} 📦缓存{cached} ❌{failed}")
    
    # 打印缓存状态
    cache = load_cache()
    print(f"\n📦 缓存文件: {CACHE_FILE}")
    print(f"   缓存条目: {len(cache)}")
    if cache:
        oldest = min(v.get('updated_at', '') for v in cache.values() if v.get('updated_at'))
        print(f"   最旧条目: {oldest[:10]}")


# ===== 命令行入口 =====
if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from config import ETF_CONFIG
    
    all_etfs = {}
    all_etfs.update(ETF_CONFIG['sector_etfs'])
    all_etfs.update(ETF_CONFIG['emerging_etfs'])
    all_etfs.update(ETF_CONFIG['option_income_etfs'])
    all_etfs.update(ETF_CONFIG['benchmark_etfs'])
    
    tickers = list(all_etfs.keys())
    
    if '--force' in sys.argv:
        print("⚠️ 强制刷新模式")
        for t in tickers:
            get_etf_fundamentals(t, force_refresh=True)
    else:
        refresh_all_etfs(tickers)

"""
专业ETF数据源模块
支持多个数据源获取更全面的市场数据
"""

import os
import time
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional


class ETFDataSource:
    """ETF专业数据源"""
    
    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        self.cache = {}
        
    def fetch_comprehensive_data(self, ticker: str, period: str = '2y') -> Dict:
        """
        获取综合ETF数据
        包括: 价格、因子数据、基本面、替代数据
        """
        data = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'success': False
        }
        
        try:
            # 1. 价格数据
            price_data = self._fetch_price_data(ticker, period)
            if price_data is not None:
                data['price'] = price_data
                
                # 2. 计算价格因子
                data['price_factors'] = self._calculate_price_factors(price_data)
            
            # 3. 基本面数据
            fundamentals = self._fetch_fundamentals(ticker)
            if fundamentals:
                data['fundamentals'] = fundamentals
            
            # 4. 期权数据
            options = self._fetch_options_data(ticker)
            if options:
                data['options'] = options
                
            # 5. 关联ETF数据
            correlations = self._calculate_correlations(ticker)
            if correlations:
                data['correlations'] = correlations
                
            data['success'] = True
            
        except Exception as e:
            data['error'] = str(e)
        
        return data
    
    def _fetch_price_data(self, ticker: str, period: str) -> Optional[pd.DataFrame]:
        """获取价格数据"""
        try:
            etf = yf.Ticker(ticker)
            hist = etf.history(period=period)
            
            if hist.empty:
                return None
            
            # 转换为日收益率
            prices = hist['Close']
            returns = prices.pct_change().dropna()
            
            return {
                'prices': prices.to_dict(),
                'returns': returns.to_dict(),
                'volume': hist['Volume'].to_dict(),
                'start_date': str(prices.index[0].date()),
                'end_date': str(prices.index[-1].date()),
            }
            
        except Exception as e:
            print(f"  ⚠️ {ticker} 价格数据获取失败: {e}")
            return None
    
    def _calculate_price_factors(self, price_data: Dict) -> Dict:
        """计算价格因子"""
        prices = pd.Series(price_data['prices'])
        returns = pd.Series(price_data['returns'])
        
        factors = {}
        
        # 动量因子 (不同周期)
        for period in [5, 10, 20, 60, 120, 250]:
            if len(prices) >= period:
                ret = (prices.iloc[-1] / prices.iloc[-period] - 1) * 100
                factors[f'momentum_{period}d'] = round(ret, 2)
        
        # 波动率因子
        if len(returns) >= 20:
            vol_20d = returns.tail(20).std() * np.sqrt(252) * 100
            factors['volatility_20d'] = round(vol_20d, 2)
        
        if len(returns) >= 60:
            vol_60d = returns.tail(60).std() * np.sqrt(252) * 100
            factors['volatility_60d'] = round(vol_60d, 2)
        
        # 波动率变化
        if len(returns) >= 40:
            recent_vol = returns.tail(20).std()
            older_vol = returns.iloc[-40:-20].std()
            vol_change = (recent_vol / older_vol - 1) * 100 if older_vol > 0 else 0
            factors['volatility_change'] = round(vol_change, 2)
        
        # 收益率分布
        if len(returns) >= 20:
            factors['skewness'] = round(returns.tail(20).skew(), 3)
            factors['kurtosis'] = round(returns.tail(20).kurtosis(), 3)
        
        # 创新高/新低
        if len(prices) >= 20:
            factors['price_position'] = round(
                (prices.iloc[-1] - prices.min()) / (prices.max() - prices.min() + 0.001) * 100, 1
            )
        
        # 成交量因子
        if 'volume' in price_data and len(price_data['volume']) >= 20:
            volumes = pd.Series(price_data['volume'])
            avg_vol_20 = volumes.tail(20).mean()
            avg_vol_60 = volumes.iloc[-60:-20].mean() if len(volumes) >= 60 else avg_vol_20
            vol_ratio = avg_vol_20 / avg_vol_60 if avg_vol_60 > 0 else 1
            factors['volume_ratio'] = round(vol_ratio, 2)
        
        return factors
    
    def _fetch_fundamentals(self, ticker: str) -> Optional[Dict]:
        """获取基本面数据"""
        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            
            fundamentals = {}
            
            # 费率相关
            if 'expenseRatio' in info:
                fundamentals['expense_ratio'] = info.get('expenseRatio', 0)
            if 'totalAssets' in info:
                fundamentals['aum'] = info.get('totalAssets', 0)
            
            # 股息相关
            if 'dividendYield' in info and info['dividendYield']:
                fundamentals['dividend_yield'] = info.get('dividendYield', 0) * 100
            if 'dividendRate' in info:
                fundamentals['dividend_rate'] = info.get('dividendRate', 0)
            
            # 价格倍数
            if 'peRatio' in info:
                fundamentals['pe_ratio'] = info.get('peRatio', None)
            if 'pbRatio' in info:
                fundamentals['pb_ratio'] = info.get('pbRatio', None)
            
            # 杠杆/反向
            if 'leveraged' in info:
                fundamentals['leveraged'] = info.get('leveraged', False)
            if 'beta' in info:
                fundamentals['beta'] = info.get('beta', 1.0)
            
            return fundamentals
            
        except Exception as e:
            return None
    
    def _fetch_options_data(self, ticker: str) -> Optional[Dict]:
        """获取期权数据"""
        try:
            etf = yf.Ticker(ticker)
            
            # 获取put/call比率
            try:
                put_call = etf.option_chain
                if put_call:
                    return {'has_options': True}
            except:
                pass
            
            return {'has_options': False}
            
        except:
            return None
    
    def _calculate_correlations(self, ticker: str) -> Optional[Dict]:
        """计算与主要指数的相关性"""
        # 简化的相关性计算
        benchmarks = ['SPY', 'QQQ', 'IWM', 'DIA', 'TLT']
        
        try:
            # 下载基准数据
            benchmark_data = yf.download(benchmarks, period='1y', progress=False)['Close']
            etf_data = yf.download(ticker, period='1y', progress=False)['Close']
            
            if benchmark_data.empty or etf_data.empty:
                return None
            
            # 计算相关系数
            etf_returns = etf_data.pct_change().dropna()
            benchmark_returns = benchmark_data.pct_change().dropna()
            
            # 对齐数据
            aligned = pd.concat([etf_returns, benchmark_returns], axis=1).dropna()
            if aligned.empty:
                return None
            
            correlations = {}
            for col in benchmarks:
                if col in aligned.columns:
                    corr = aligned[ticker].corr(aligned[col])
                    correlations[col] = round(corr, 3)
            
            return correlations
            
        except Exception as e:
            return None
    
    def fetch_market_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """批量获取市场数据"""
        results = {}
        
        for ticker in tickers:
            print(f"  获取 {ticker} 数据...")
            results[ticker] = self.fetch_comprehensive_data(ticker)
            time.sleep(0.3)  # 避免请求过快
        
        return results


class FactorModel:
    """多因子模型"""
    
    def __init__(self):
        self.factors = {}
        
    def calculate_factors(self, etf_data: Dict[str, Dict]) -> pd.DataFrame:
        """
        计算所有ETF的因子值
        """
        factor_matrix = []
        
        for ticker, data in etf_data.items():
            if not data.get('success'):
                continue
            
            row = {'ticker': ticker}
            
            # 1. 动量因子
            price_factors = data.get('price_factors', {})
            row['momentum_20d'] = price_factors.get('momentum_20d', 0)
            row['momentum_60d'] = price_factors.get('momentum_60d', 0)
            row['momentum_120d'] = price_factors.get('momentum_120d', 0)
            
            # 动量加速度
            if 'momentum_20d' in price_factors and 'momentum_60d' in price_factors:
                row['momentum_acceleration'] = (
                    price_factors['momentum_20d'] - price_factors['momentum_60d']
                )
            
            # 2. 波动率因子
            row['volatility_20d'] = price_factors.get('volatility_20d', 0)
            row['volatility_60d'] = price_factors.get('volatility_60d', 0)
            row['volatility_change'] = price_factors.get('volatility_change', 0)
            
            # 低波动因子 (波动率排名)
            # 稍后计算
            
            # 3. 规模因子 (AUM)
            fundamentals = data.get('fundamentals', {})
            aum = fundamentals.get('aum', 0)
            row['log_aum'] = np.log(aum + 1) if aum > 0 else 0
            
            # 4. 价值因子
            row['dividend_yield'] = fundamentals.get('dividend_yield', 0)
            row['pe_ratio'] = fundamentals.get('pe_ratio') or 0
            
            # 5. 质量因子
            expense_ratio = fundamentals.get('expense_ratio', 0)
            row['quality'] = -expense_ratio * 100  # 低费率 = 高质量
            
            # 6. 杠杆因子
            row['beta'] = fundamentals.get('beta', 1.0)
            row['leveraged'] = 1 if fundamentals.get('leveraged') else 0
            
            # 7. 流动性因子
            row['volume_ratio'] = price_factors.get('volume_ratio', 1)
            
            # 8. 分布因子
            row['skewness'] = price_factors.get('skewness', 0)
            row['kurtosis'] = price_factors.get('kurtosis', 0)
            
            # 9. 相对强弱
            row['price_position'] = price_factors.get('price_position', 50)
            
            # 相关性因子 (后续计算)
            
            factor_matrix.append(row)
        
        return pd.DataFrame(factor_matrix)
    
    def calculate_factor_returns(self, factor_matrix: pd.DataFrame) -> Dict:
        """计算因子收益率"""
        if factor_matrix.empty:
            return {}
        
        # 使用收益率作为被解释变量
        # 这里简化处理，实际需要回归分析
        
        factor_returns = {}
        
        # 计算每个因子与收益的相关性
        return_cols = [c for c in factor_matrix.columns if c.startswith('momentum_')]
        
        if return_cols:
            primary_return = factor_matrix['momentum_20d']
            
            for col in factor_matrix.columns:
                if col in ['ticker', 'momentum_20d']:
                    continue
                
                corr = factor_matrix[col].corr(primary_return)
                factor_returns[col] = round(corr, 3)
        
        return factor_returns
    
    def calculate_portfolio_factors(self, holdings: Dict[str, float], etf_data: Dict) -> Dict:
        """
        计算组合的因子暴露
        holdings: {ticker: weight}
        """
        if not holdings:
            return {}
        
        factor_exposure = {
            'momentum': 0,
            'volatility': 0,
            'quality': 0,
            'dividend_yield': 0,
            'beta': 0,
        }
        
        total_weight = sum(holdings.values())
        
        for ticker, weight in holdings.items():
            if ticker not in etf_data or not etf_data[ticker].get('success'):
                continue
            
            norm_weight = weight / total_weight
            
            pf = etf_data[ticker].get('price_factors', {})
            fd = etf_data[ticker].get('fundamentals', {})
            
            factor_exposure['momentum'] += norm_weight * pf.get('momentum_20d', 0)
            factor_exposure['volatility'] += norm_weight * pf.get('volatility_20d', 0)
            factor_exposure['quality'] += norm_weight * fd.get('expense_ratio', 0) * 100
            factor_exposure['dividend_yield'] += norm_weight * fd.get('dividend_yield', 0)
            factor_exposure['beta'] += norm_weight * fd.get('beta', 1.0)
        
        return {k: round(v, 2) for k, v in factor_exposure.items()}


# 数据源配置
DATA_SOURCES = {
    'yfinance': {
        'name': 'Yahoo Finance',
        'free': True,
        'description': '免费实时价格数据'
    },
    'alphavantage': {
        'name': 'Alpha Vantage',
        'free': '有限',
        'key': 'api_key',
        'description': '提供API key后可获取更多数据'
    },
    'fmp': {
        'name': 'Financial Modeling Prep',
        'free': '有限',
        'key': 'fmp_key',
        'description': '专业基本面数据'
    }
}


if __name__ == '__main__':
    # 测试
    ds = ETFDataSource()
    tickers = ['XLK', 'SPY', 'QQQ']
    
    data = ds.fetch_market_data(tickers)
    print(f"获取了 {len(data)} 个ETF的数据")
    
    # 计算因子
    fm = FactorModel()
    factors = fm.calculate_factors(data)
    print(f"\n因子矩阵:\n{factors.head()}")

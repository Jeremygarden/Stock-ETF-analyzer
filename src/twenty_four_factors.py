"""
24因子模型模块
基于Barra多因子模型和业界标准量化因子
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional
import yfinance as yf
from datetime import datetime, timedelta


class TwentyFourFactorModel:
    """
    24因子量化模型
    
    因子分类:
    1. 动量因子 (6个): 短期/中期/长期/动量加速/相对动量/绝对动量
    2. 价值因子 (4个): 股息率/PE/PB/PCF
    3. 质量因子 (5个): ROE/ROA/毛利率/净利率/资产周转率
    4. 成长因子 (3个): 营收增长/盈利增长/ROE变化
    5. 波动率因子 (3个): 20日/60日/波动率变化
    6. 规模因子 (1个): 市值
    7. 流动性因子 (2个): 成交量/换手率变化
    """
    
    def __init__(self):
        self.factor_names = [
            # 动量因子 (6)
            'momentum_1m', 'momentum_3m', 'momentum_6m', 
            'momentum_accel', 'relative_momentum', 'absolute_momentum',
            # 价值因子 (4)
            'dividend_yield', 'earnings_yield', 'book_value', 'cashflow',
            # 质量因子 (5)
            'roe', 'roa', 'gross_margin', 'net_margin', 'asset_turnover',
            # 成长因子 (3)
            'revenue_growth', 'earnings_growth', 'roe_change',
            # 波动率因子 (3)
            'volatility_1m', 'volatility_3m', 'vol_change',
            # 规模因子 (1)
            'size',
            # 流动性因子 (2)
            'trading_volume', 'turnover_change'
        ]
        
    def calculate_all_factors(self, ticker: str, period: str = '2y') -> Dict:
        """计算单只ETF的24个因子"""
        factors = {'ticker': ticker}
        
        try:
            etf = yf.Ticker(ticker)
            hist = etf.history(period=period)
            info = etf.info
            
            if hist.empty:
                return {'ticker': ticker, 'error': 'No data'}
            
            prices = hist['Close']
            returns = prices.pct_change().dropna()
            volumes = hist['Volume']
            
            # ========== 1. 动量因子 (6个) ==========
            # 1.1 短期动量 (1个月)
            if len(prices) >= 21:
                factors['momentum_1m'] = round((prices.iloc[-1] / prices.iloc[-21] - 1) * 100, 2)
            
            # 1.2 中期动量 (3个月)
            if len(prices) >= 63:
                factors['momentum_3m'] = round((prices.iloc[-1] / prices.iloc[-63] - 1) * 100, 2)
            
            # 1.3 长期动量 (6个月)
            if len(prices) >= 126:
                factors['momentum_6m'] = round((prices.iloc[-1] / prices.iloc[-126] - 1) * 100, 2)
            
            # 1.4 动量加速度 (短期-长期)
            if 'momentum_1m' in factors and 'momentum_3m' in factors:
                factors['momentum_accel'] = round(factors['momentum_1m'] - factors['momentum_3m'], 2)
            
            # 1.5 相对动量 (vs 市场)
            if len(prices) >= 63:
                market_data = yf.download('SPY', period=period, progress=False)['Close']
                if not market_data.empty:
                    etf_ret = (prices.iloc[-1] / prices.iloc[-63] - 1)
                    mkt_ret = (market_data.iloc[-1] / market_data.iloc[-63] - 1)
                    factors['relative_momentum'] = round((etf_ret - mkt_ret) * 100, 2)
            
            # 1.6 绝对动量 (6个月是否上涨)
            if 'momentum_6m' in factors:
                factors['absolute_momentum'] = 1 if factors['momentum_6m'] > 0 else 0
            
            # ========== 2. 价值因子 (4个) ==========
            # 2.1 股息率
            if 'dividendYield' in info and info['dividendYield']:
                factors['dividend_yield'] = round(info['dividendYield'] * 100, 2)
            elif 'dividendRate' in info and 'currentPrice' in info and info['currentPrice']:
                factors['dividend_yield'] = round(info.get('dividendRate', 0) / info['currentPrice'] * 100, 2)
            else:
                factors['dividend_yield'] = 0
            
            # 2.2 盈利收益率 (1/E/P)
            if 'peRatio' in info and info['peRatio'] and info['peRatio'] > 0:
                factors['earnings_yield'] = round(100 / info['peRatio'], 2)
            else:
                factors['earnings_yield'] = 0
            
            # 2.3 账面价值 (1/PB)
            if 'priceToBook' in info and info['priceToBook'] and info['priceToBook'] > 0:
                factors['book_value'] = round(1 / info['priceToBook'], 2)
            else:
                factors['book_value'] = 0
            
            # 2.4 现金流 (1/PCF)
            if 'priceToCashFlow' in info and info['priceToCashFlow'] and info['priceToCashFlow'] > 0:
                factors['cashflow'] = round(1 / info['priceToCashFlow'], 2)
            else:
                factors['cashflow'] = 0
            
            # ========== 3. 质量因子 (5个) ==========
            # 3.1 ROE (净资产收益率)
            if 'returnOnEquity' in info and info['returnOnEquity']:
                factors['roe'] = round(info['returnOnEquity'] * 100, 2)
            else:
                factors['roe'] = 0
            
            # 3.2 ROA (总资产收益率)
            if 'returnOnAssets' in info and info['returnOnAssets']:
                factors['roa'] = round(info['returnOnAssets'] * 100, 2)
            else:
                factors['roa'] = 0
            
            # 3.3 毛利率
            if 'grossMargins' in info and info['grossMargins']:
                factors['gross_margin'] = round(info['grossMargins'] * 100, 2)
            else:
                factors['gross_margin'] = 0
            
            # 3.4 净利率
            if 'profitMargins' in info and info['profitMargins']:
                factors['net_margin'] = round(info['profitMargins'] * 100, 2)
            else:
                factors['net_margin'] = 0
            
            # 3.5 资产周转率
            if 'assetTurnover' in info and info['assetTurnover']:
                factors['asset_turnover'] = round(info['assetTurnover'], 2)
            else:
                factors['asset_turnover'] = 0
            
            # ========== 4. 成长因子 (3个) ==========
            # 4.1 营收增长
            if 'revenueGrowth' in info and info['revenueGrowth']:
                factors['revenue_growth'] = round(info['revenueGrowth'] * 100, 2)
            else:
                factors['revenue_growth'] = 0
            
            # 4.2 盈利增长
            if 'earningsGrowth' in info and info['earningsGrowth']:
                factors['earnings_growth'] = round(info['earningsGrowth'] * 100, 2)
            else:
                factors['earnings_growth'] = 0
            
            # 4.3 ROE变化
            # 简化: 使用当前ROE作为代理
            factors['roe_change'] = factors.get('roe', 0)
            
            # ========== 5. 波动率因子 (3个) ==========
            # 5.1 短期波动率 (20日年化)
            if len(returns) >= 20:
                factors['volatility_1m'] = round(returns.tail(20).std() * np.sqrt(252) * 100, 2)
            
            # 5.2 中期波动率 (60日年化)
            if len(returns) >= 60:
                factors['volatility_3m'] = round(returns.tail(60).std() * np.sqrt(252) * 100, 2)
            
            # 5.3 波动率变化
            if 'volatility_1m' in factors and 'volatility_3m' in factors:
                factors['vol_change'] = round(factors['volatility_1m'] - factors['volatility_3m'], 2)
            
            # ========== 6. 规模因子 (1个) ==========
            # 6.1 市值 (对数)
            if 'totalAssets' in info and info['totalAssets']:
                factors['size'] = round(np.log(info['totalAssets'] + 1), 2)
            else:
                factors['size'] = 0
            
            # ========== 7. 流动性因子 (2个) ==========
            # 7.1 成交量 (对数)
            if len(volumes) > 0:
                factors['trading_volume'] = round(np.log(volumes.iloc[-20:].mean() + 1), 2)
            
            # 7.2 换手率变化
            if len(volumes) >= 60:
                recent_vol = volumes.tail(20).mean()
                older_vol = volumes.iloc[-60:-20].mean()
                if older_vol > 0:
                    factors['turnover_change'] = round((recent_vol / older_vol - 1) * 100, 2)
                else:
                    factors['turnover_change'] = 0
            
            factors['success'] = True
            
        except Exception as e:
            factors['error'] = str(e)
        
        return factors
    
    def calculate_factor_matrix(self, tickers: List[str]) -> pd.DataFrame:
        """计算多只ETF的因子矩阵"""
        import time
        
        factor_list = []
        
        for ticker in tickers:
            print(f"  计算 {ticker} 因子...")
            factors = self.calculate_all_factors(ticker)
            factor_list.append(factors)
            time.sleep(0.2)
        
        df = pd.DataFrame(factor_list)
        return df.set_index('ticker')
    
    def standardize_factors(self, factor_matrix: pd.DataFrame) -> pd.DataFrame:
        """因子标准化 (Z-score)"""
        standardized = factor_matrix.copy()
        
        for col in standardized.columns:
            if col == 'ticker' or col == 'error' or col == 'success':
                continue
            
            mean = standardized[col].mean()
            std = standardized[col].std()
            
            if std > 0:
                standardized[col] = (standardized[col] - mean) / std
            else:
                standardized[col] = 0
        
        return standardized
    
    def winsorize_factors(self, factor_matrix: pd.DataFrame, 
                         lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
        """因子去极值 (Winsorize)"""
        winsorized = factor_matrix.copy()
        
        for col in winsorized.columns:
            if col in ['ticker', 'error', 'success']:
                continue
            
            # 转换为数值类型
            winsorized[col] = pd.to_numeric(winsorized[col], errors='coerce')
            
            if winsorized[col].notna().sum() < 2:
                continue
                
            try:
                lower_val = winsorized[col].quantile(lower)
                upper_val = winsorized[col].quantile(upper)
                
                winsorized[col] = winsorized[col].clip(lower_val, upper_val)
            except:
                pass
        
        return winsorized
    
    def neutralize_factors(self, factor_matrix: pd.DataFrame, 
                          neutralize_on: List[str] = None) -> pd.DataFrame:
        """因子中性化"""
        if neutralize_on is None:
            neutralize_on = ['size']
        
        neutral = factor_matrix.copy()
        
        # 对每个因子回归size, 保留残差
        for col in neutral.columns:
            if col in ['ticker', 'error', 'success'] or col in neutralize_on:
                continue
            
            if 'size' in neutral.columns:
                valid = neutral[col].notna() & neutral['size'].notna()
                if valid.sum() > 10:
                    try:
                        slope, intercept, _, _, _ = stats.linregress(
                            neutral.loc[valid, 'size'],
                            neutral.loc[valid, col]
                        )
                        neutral.loc[valid, col] = neutral.loc[valid, col] - slope * neutral.loc[valid, 'size']
                    except:
                        pass
        
        return neutral
    
    def calculate_factor_returns(self, factor_matrix: pd.DataFrame, 
                                 forward_returns: pd.Series) -> pd.DataFrame:
        """计算因子收益率 (IC方法)"""
        ic_results = []
        
        for col in factor_matrix.columns:
            if col in ['ticker', 'error', 'success']:
                continue
            
            valid = factor_matrix[col].notna() & forward_returns.notna()
            
            if valid.sum() > 5:
                ic, p_value = stats.spearmanr(
                    factor_matrix.loc[valid, col],
                    forward_returns[valid]
                )
                ic_results.append({
                    'factor': col,
                    'IC': round(ic, 4),
                    'p_value': round(p_value, 4),
                    'n': valid.sum()
                })
        
        return pd.DataFrame(ic_results).sort_values('IC', ascending=False)
    
    def factor_weight_optimization(self, factor_matrix: pd.DataFrame,
                                   target_vol: float = 0.15) -> Dict:
        """
        因子权重优化
        基于因子有效性IC分配权重
        """
        # 简化: 基于因子方向和有效性分配
        weights = {}
        
        # 动量因子 (正向)
        momentum_factors = [f for f in ['momentum_1m', 'momentum_3m', 'momentum_6m', 'relative_momentum'] 
                          if f in factor_matrix.columns]
        weights['momentum'] = 0.25
        
        # 价值因子 (正向)
        value_factors = [f for f in ['dividend_yield', 'earnings_yield', 'book_value', 'cashflow'] 
                        if f in factor_matrix.columns]
        weights['value'] = 0.15
        
        # 质量因子 (正向)
        quality_factors = [f for f in ['roe', 'roa', 'gross_margin', 'net_margin'] 
                         if f in factor_matrix.columns]
        weights['quality'] = 0.20
        
        # 成长因子 (正向)
        growth_factors = [f for f in ['revenue_growth', 'earnings_growth'] 
                         if f in factor_matrix.columns]
        weights['growth'] = 0.10
        
        # 低波动因子 (反向)
        vol_factors = [f for f in ['volatility_1m', 'volatility_3m'] 
                      if f in factor_matrix.columns]
        weights['low_volatility'] = 0.15
        
        # 流动性 (中性)
        weights['liquidity'] = 0.05
        
        # 规模 (中性)
        weights['size'] = 0.05
        
        # 动量加速 (中性)
        weights['momentum_accel'] = 0.05
        
        return weights
    
    def generate_composite_score(self, factor_matrix: pd.DataFrame, 
                                weights: Dict = None) -> pd.Series:
        """生成综合因子得分"""
        if weights is None:
            weights = self.factor_weight_optimization(factor_matrix)
        
        # 标准化
        std_matrix = self.standardize_factors(factor_matrix)
        
        # 分类因子
        factor_groups = {
            'momentum': ['momentum_1m', 'momentum_3m', 'momentum_6m', 'relative_momentum'],
            'value': ['dividend_yield', 'earnings_yield', 'book_value', 'cashflow'],
            'quality': ['roe', 'roa', 'gross_margin', 'net_margin', 'asset_turnover'],
            'growth': ['revenue_growth', 'earnings_growth', 'roe_change'],
            'low_volatility': ['volatility_1m', 'volatility_3m', 'vol_change'],
            'size': ['size'],
            'liquidity': ['trading_volume', 'turnover_change'],
            'momentum_accel': ['momentum_accel', 'absolute_momentum']
        }
        
        # 计算每组因子得分
        group_scores = {}
        for group, factors in factor_groups.items():
            valid_factors = [f for f in factors if f in std_matrix.columns]
            if valid_factors:
                # 低波动因子取负
                if group == 'low_volatility':
                    group_scores[group] = -std_matrix[valid_factors].mean(axis=1)
                else:
                    group_scores[group] = std_matrix[valid_factors].mean(axis=1)
        
        # 加权求和
        composite = pd.Series(0.0, index=factor_matrix.index)
        for group, weight in weights.items():
            if group in group_scores:
                composite += weight * group_scores[group]
        
        return composite
    
    def get_top_etfs(self, factor_matrix: pd.DataFrame, 
                    n: int = 5, 
                    method: str = 'composite') -> List[str]:
        """获取Top ETF"""
        if method == 'composite':
            scores = self.generate_composite_score(factor_matrix)
        else:
            scores = factor_matrix.get(method, pd.Series())
        
        if scores.empty:
            return []
        
        return scores.sort_values(ascending=False).head(n).index.tolist()


# 测试
if __name__ == '__main__':
    model = TwentyFourFactorModel()
    
    # 测试单只ETF
    factors = model.calculate_all_factors('XLK')
    print("XLK 24因子:")
    for k, v in factors.items():
        if k != 'error':
            print(f"  {k}: {v}")
    
    # 批量计算
    tickers = ['XLK', 'XLV', 'XLF', 'XLY', 'XLE', 'SPY', 'QQQ']
    matrix = model.calculate_factor_matrix(tickers)
    print(f"\n因子矩阵 shape: {matrix.shape}")
    
    # 标准化
    std_matrix = model.standardize_factors(matrix)
    print(f"\n标准化后:\n{std_matrix.head()}")
    
    # 综合得分
    scores = model.generate_composite_score(matrix)
    print(f"\n综合得分:\n{scores.sort_values(ascending=False)}")

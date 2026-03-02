"""
24因子量化模型模块
==================

基于Barra多因子模型和业界标准量化因子构建的24因子系统。
用于ETF的量化分析和选股决策。

因子分类:
- 动量因子 (6个): 短期/中期/长期/动量加速/相对动量/绝对动量
- 价值因子 (4个): 股息率/PE/PB/PCF
- 质量因子 (5个): ROE/ROA/毛利率/净利率/资产周转率
- 成长因子 (3个): 营收增长/盈利增长/ROE变化
- 波动率因子 (3个): 20日/60日/波动率变化
- 规模因子 (1个): 市值
- 流动性因子 (2个): 成交量/换手率变化

Author: Financer AI
Date: 2026-03-02
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional
import yfinance as yf
from datetime import datetime, timedelta


class TwentyFourFactorModel:
    """
    24因子量化模型类
    
    提供完整的因子计算、数据处理和选股功能。
    继承自业界标准的Barra多因子框架。
    
    Attributes:
        factor_names: 24个因子的名称列表
    """
    
    # 因子名称列表 - 用于文档和验证
    factor_names = [
        # 动量因子 (6个)
        'momentum_1m',    # 1个月动量
        'momentum_3m',    # 3个月动量
        'momentum_6m',    # 6个月动量
        'momentum_accel', # 动量加速度
        'relative_momentum',  # 相对动量(vs市场)
        'absolute_momentum', # 绝对动量(趋势过滤)
        # 价值因子 (4个)
        'dividend_yield',    # 股息率
        'earnings_yield',    # 盈利收益率(1/E)
        'book_value',        # 账面价值(1/PB)
        'cashflow',          # 现金流(1/PCF)
        # 质量因子 (5个)
        'roe',               # 净资产收益率
        'roa',               # 总资产收益率
        'gross_margin',      # 毛利率
        'net_margin',        # 净利率
        'asset_turnover',    # 资产周转率
        # 成长因子 (3个)
        'revenue_growth',    # 营收增长
        'earnings_growth',   # 盈利增长
        'roe_change',        # ROE变化
        # 波动率因子 (3个)
        'volatility_1m',     # 20日波动率
        'volatility_3m',     # 60日波动率
        'vol_change',        # 波动率变化
        # 规模因子 (1个)
        'size',              # 市值(对数)
        # 流动性因子 (2个)
        'trading_volume',   # 成交量(对数)
        'turnover_change'    # 换手率变化
    ]
    
    def __init__(self):
        """初始化24因子模型"""
        pass
        
    def calculate_all_factors(self, ticker: str, period: str = '2y') -> Dict:
        """
        计算单只ETF的24个因子
        
        从Yahoo Finance获取数据，计算所有可用因子。
        某些因子(如基本面)可能因数据限制无法获取。
        
        Args:
            ticker: ETF代码,如'XLK'
            period: 数据周期,默认'2y'(2年)
            
        Returns:
            Dict: 包含24因子值的字典
            
        Example:
            >>> model = TwentyFourFactorModel()
            >>> factors = model.calculate_all_factors('XLK')
            >>> print(factors['momentum_1m'])
            5.23
        """
        factors = {'ticker': ticker}
        
        try:
            # ===== 数据获取 =====
            etf = yf.Ticker(ticker)
            hist = etf.history(period=period)
            info = etf.info
            
            if hist.empty:
                return {'ticker': ticker, 'error': 'No data'}
            
            prices = hist['Close']
            returns = prices.pct_change().dropna()
            volumes = hist['Volume']
            
            # ===== 1. 动量因子 (6个) =====
            # 说明: 动量因子衡量过去价格趋势的强度
            
            # 1.1 短期动量 (1个月 ≈ 21个交易日)
            if len(prices) >= 21:
                factors['momentum_1m'] = round((prices.iloc[-1] / prices.iloc[-21] - 1) * 100, 2)
            
            # 1.2 中期动量 (3个月 ≈ 63个交易日)
            if len(prices) >= 63:
                factors['momentum_3m'] = round((prices.iloc[-1] / prices.iloc[-63] - 1) * 100, 2)
            
            # 1.3 长期动量 (6个月 ≈ 126个交易日)
            if len(prices) >= 126:
                factors['momentum_6m'] = round((prices.iloc[-1] / prices.iloc[-126] - 1) * 100, 2)
            
            # 1.4 动量加速度 (短期动量 - 中期动量)
            # 意义: 动量在加速还是减速
            if 'momentum_1m' in factors and 'momentum_3m' in factors:
                factors['momentum_accel'] = round(factors['momentum_1m'] - factors['momentum_3m'], 2)
            
            # 1.5 相对动量 (vs 市场基准SPY)
            # 意义: 相对于市场的超额收益
            if len(prices) >= 63:
                market_data = yf.download('SPY', period=period, progress=False)['Close']
                if not market_data.empty:
                    etf_ret = (prices.iloc[-1] / prices.iloc[-63] - 1)
                    mkt_ret = (market_data.iloc[-1] / market_data.iloc[-63] - 1)
                    factors['relative_momentum'] = round((etf_ret - mkt_ret) * 100, 2)
            
            # 1.6 绝对动量 (趋势过滤)
            # 意义: 6个月是否上涨,用于过滤下跌趋势
            if 'momentum_6m' in factors:
                factors['absolute_momentum'] = 1 if factors['momentum_6m'] > 0 else 0
            
            # ===== 2. 价值因子 (4个) =====
            # 说明: 价值因子衡量估值水平,低估值可能预示高回报
            
            # 2.1 股息率 (Dividend Yield)
            if 'dividendYield' in info and info['dividendYield']:
                factors['dividend_yield'] = round(info['dividendYield'] * 100, 2)
            elif 'dividendRate' in info and 'currentPrice' in info and info['currentPrice']:
                factors['dividend_yield'] = round(info.get('dividendRate', 0) / info['currentPrice'] * 100, 2)
            else:
                factors['dividend_yield'] = 0
            
            # 2.2 盈利收益率 (Earnings Yield = 1/PE)
            if 'peRatio' in info and info['peRatio'] and info['peRatio'] > 0:
                factors['earnings_yield'] = round(100 / info['peRatio'], 2)
            else:
                factors['earnings_yield'] = 0
            
            # 2.3 账面价值 (Book Value = 1/PB)
            if 'priceToBook' in info and info['priceToBook'] and info['priceToBook'] > 0:
                factors['book_value'] = round(1 / info['priceToBook'], 2)
            else:
                factors['book_value'] = 0
            
            # 2.4 现金流 (Cashflow = 1/PCF)
            if 'priceToCashFlow' in info and info['priceToCashFlow'] and info['priceToCashFlow'] > 0:
                factors['cashflow'] = round(1 / info['priceToCashFlow'], 2)
            else:
                factors['cashflow'] = 0
            
            # ===== 3. 质量因子 (5个) =====
            # 说明: 质量因子衡量盈利能力和运营效率
            
            # 3.1 ROE (Return on Equity) - 净资产收益率
            if 'returnOnEquity' in info and info['returnOnEquity']:
                factors['roe'] = round(info['returnOnEquity'] * 100, 2)
            else:
                factors['roe'] = 0
            
            # 3.2 ROA (Return on Assets) - 总资产收益率
            if 'returnOnAssets' in info and info['returnOnAssets']:
                factors['roa'] = round(info['returnOnAssets'] * 100, 2)
            else:
                factors['roa'] = 0
            
            # 3.3 Gross Margin - 毛利率
            if 'grossMargins' in info and info['grossMargins']:
                factors['gross_margin'] = round(info['grossMargins'] * 100, 2)
            else:
                factors['gross_margin'] = 0
            
            # 3.4 Net Margin - 净利率
            if 'profitMargins' in info and info['profitMargins']:
                factors['net_margin'] = round(info['profitMargins'] * 100, 2)
            else:
                factors['net_margin'] = 0
            
            # 3.5 Asset Turnover - 资产周转率
            if 'assetTurnover' in info and info['assetTurnover']:
                factors['asset_turnover'] = round(info['assetTurnover'], 2)
            else:
                factors['asset_turnover'] = 0
            
            # ===== 4. 成长因子 (3个) =====
            # 说明: 成长因子衡量业绩增长速度
            
            # 4.1 Revenue Growth - 营收增长率
            if 'revenueGrowth' in info and info['revenueGrowth']:
                factors['revenue_growth'] = round(info['revenueGrowth'] * 100, 2)
            else:
                factors['revenue_growth'] = 0
            
            # 4.2 Earnings Growth - 盈利增长率
            if 'earningsGrowth' in info and info['earningsGrowth']:
                factors['earnings_growth'] = round(info['earningsGrowth'] * 100, 2)
            else:
                factors['earnings_growth'] = 0
            
            # 4.3 ROE Change - ROE变化(使用当前ROE作为代理)
            factors['roe_change'] = factors.get('roe', 0)
            
            # ===== 5. 波动率因子 (3个) =====
            # 说明: 波动率因子衡量风险,低波动通常有超额收益
            
            # 5.1 短期波动率 (20日年化)
            if len(returns) >= 20:
                factors['volatility_1m'] = round(returns.tail(20).std() * np.sqrt(252) * 100, 2)
            
            # 5.2 中期波动率 (60日年化)
            if len(returns) >= 60:
                factors['volatility_3m'] = round(returns.tail(60).std() * np.sqrt(252) * 100, 2)
            
            # 5.3 波动率变化 (短期 - 中期)
            if 'volatility_1m' in factors and 'volatility_3m' in factors:
                factors['vol_change'] = round(factors['volatility_1m'] - factors['volatility_3m'], 2)
            
            # ===== 6. 规模因子 (1个) =====
            # 说明: 市值规模,小市值通常有更高潜在回报
            
            # 6.1 Size - 市值(对数变换减少偏度)
            if 'totalAssets' in info and info['totalAssets']:
                factors['size'] = round(np.log(info['totalAssets'] + 1), 2)
            else:
                factors['size'] = 0
            
            # ===== 7. 流动性因子 (2个) =====
            # 说明: 流动性因子衡量交易活跃程度
            
            # 7.1 Trading Volume - 平均成交量(对数)
            if len(volumes) > 0:
                factors['trading_volume'] = round(np.log(volumes.iloc[-20:].mean() + 1), 2)
            
            # 7.2 Turnover Change - 换手率变化
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
        """
        计算多只ETF的因子矩阵
        
        Args:
            tickers: ETF代码列表
            
        Returns:
            DataFrame: 以ticker为索引的因子矩阵
            
        Example:
            >>> tickers = ['XLK', 'XLV', 'XLF']
            >>> matrix = model.calculate_factor_matrix(tickers)
            >>> matrix.shape
            (3, 24)
        """
        import time
        
        factor_list = []
        
        for ticker in tickers:
            print(f"  计算 {ticker} 因子...")
            factors = self.calculate_all_factors(ticker)
            factor_list.append(factors)
            # 避免请求过快
            time.sleep(0.2)
        
        df = pd.DataFrame(factor_list)
        return df.set_index('ticker')
    
    def standardize_factors(self, factor_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        因子Z-score标准化
        
        将每个因子转换为均值为0、标准差为1的分布，
        便于不同因子之间的比较和加权。
        
        Args:
            factor_matrix: 原始因子矩阵
            
        Returns:
            DataFrame: 标准化后的因子矩阵
        """
        standardized = factor_matrix.copy()
        
        for col in standardized.columns:
            # 跳过非数值列
            if col in ['ticker', 'error', 'success']:
                continue
            
            mean = standardized[col].mean()
            std = standardized[col].std()
            
            # Z-score公式: (x - mean) / std
            if std > 0:
                standardized[col] = (standardized[col] - mean) / std
            else:
                standardized[col] = 0  # 常数列设为0
        
        return standardized
    
    def winsorize_factors(self, factor_matrix: pd.DataFrame, 
                         lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
        """
        因子去极值 (Winsorize)
        
        将超出指定分位数的值替换为分位数边界值，
        减少极端值对分析的影響。
        
        Args:
            factor_matrix: 原始因子矩阵
            lower: 下界分位数 (默认1%)
            upper: 上界分位数 (默认99%)
            
        Returns:
            DataFrame: 去极值后的因子矩阵
            
        Example:
            >>> # 1%和99%分位数之外的会被裁剪
            >>> clean_matrix = model.winsorize_factors(matrix)
        """
        winsorized = factor_matrix.copy()
        
        for col in winsorized.columns:
            if col in ['ticker', 'error', 'success']:
                continue
            
            # 转换为数值类型,无效值设为NaN
            winsorized[col] = pd.to_numeric(winsorized[col], errors='coerce')
            
            # 跳过数据不足的列
            if winsorized[col].notna().sum() < 2:
                continue
            
            try:
                # 计算分位数边界
                lower_val = winsorized[col].quantile(lower)
                upper_val = winsorized[col].quantile(upper)
                
                # 裁剪到边界范围内
                winsorized[col] = winsorized[col].clip(lower_val, upper_val)
            except:
                pass
        
        return winsorized
    
    def neutralize_factors(self, factor_matrix: pd.DataFrame, 
                          neutralize_on: List[str] = None) -> pd.DataFrame:
        """
        因子中性化
        
        去除因子与规模因子的相关性,使因子更纯粹地反映
        该因子自身的预测能力。
        
        Args:
            factor_matrix: 因子矩阵
            neutralize_on: 需要中性化的因子列表
            
        Returns:
            DataFrame: 中性化后的因子矩阵
        """
        if neutralize_on is None:
            neutralize_on = ['size']
        
        neutral = factor_matrix.copy()
        
        # 对每个因子回归规模因子,保留残差
        for col in neutral.columns:
            if col in ['ticker', 'error', 'success'] or col in neutralize_on:
                continue
            
            if 'size' in neutral.columns:
                valid = neutral[col].notna() & neutral['size'].notna()
                if valid.sum() > 10:
                    try:
                        # 线性回归
                        slope, intercept, _, _, _ = stats.linregress(
                            neutral.loc[valid, 'size'],
                            neutral.loc[valid, col]
                        )
                        # 残差 = 原始值 - 规模影响
                        neutral.loc[valid, col] = neutral.loc[valid, col] - slope * neutral.loc[valid, 'size']
                    except:
                        pass
        
        return neutral
    
    def calculate_factor_returns(self, factor_matrix: pd.DataFrame, 
                                 forward_returns: pd.Series) -> pd.DataFrame:
        """
        计算因子IC (Information Coefficient)
        
        衡量因子对未来收益的预测能力。
        IC > 0 表示正相关, IC < 0 表示负相关。
        
        Args:
            factor_matrix: 因子矩阵
            forward_returns: 未来收益序列
            
        Returns:
            DataFrame: 包含IC值和显著性的因子分析结果
        """
        ic_results = []
        
        for col in factor_matrix.columns:
            if col in ['ticker', 'error', 'success']:
                continue
            
            # 筛选有效数据
            valid = factor_matrix[col].notna() & forward_returns.notna()
            
            if valid.sum() > 5:
                # Spearman秩相关(对非线性关系更鲁棒)
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
        
        根据因子类别和有效性分配权重。
        动量因子权重较高,因为在ETF轮动中表现较好。
        
        Args:
            factor_matrix: 因子矩阵(未使用,保留扩展)
            target_vol: 目标波动率(默认15%)
            
        Returns:
            Dict: 各类因子的权重配置
            
        Note:
            权重分配逻辑:
            - 动量: 25% (在趋势行情中表现好)
            - 质量: 20% (稳定性重要)
            - 低波动: 15% (风险控制)
            - 价值: 15% (估值保护)
            - 成长: 10% (增长潜力)
            - 流动性: 5% (交易便利)
            - 规模: 5% (市值中性)
            - 动量加速: 5% (趋势强度)
        """
        # 固定权重配置 - 基于学术研究和实践验证
        weights = {
            'momentum': 0.25,       # 动量因子
            'value': 0.15,          # 价值因子
            'quality': 0.20,        # 质量因子
            'growth': 0.10,         # 成长因子
            'low_volatility': 0.15, # 低波动因子
            'size': 0.05,           # 规模因子
            'liquidity': 0.05,      # 流动性因子
            'momentum_accel': 0.05  # 动量加速
        }
        
        return weights
    
    def generate_composite_score(self, factor_matrix: pd.DataFrame, 
                                weights: Dict = None) -> pd.Series:
        """
        生成综合因子得分
        
        将多个因子按权重加权求和,得到最终的选股得分。
        低波动因子取负,因为波动越低越好。
        
        Args:
            factor_matrix: 因子矩阵
            weights: 因子权重配置
            
        Returns:
            Series: 综合得分,按得分降序排列
            
        Example:
            >>> scores = model.generate_composite_score(matrix)
            >>> top_etfs = scores.sort_values(ascending=False).head(5)
        """
        if weights is None:
            weights = self.factor_weight_optimization(factor_matrix)
        
        # 标准化
        std_matrix = self.standardize_factors(factor_matrix)
        
        # 因子分组
        factor_groups = {
            'momentum': ['momentum_1m', 'momentum_3m', 'momentum_6m', 'relative_momentum'],
            'value': ['dividend_yield', 'earnings_yield', 'book_value', 'cashflow'],
            'quality': ['roe', 'roa', 'gross_margin', 'net_margin', 'asset_turnover'],
            'venue_growth',growth': ['re 'earnings_growth', 'roe_change'],
            'low_volatility': ['volatility_1m', 'volatility_3m', 'volsize': ['size_change'],
            ''],
            'liquidity': ['trading_volume', 'turnover_change'],
            'momentum_accel': ['momentum_accel', 'absolute_momentum']
        }
        
        #得分 ( 计算每组因子组内简单平均)
        group_scores = {}
        for group, factors in factor_groups.items():
            valid_factors = [f for f in factors if f in std_matrix.columns]
            if valid_factors:
                if group == 'low_volatility':
                    # 低波动取负,低波动=高分
                    group_scores[group] = -std_matrix[valid_factors].mean(axis=1)
                else:
                    group_scores[group] = std_matrix[valid_factors].mean(axis=1)
        
        # 加权求和得到综合得分
        composite = pd.Series(0.0, index=factor_matrix.index)
        for group, weight in weights.items():
            if group in group_scores:
                composite += weight * group_scores[group]
        
        return composite
    
    def get_top_etfs(self, factor_matrix: pd.DataFrame, 
                    n: int = 5, 
                    method: str = 'composite') -> List[str]:
        """
        获取Top N ETF
        
        Args:
            factor_matrix: 因子矩阵
            n: 返回数量
            method: 排序方法 ('composite'或因子名)
            
        Returns:
            List: Top N ETF代码列表
        """
        if method == 'composite':
            scores = self.generate_composite_score(factor_matrix)
        else:
            scores = factor_matrix.get(method, pd.Series())
        
        if scores.empty:
            return []
        
        return scores.sort_values(ascending=False).head(n).index.tolist()


# ===== 模块测试 =====
if __name__ == '__main__':
    # 创建模型实例
    model = TwentyFourFactorModel()
    
    # 测试单只ETF
    print("测试计算XLK的24因子...")
    factors = model.calculate_all_factors('XLK')
    print(f"成功: {factors.get('success', False)}")
    print(f"动量因子: {factors.get('momentum_1m')}%")
    print(f"波动率: {factors.get('volatility_1m')}%")
    
    # 批量计算
    tickers = ['XLK', 'XLV', 'XLF', 'XLY', 'XLE', 'SPY', 'QQQ']
    print(f"\n批量计算 {len(tickers)} 个ETF...")
    matrix = model.calculate_factor_matrix(tickers)
    print(f"因子矩阵形状: {matrix.shape}")
    
    # 标准化
    std_matrix = model.standardize_factors(matrix)
    print(f"标准化完成")
    
    # 综合得分
    scores = model.generate_composite_score(matrix)
    print(f"\n综合得分排名:")
    print(scores.sort_values(ascending=False))

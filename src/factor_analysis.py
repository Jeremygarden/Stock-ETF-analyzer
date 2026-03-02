"""
专业因子分析模块
包含:
- 因子计算
- 因子正交化
- IC分析
- 因子有效性检验
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple


class FactorAnalyzer:
    """因子分析器"""
    
    def __init__(self):
        self.factor_returns = None
        self.ic_matrix = None
        
    def calculate_ic(self, factor_values: pd.Series, forward_returns: pd.Series) -> Dict:
        """
        计算Information Coefficient (IC)
        衡量因子预测能力
        """
        # 去除NaN
        valid = factor_values.notna() & forward_returns.notna()
        f = factor_values[valid]
        r = forward_returns[valid]
        
        if len(f) < 10:
            return {'ic': 0, 'p_value': 1}
        
        # Pearson相关系数
        ic, p_value = stats.pearsonr(f, r)
        
        # Spearman秩相关
        spearman_ic, spearman_p = stats.spearmanr(f, r)
        
        return {
            'ic': round(ic, 4),
            'ic_p_value': round(p_value, 4),
            'rank_ic': round(spearman_ic, 4),
            'rank_ic_p_value': round(spearman_p, 4),
            'n_observations': len(f)
        }
    
    def calculate_rolling_ic(self, factor_df: pd.DataFrame, returns: pd.Series, 
                            window: int = 12) -> pd.Series:
        """
        计算滚动IC序列
        检验因子稳定性
        """
        rolling_ic = []
        dates = []
        
        for i in range(window, len(factor_df)):
            subset_factors = factor_df.iloc[i-window:i]
            subset_returns = returns.iloc[i-window:i]
            
            ic_vals = []
            for col in subset_factors.columns:
                ic = subset_factors[col].corr(subset_returns)
                if not np.isnan(ic):
                    ic_vals.append(ic)
            
            if ic_vals:
                rolling_ic.append(np.mean(ic_vals))
                dates.append(factor_df.index[i])
        
        return pd.Series(rolling_ic, index=dates)
    
    def factor_neutralization(self, factor_matrix: pd.DataFrame, 
                              neutralize_cols: List[str] = None) -> pd.DataFrame:
        """
        因子正交化
        去除因子间的共线性
        """
        if neutralize_cols is None:
            neutralize_cols = ['momentum_20d', 'volatility_20d', 'dividend_yield']
        
        # 只保留数值列
        numeric_cols = [c for c in factor_matrix.columns 
                      if c != 'ticker' and factor_matrix[c].dtype in [np.float64, np.int64]]
        
        # 构建因子矩阵
        X = factor_matrix[numeric_cols].fillna(0)
        
        # 逐步正交化
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                # 回归
                valid = X[col1].notna() & X[col2].notna() & (X[col1] != X[col1].iloc[0])
                if valid.sum() > 10:
                    try:
                        slope, intercept, _, _, _ = stats.linregress(
                            X.loc[valid, col1], X.loc[valid, col2]
                        )
                        # 从col2中去除col1的影响
                        X.loc[valid, col2] = X.loc[valid, col2] - slope * X.loc[valid, col1]
                    except:
                        pass  # 跳过无法回归的情况
        
        result = factor_matrix.copy()
        result[numeric_cols] = X
        
        return result
    
    def calculate_factor_returns_regression(self, factor_matrix: pd.DataFrame, 
                                           returns: pd.Series) -> pd.DataFrame:
        """
        使用回归计算因子收益率
        """
        # 准备因子矩阵
        factor_cols = [c for c in factor_matrix.columns if c != 'ticker']
        X = factor_matrix[factor_cols].fillna(0)
        X = X.reset_index(drop=True)
        
        # 对齐收益率
        if len(returns) != len(X):
            min_len = min(len(returns), len(X))
            X = X.iloc[:min_len]
            returns = returns.iloc[:min_len]
        
        # OLS回归
        from scipy import linalg
        
        X_with_const = np.column_stack([np.ones(len(X)), X.values])
        
        try:
            coeffs, residuals, rank, s = linalg.lstsq(X_with_const, returns.values)
            
            factor_returns = pd.Series(coeffs[1:], index=factor_cols)
            return factor_returns
            
        except Exception as e:
            print(f"回归失败: {e}")
            return pd.Series()
    
    def quantile_analysis(self, factor_matrix: pd.DataFrame, returns: pd.Series,
                        factor_name: str, n_quantiles: int = 5) -> Dict:
        """
        分位数分析
        检验因子分组的收益差异
        """
        # 对因子排序分组
        valid = factor_matrix[factor_name].notna() & returns.notna()
        f = factor_matrix.loc[valid, factor_name]
        r = returns[valid]
        
        if len(f) < n_quantiles:
            return {}
        
        # 分位数
        quantiles = pd.qcut(f, n_quantiles, labels=False, duplicates='drop')
        
        # 计算每个分位数的收益
        quantile_returns = []
        for q in range(n_quantiles):
            mask = quantiles == q
            if mask.sum() > 0:
                avg_ret = r[mask].mean()
                quantile_returns.append({
                    'quantile': q + 1,
                    'avg_return': avg_ret,
                    'count': mask.sum()
                })
        
        # 计算Long-Short收益
        if len(quantile_returns) >= 2:
            long_short = quantile_returns[-1]['avg_return'] - quantile_returns[0]['avg_return']
            spread_std = np.std([q['avg_return'] for q in quantile_returns])
            t_stat = long_short / (spread_std / np.sqrt(len(quantile_returns))) if spread_std > 0 else 0
        else:
            long_short = 0
            t_stat = 0
        
        return {
            'quantile_returns': quantile_returns,
            'long_short_return': round(long_short * 100, 2),
            't_statistic': round(t_stat, 2),
            'spread': round(spread_std * 100, 2) if 'spread_std' in locals() else 0
        }
    
    def factor_correlation_matrix(self, factor_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子相关性矩阵
        检测多重共线性
        """
        numeric_cols = [c for c in factor_matrix.columns 
                      if c != 'ticker' and factor_matrix[c].dtype in [np.float64, np.int64]]
        
        return factor_matrix[numeric_cols].corr()
    
    def calculate_portfolio_metrics(self, factor_matrix: pd.DataFrame, 
                                    weights: Dict[str, float]) -> Dict:
        """
        计算组合的因子暴露
        """
        # 归一化权重
        total = sum(weights.values())
        norm_weights = {k: v/total for k, v in weights.items()}
        
        # 匹配因子数据
        exposures = {}
        
        for factor in factor_matrix.columns:
            if factor == 'ticker':
                continue
            
            exp = 0
            for ticker, w in norm_weights.items():
                row = factor_matrix[factor_matrix['ticker'] == ticker]
                if not row.empty:
                    exp += w * row[factor].values[0]
            
            exposures[factor] = round(exp, 4)
        
        return exposures


class PortfolioOptimizer:
    """组合优化器"""
    
    def __init__(self):
        self.risk_free_rate = 0.03
        
    def mean_variance_optimization(self, returns: pd.Series, 
                                  factor_exposures: pd.DataFrame = None,
                                  risk_aversion: float = 1.0) -> Dict:
        """
        均值方差优化
        """
        # 简化实现
        n = len(returns)
        
        if n == 0:
            return {}
        
        # 期望收益
        expected_returns = returns.mean() * 12  # 年化
        
        # 协方差矩阵 (简化)
        cov_matrix = returns.cov() * 12
        
        # 最优化权重
        inv_cov = np.linalg.pinv(cov_matrix.values)
        ones = np.ones(len(returns))
        
        # 解析解
        numerator = inv_cov @ expected_returns.values - risk_aversion * ones
        denominator = ones @ invCov @ ones
        
        weights = numerator / denominator
        
        # 转为字典
        portfolio = {}
        for i, ticker in enumerate(returns.index):
            if weights[i] > 0.01:  # 只保留>1%的持仓
                portfolio[ticker] = round(weights[i], 4)
        
        return portfolio
    
    def risk_parity(self, returns: pd.Series) -> Dict:
        """
        风险平价组合
        """
        # 波动率
        vol = returns.std() * np.sqrt(12)
        
        # 逆波动率权重
        inv_vol = 1 / (vol + 0.001)
        weights = inv_vol / inv_vol.sum()
        
        portfolio = {}
        for i, ticker in enumerate(returns.index):
            if weights.iloc[i] > 0.01:
                portfolio[ticker] = round(weights.iloc[i], 4)
        
        return portfolio
    
    def maximum_diversification(self, returns: pd.Series) -> Dict:
        """
        最大分散化组合
        """
        vol = returns.std() * np.sqrt(12)
        
        # 分散化比率权重
        weights = vol / vol.sum()
        
        portfolio = {}
        for i, ticker in enumerate(returns.index):
            if weights.iloc[i] > 0.01:
                portfolio[ticker] = round(weights.iloc[i], 4)
        
        return portfolio
    
    def black_litterman(self, views: Dict[str, float], 
                       cov_matrix: pd.DataFrame,
                       market_cap_weights: pd.Series = None,
                       tau: float = 0.05) -> Dict:
        """
        Black-Litterman模型
        融合主观观点与市场均衡收益
        """
        # 简化实现
        # 1. 市场均衡收益
        if market_cap_weights is None:
            market_cap_weights = pd.Series(1/len(cov_matrix), index=cov_matrix.index)
        
        # 2. 观点收益
        view_returns = pd.Series(views)
        
        # 3. 混合
        # 简化: 50%市场 + 50%观点
        combined = 0.5 * market_cap_weights + 0.5 * view_returns
        
        # 4. 重新优化
        return self.risk_parity(combined)


def calculate_factor_ic_series(factor_data: pd.DataFrame, 
                               returns: pd.Series, 
                               factor_name: str) -> pd.Series:
    """计算因子的IC时间序列"""
    ic_series = []
    
    # 月度滚动IC
    for i in range(20, len(factor_data)):
        window_factors = factor_data.iloc[i-20:i]
        window_returns = returns.iloc[i-20:i]
        
        valid = window_factors[factor_name].notna() & window_returns.notna()
        
        if valid.sum() > 5:
            ic = window_factors.loc[valid, factor_name].corr(window_returns[valid])
            ic_series.append(ic)
    
    return pd.Series(ic_series)


def generate_factor_report(factor_matrix: pd.DataFrame, returns: pd.Series) -> Dict:
    """生成完整因子分析报告"""
    analyzer = FactorAnalyzer()
    
    report = {
        'factor_list': [c for c in factor_matrix.columns if c != 'ticker'],
        'factor_correlations': analyzer.factor_correlation_matrix(factor_matrix).to_dict(),
        'quantile_analysis': {},
        'ic_analysis': {}
    }
    
    # 每个因子的分位数分析
    for factor in ['momentum_20d', 'volatility_20d', 'dividend_yield']:
        if factor in factor_matrix.columns:
            report['quantile_analysis'][factor] = analyzer.quantile_analysis(
                factor_matrix, returns, factor
            )
    
    return report


if __name__ == '__main__':
    # 测试
    import yfinance as yf
    
    # 下载数据
    tickers = ['XLK', 'XLV', 'XLF', 'XLY', 'XLE', 'SPY']
    data = yf.download(tickers, period='2y', progress=False)['Close']
    returns = data.pct_change().dropna()
    
    # 创建模拟因子数据
    factor_data = pd.DataFrame({
        'ticker': tickers,
        'momentum_20d': [5, 3, 2, 4, 1, 3],
        'volatility_20d': [20, 15, 18, 22, 25, 12],
        'dividend_yield': [1.2, 1.5, 2.0, 1.0, 2.5, 1.4]
    })
    
    # 测试IC计算
    analyzer = FactorAnalyzer()
    ic = analyzer.calculate_ic(
        factor_data.set_index('ticker')['momentum_20d'],
        returns.iloc[-1]
    )
    print(f"IC: {ic}")

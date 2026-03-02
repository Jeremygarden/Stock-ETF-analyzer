"""
高级回测指标模块
================

提供专业的回测分析功能,包括:
- 基础收益指标 (总收益、夏普比率等)
- 风险指标 (VaR、CVaR、最大回撤等)
- 尾部风险 (偏度、峰度、盈亏比)
- 稳定性检验 (防止过拟合)
- Walk-forward滚动向前分析
- Monte Carlo模拟
- Bootstrap置信区间

这些工具帮助评估策略的真实表现,避免过拟合。

Author: Financer AI
Date: 2026-03-02
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class AdvancedBacktestMetrics:
    """
    高级回测指标计算器
    
    用于全面评估量化策略的表现,包含多种防止过拟合的检验方法。
    """
    
    def __init__(self):
        self.results = {}
    
    def calculate_all_metrics(self, returns, equity_curve=None, risk_free_rate=0.03):
        """
        计算完整的回测指标体系
        
        综合评估策略的收益、风险和稳定性。
        
        Args:
            returns: 月度收益率序列
            equity_curve: 权益曲线(可选)
            risk_free_rate: 无风险利率(默认3%)
            
        Returns:
            Dict: 包含所有指标的字典
        """
        if returns.empty:
            return {}
        
        # 基础指标
        basic = self._basic_metrics(returns, equity_curve, risk_free_rate)
        
        # 风险指标
        risk = self._risk_metrics(returns, risk_free_rate)
        
        # 尾部风险指标
        tail = self._tail_metrics(returns)
        
        # 滚动稳定性指标
        stability = self._stability_metrics(returns)
        
        # 组合所有指标
        all_metrics = {**basic, **risk, **tail, **stability}
        
        return all_metrics
    
    def _basic_metrics(self, returns, equity_curve, risk_free_rate):
        """基础收益指标"""
        if equity_curve is None:
            equity_curve = (1 + returns).cumprod()
        
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) if len(equity_curve) > 1 else 0
        
        # 年化
        n_years = len(returns) / 12
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        annual_vol = returns.std() * np.sqrt(12)
        
        # 夏普比率
        sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'annual_volatility': round(annual_vol * 100, 2),
            'sharpe_ratio': round(sharpe, 3),
        }
    
    def _risk_metrics(self, returns, risk_free_rate):
        """风险指标"""
        # 最大回撤
        equity = (1 + returns).cumprod()
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        # 回撤持续时间
        dd_duration = self._max_drawdown_duration(drawdown)
        
        # Sortino比率 (只考虑下行风险)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(12) if len(downside_returns) > 0 else 0
        annual_return = returns.mean() * 12
        sortino = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # 信息比率 (相对于基准)
        # 简化: 使用零收益作为基准
        excess_returns = returns
        tracking_error = excess_returns.std() * np.sqrt(12)
        info_ratio = (excess_returns.mean() * 12) / tracking_error if tracking_error > 0 else 0
        
        # Calmar比率
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # VaR (Value at Risk) - 95%
        var_95 = np.percentile(returns, 5)
        
        # CVaR (Conditional VaR) - 预期尾部损失
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        
        return {
            'max_drawdown': round(max_dd * 100, 2),
            'max_drawdown_duration': dd_duration,
            'sortino_ratio': round(sortino, 3),
            'calmar_ratio': round(calmar, 3),
            'var_95': round(var_95 * 100, 2),
            'cvar_95': round(cvar_95 * 100, 2),
            'info_ratio': round(info_ratio, 3),
        }
    
    def _max_drawdown_duration(self, drawdown):
        """计算最大回撤持续时间"""
        # 找到回撤开始和恢复的月份
        in_drawdown = drawdown < 0
        max_duration = 0
        current_duration = 0
        
        for dd in in_drawdown:
            if dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration
    
    def _tail_metrics(self, returns):
        """尾部风险指标"""
        # 偏度 (Skewness)
        skewness = stats.skew(returns)
        
        # 峰度 (Kurtosis)
        kurtosis = stats.kurtosis(returns)
        
        # 尾比率 (Tail Ratio) - 右尾/左尾
        right_tail = abs(returns[returns > 0].mean()) if len(returns[returns > 0]) > 0 else 0
        left_tail = abs(returns[returns < 0].mean()) if len(returns[returns < 0]) > 0 else 0
        tail_ratio = right_tail / left_tail if left_tail > 0 else 0
        
        # 盈利/亏损比
        avg_win = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
        avg_loss = abs(returns[returns < 0].mean()) if len(returns[returns < 0]) > 0 else 0
        gain_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 胜率
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
        
        # 月度盈利比例
        monthly_positive = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
        
        return {
            'skewness': round(skewness, 3),
            'kurtosis': round(kurtosis, 3),
            'tail_ratio': round(tail_ratio, 3),
            'gain_loss_ratio': round(gain_loss_ratio, 3),
            'win_rate': round(win_rate * 100, 2),
            'monthly_positive_rate': round(monthly_positive * 100, 2),
        }
    
    def _stability_metrics(self, returns):
        """稳定性指标 - 防止过拟合"""
        # 滚动夏普比率
        if len(returns) >= 12:
            rolling_sharpe = returns.rolling(12).apply(
                lambda x: x.mean() / x.std() * np.sqrt(12) if x.std() > 0 else 0
            )
            sharpe_stability = rolling_sharpe.std()
        else:
            sharpe_stability = 0
        
        # 收益一致性
        returns_consistency = 1 - returns.std() / (abs(returns.mean()) + 0.001)
        
        # 滚动最大回撤
        if len(returns) >= 12:
            rolling_dd = returns.rolling(12).apply(
                lambda x: self._calc_max_dd(x)
            )
            dd_stability = rolling_dd.std()
        else:
            dd_stability = 0
        
        return {
            'sharpe_stability': round(sharpe_stability, 3),
            'returns_consistency': round(returns_consistency, 3),
            'drawdown_stability': round(dd_stability, 3),
        }
    
    def _calc_max_dd(self, returns):
        """计算单期最大回撤"""
        equity = (1 + returns).cumprod()
        rolling_max = equity.cummax()
        dd = (equity - rolling_max) / rolling_max
        return dd.min()
    
    def walk_forward_analysis(self, returns, train_months=18, test_months=6):
        """
        滚动向前分析 (Walk-forward)
        防止过拟合: 只使用历史数据训练, 在未见数据上测试
        """
        results = []
        
        total_months = len(returns)
        
        for start in range(0, total_months - train_months - test_months, test_months):
            train_end = start + train_months
            test_end = min(start + train_months + test_months, total_months)
            
            train_returns = returns.iloc[start:train_end]
            test_returns = returns.iloc[train_end:test_end]
            
            if len(train_returns) < 12 or len(test_returns) < 3:
                continue
            
            # 训练集表现
            train_metrics = self.calculate_all_metrics(train_returns)
            
            # 测试集表现
            test_metrics = self.calculate_all_metrics(test_returns)
            
            results.append({
                'train_period': f"{train_returns.index[0].strftime('%Y-%m')} ~ {train_returns.index[-1].strftime('%Y-%m')}",
                'test_period': f"{test_returns.index[0].strftime('%Y-%m')} ~ {test_returns.index[-1].strftime('%Y-%m')}",
                'train_sharpe': train_metrics.get('sharpe_ratio', 0),
                'test_sharpe': test_metrics.get('sharpe_ratio', 0),
                'train_return': train_metrics.get('annual_return', 0),
                'test_return': test_metrics.get('annual_return', 0),
                'train_drawdown': train_metrics.get('max_drawdown', 0),
                'test_drawdown': test_metrics.get('max_drawdown', 0),
            })
        
        return results
    
    def monte_carlo_simulation(self, returns, n_simulations=1000, n_periods=24):
        """
        蒙特卡洛模拟
        通过随机重采样评估策略稳健性
        """
        # 参数
        mu = returns.mean()
        sigma = returns.std()
        
        simulations = []
        
        for _ in range(n_simulations):
            # 随机生成收益序列
            random_returns = np.random.normal(mu, sigma, n_periods)
            sim_returns = pd.Series(random_returns, index=range(n_periods))
            
            # 计算模拟收益
            equity = (1 + sim_returns).cumprod()
            total_ret = equity.iloc[-1] - 1
            
            simulations.append({
                'total_return': total_ret,
                'sharpe': (sim_returns.mean() * 12) / (sim_returns.std() * np.sqrt(12)) if sim_returns.std() > 0 else 0,
                'max_dd': self._calc_series_max_dd(equity),
            })
        
        sim_df = pd.DataFrame(simulations)
        
        return {
            'mean_return': round(sim_df['total_return'].mean() * 100, 2),
            'return_std': round(sim_df['total_return'].std() * 100, 2),
            'return_5pct': round(sim_df['total_return'].quantile(0.05) * 100, 2),
            'return_95pct': round(sim_df['total_return'].quantile(0.95) * 100, 2),
            'mean_sharpe': round(sim_df['sharpe'].mean(), 2),
            'sharpe_5pct': round(sim_df['sharpe'].quantile(0.05), 2),
            'prob_positive': (sim_df['total_return'] > 0).mean() * 100,
        }
    
    def _calc_series_max_dd(self, equity):
        """计算序列最大回撤"""
        rolling_max = equity.cummax()
        dd = (equity - rolling_max) / rolling_max
        return dd.min()
    
    def bootstrap_confidence(self, returns, n_bootstrap=500):
        """
        Bootstrap置信区间
        评估指标的不确定性
        """
        sharpes = []
        returns_list = []
        max_dds = []
        
        for _ in range(n_bootstrap):
            # 随机有放回抽样
            bootstrap = returns.sample(n=len(returns), replace=True)
            
            if len(bootstrap) < 3:
                continue
            
            # 计算指标
            ann_ret = bootstrap.mean() * 12
            ann_vol = bootstrap.std() * np.sqrt(12)
            sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
            
            equity = (1 + bootstrap).cumprod()
            dd = self._calc_series_max_dd(equity)
            
            sharpes.append(sharpe)
            returns_list.append(ann_ret)
            max_dds.append(dd)
        
        return {
            'sharpe_ci_lower': round(np.percentile(sharpes, 5), 3),
            'sharpe_ci_upper': round(np.percentile(sharpes, 95), 3),
            'return_ci_lower': round(np.percentile(returns_list, 5) * 100, 2),
            'return_ci_upper': round(np.percentile(returns_list, 95) * 100, 2),
            'dd_ci_lower': round(np.percentile(max_dds, 5) * 100, 2),
            'dd_ci_upper': round(np.percentile(max_dds, 95) * 100, 2),
        }
    
    def regime_analysis(self, returns):
        """
        市场状态分析
        评估策略在不同市场环境下的表现
        """
        # 简单划分: 上涨/下跌市场
        bull_market = returns[returns > 0]
        bear_market = returns[returns < 0]
        
        # 波动率 regime
        low_vol = returns[returns.rolling(3).std() < returns.std()]
        high_vol = returns[returns.rolling(3).std() >= returns.std()]
        
        return {
            'bull_return': round(bull_market.mean() * 100, 2) if len(bull_market) > 0 else 0,
            'bear_return': round(bear_market.mean() * 100, 2) if len(bear_market) > 0 else 0,
            'low_vol_return': round(low_vol.mean() * 100, 2) if len(low_vol) > 0 else 0,
            'high_vol_return': round(high_vol.mean() * 100, 2) if len(high_vol) > 0 else 0,
            'recovery_ratio': round(len(bull_market) / len(bear_market), 2) if len(bear_market) > 0 else 0,
        }
    
    def generate_report(self, returns, equity_curve=None):
        """生成完整回测报告"""
        metrics = self.calculate_all_metrics(returns, equity_curve)
        
        # 滚动向前分析
        wf_results = self.walk_forward_analysis(returns)
        
        # 蒙特卡洛
        mc_results = self.monte_carlo_simulation(returns)
        
        # Bootstrap
        bootstrap = self.bootstrap_confidence(returns)
        
        # 市场状态
        regimes = self.regime_analysis(returns)
        
        return {
            'metrics': metrics,
            'walk_forward': wf_results,
            'monte_carlo': mc_results,
            'bootstrap': bootstrap,
            'regimes': regimes,
        }


def print_advanced_report(report):
    """打印高级回测报告"""
    print("\n" + "="*70)
    print("📊 高级回测分析报告")
    print("="*70)
    
    m = report['metrics']
    
    print("\n🎯 收益与风险:")
    print(f"   年化收益: {m.get('annual_return', 0):+.1f}%")
    print(f"   年化波动: {m.get('annual_volatility', 0):.1f}%")
    print(f"   夏普比率: {m.get('sharpe_ratio', 0):.2f}")
    print(f"   Sortino: {m.get('sortino_ratio', 0):.2f}")
    
    print("\n🛡️ 风险控制:")
    print(f"   最大回撤: {m.get('max_drawdown', 0):.1f}%")
    print(f"   回撤持续: {m.get('max_drawdown_duration', 0)}个月")
    print(f"   VaR(95%): {m.get('var_95', 0):.2f}%")
    print(f"   CVaR(95%): {m.get('cvar_95', 0):.2f}%")
    
    print("\n📈 尾部特征:")
    print(f"   偏度: {m.get('skewness', 0):.2f}")
    print(f"   峰度: {m.get('kurtosis', 0):.2f}")
    print(f"   尾比率: {m.get('tail_ratio', 0):.2f}")
    print(f"   盈亏比: {m.get('gain_loss_ratio', 0):.2f}")
    print(f"   胜率: {m.get('win_rate', 0):.1f}%")
    
    print("\n🔬 稳定性检验:")
    print(f"   夏普稳定性: {m.get('sharpe_stability', 0):.3f}")
    print(f"   收益一致性: {m.get('returns_consistency', 0):.3f}")
    
    mc = report['monte_carlo']
    print("\n🎲 蒙特卡洛模拟 (1000次):")
    print(f"   期望收益: {mc.get('mean_return', 0):+.1f}%")
    print(f"   收益标准差: {mc.get('return_std', 0):.1f}%")
    print(f"   5%分位收益: {mc.get('return_5pct', 0):+.1f}%")
    print(f"   95%分位收益: {mc.get('return_95pct', 0):+.1f}%")
    print(f"   正收益概率: {mc.get('prob_positive', 0):.1f}%")
    
    bs = report['bootstrap']
    print("\n📐 Bootstrap 95%置信区间:")
    print(f"   夏普: [{bs.get('sharpe_ci_lower', 0):.2f}, {bs.get('sharpe_ci_upper', 0):.2f}]")
    print(f"   收益: [{bs.get('return_ci_lower', 0):+.1f}%, {bs.get('return_ci_upper', 0):+.1f}%]")
    
    reg = report['regimes']
    print("\n🌊 市场状态分析:")
    print(f"   牛市月均: {reg.get('bull_return', 0):+.2f}%")
    print(f"   熊市月均: {reg.get('bear_return', 0):.2f}%")
    print(f"   低波动月均: {reg.get('low_vol_return', 0):+.2f}%")
    print(f"   高波动月均: {reg.get('high_vol_return', 0):+.2f}%")
    
    wf = report.get('walk_forward', [])
    if wf:
        print("\n🔄 Walk-forward分析:")
        print(f"   {'训练期':<20} {'测试期':<20} {'训练夏普':<10} {'测试夏普':<10}")
        print("   " + "-"*60)
        for r in wf[:5]:
            print(f"   {r['train_period']:<20} {r['test_period']:<20} {r['train_sharpe']:<10.2f} {r['test_sharpe']:<10.2f}")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    # 测试
    import yfinance as yf
    
    # 下载测试数据
    data = yf.download('SPY', start='2023-01-01', end='2025-01-01', progress=False)
    returns = data['Close'].pct_change().dropna()
    
    analyzer = AdvancedBacktestMetrics()
    report = analyzer.generate_report(returns)
    print_advanced_report(report)

"""
ETF轮动系统回测模块
用于验证策略的历史表现
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')


class ETFBacktester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.results = {}
        
    def run_backtest(self, etf_tickers, strategy='momentum', start_date=None, end_date=None):
        """
        运行回测
        
        Parameters:
        - etf_tickers: ETF代码列表
        - strategy: 策略类型 ['momentum', 'dual_momentum', 'risk_parity', 'advanced']
        - start_date: 回测开始日期
        - end_date: 回测结束日期
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)  # 默认1年
        
        print(f"\n{'='*60}")
        print(f"📊 ETF轮动系统回测")
        print(f"{'='*60}")
        print(f"策略: {strategy}")
        print(f"回测期: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"ETF数量: {len(etf_tickers)}")
        print(f"{'='*60}\n")
        
        # 获取历史数据
        print("📥 正在下载历史数据...")
        price_data = self._download_data(etf_tickers, start_date, end_date)
        
        if price_data.empty:
            return {'error': '无法获取数据'}
        
        # 计算日收益率
        returns = price_data.pct_change().dropna()
        
        # 根据策略执行回测
        if strategy == 'momentum':
            results = self._momentum_strategy(returns, price_data)
        elif strategy == 'dual_momentum':
            results = self._dual_momentum_strategy(returns, price_data)
        elif strategy == 'risk_parity':
            results = self._risk_parity_strategy(returns, price_data)
        elif strategy == 'advanced':
            results = self._advanced_strategy(returns, price_data)
        else:
            results = self._momentum_strategy(returns, price_data)
        
        # 计算性能指标
        performance = self._calculate_performance(results['portfolio_returns'])
        
        # 整合结果
        self.results = {
            'strategy': strategy,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'etf_pool': etf_tickers,
            'portfolio_value': results['portfolio_value'],
            'portfolio_returns': results['portfolio_returns'],
            'trades': results['trades'],
            'performance': performance,
            'monthly_returns': self._calculate_monthly_returns(results['portfolio_returns']),
            'drawdown': self._calculate_drawdown(results['portfolio_value'])
        }
        
        # 打印结果
        self._print_results(performance)
        
        return self.results
    
    def _download_data(self, tickers, start_date, end_date):
        """下载ETF价格数据"""
        # 延后几天确保有数据
        start = start_date - timedelta(days=10)
        
        data = yf.download(tickers, start=start, end=end_date, progress=False)['Adj Close']
        
        # 只保留回测期间的数据
        data = data[data.index >= start_date]
        
        return data
    
    def _momentum_strategy(self, returns, price_data):
        """动量策略: 每月轮动到Top 3"""
        portfolio_value = [self.initial_capital]
        trades = []
        
        # 按月回测
        monthly_returns = returns.resample('M').agg(lambda x: (1+x).prod() - 1)
        
        for i in range(1, len(monthly_returns)):
            # 获取过去20日收益
            lookback_idx = max(0, i-1)
            
            # 计算动量分数
            momentum_scores = {}
            for ticker in returns.columns:
                hist_return = (1 + returns[ticker].iloc[:lookback_idx*20].tail(20)).prod() - 1
                momentum_scores[ticker] = hist_return
            
            # 选择Top 3
            top_etfs = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_tickers = [t[0] for t in top_etfs]
            
            # 等权配置
            weight = 1.0 / len(top_tickers) if top_tickers else 0
            
            # 计算当月收益
            month_ret = sum(weight * monthly_returns[ticker].iloc[i] for ticker in top_tickers if ticker in monthly_returns.columns)
            
            # 更新组合价值
            new_value = portfolio_value[-1] * (1 + month_ret)
            portfolio_value.append(new_value)
            
            if month_ret != 0:
                trades.append({
                    'date': monthly_returns.index[i],
                    'etfs': top_tickers,
                    'return': month_ret
                })
        
        portfolio_returns = pd.Series(
            [pportfolio_value[i] / portfolio_value[i-1] - 1 for i in range(1, len(portfolio_value))],
            index=price_data.resample('M').first().index[1:len(portfolio_value)]
        )
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_returns': portfolio_returns,
            'trades': trades
        }
    
    def _dual_momentum_strategy(self, returns, price_data):
        """双动量策略: 相对动量 + 绝对动量过滤"""
        portfolio_value = [self.initial_capital]
        trades = []
        
        monthly_returns = returns.resample('M').agg(lambda x: (1+x).prod() - 1)
        
        for i in range(1, len(monthly_returns)):
            lookback_idx = max(0, i-1)
            
            # 相对动量
            momentum_scores = {}
            for ticker in returns.columns:
                hist_return = (1 + returns[ticker].iloc[:lookback_idx*20].tail(20)).prod() - 1
                momentum_scores[ticker] = hist_return
            
            # 绝对动量过滤 (60日必须为正)
            absolute_momentum = {}
            for ticker in returns.columns:
                abs_ret = (1 + returns[ticker].iloc[:lookback_idx*60].tail(60)).prod() - 1
                absolute_momentum[ticker] = abs_ret
            
            # 筛选: 相对动量Top 5 + 绝对动量为正
            eligible = [t for t in momentum_scores.keys() 
                       if absolute_momentum.get(t, 0) > 0]
            
            if eligible:
                eligible_scores = {t: momentum_scores[t] for t in eligible}
                top_etfs = sorted(eligible_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                top_tickers = [t[0] for t in top_etfs]
            else:
                top_tickers = []  # 无持仓
            
            weight = 1.0 / len(top_tickers) if top_tickers else 0
            
            month_ret = sum(weight * monthly_returns[ticker].iloc[i] 
                          for ticker in top_tickers if ticker in monthly_returns.columns)
            
            new_value = portfolio_value[-1] * (1 + month_ret)
            portfolio_value.append(new_value)
            
            trades.append({
                'date': monthly_returns.index[i],
                'etfs': top_tickers,
                'return': month_ret
            })
        
        portfolio_returns = pd.Series(
            [portfolio_value[i] / portfolio_value[i-1] - 1 for i in range(1, len(portfolio_value))],
            index=price_data.resample('M').first().index[1:len(portfolio_value)]
        )
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_returns': portfolio_returns,
            'trades': trades
        }
    
    def _risk_parity_strategy(self, returns, price_data):
        """风险平价策略"""
        portfolio_value = [self.initial_capital]
        trades = []
        
        monthly_returns = returns.resample('M').agg(lambda x: (1+x).prod() - 1)
        
        for i in range(1, len(monthly_returns)):
            lookback_idx = max(0, i-1)
            
            # 计算各ETF波动率
            volatilities = {}
            for ticker in returns.columns:
                vol = returns[ticker].iloc[:lookback_idx*20].tail(20).std()
                volatilities[ticker] = vol
            
            # 风险平价权重
            inv_vols = {t: 1/v if v > 0 else 0 for t, v in volatilities.items()}
            total = sum(inv_vols.values())
            
            if total > 0:
                weights = {t: v/total for t, v in inv_vols.items()}
            else:
                weights = {}
            
            # 选择Top 5低波动ETF
            sorted_by_vol = sorted(volatilities.items(), key=lambda x: x[1])[:5]
            top_tickers = [t[0] for t in sorted_by_vol]
            
            # 应用风险平价权重
            month_ret = sum(weights.get(t, 0) * monthly_returns[ticker].iloc[i] 
                          for ticker in top_tickers if ticker in monthly_returns.columns)
            
            new_value = portfolio_value[-1] * (1 + month_ret)
            portfolio_value.append(new_value)
            
            trades.append({
                'date': monthly_returns.index[i],
                'etfs': top_tickers,
                'weights': {t: weights.get(t, 0) for t in top_tickers},
                'return': month_ret
            })
        
        portfolio_returns = pd.Series(
            [portfolio_value[i] / portfolio_value[i-1] - 1 for i in range(1, len(portfolio_value))],
            index=price_data.resample('M').first().index[1:len(portfolio_value)]
        )
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_returns': portfolio_returns,
            'trades': trades
        }
    
    def _advanced_strategy(self, returns, price_data):
        """高级多因子策略"""
        portfolio_value = [self.initial_capital]
        trades = []
        
        monthly_returns = returns.resample('M').agg(lambda x: (1+x).prod() - 1)
        
        for i in range(1, len(monthly_returns)):
            lookback_idx = max(0, i-1)
            
            # 多因子评分
            factor_scores = {}
            
            for ticker in returns.columns:
                # 动量因子
                momentum = (1 + returns[ticker].iloc[:lookback_idx*20].tail(20)).prod() - 1
                
                # 波动率因子 (低波动 = 高分)
                vol = returns[ticker].iloc[:lookback_idx*20].tail(20).std()
                risk_score = 1 / vol if vol > 0 else 0
                
                # 质量因子 (收益稳定性)
                month_rets = returns[ticker].iloc[:lookback_idx*20].tail(4)
                quality = -abs(month_rets.std())  # 越稳定越好
                
                # 综合分数
                score = momentum * 0.4 + risk_score * 0.35 + quality * 0.25
                factor_scores[ticker] = score
            
            # 选择Top 3
            top_etfs = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_tickers = [t[0] for t in top_etfs]
            
            weight = 1.0 / len(top_tickers) if top_tickers else 0
            
            month_ret = sum(weight * monthly_returns[ticker].iloc[i] 
                          for ticker in top_tickers if ticker in monthly_returns.columns)
            
            new_value = portfolio_value[-1] * (1 + month_ret)
            portfolio_value.append(new_value)
            
            trades.append({
                'date': monthly_returns.index[i],
                'etfs': top_tickers,
                'scores': {t: factor_scores.get(t, 0) for t in top_tickers},
                'return': month_ret
            })
        
        portfolio_returns = pd.Series(
            [portfolio_value[i] / portfolio_value[i-1] - 1 for i in range(1, len(portfolio_value))],
            index=price_data.resample('M').first().index[1:len(portfolio_value)]
        )
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_returns': portfolio_returns,
            'trades': trades
        }
    
    def _calculate_performance(self, returns):
        """计算性能指标"""
        if returns.empty:
            return {}
        
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (12 / len(returns)) - 1
        
        # 年化波动率
        annual_vol = returns.std() * np.sqrt(12)
        
        # 夏普比率 (假设无风险利率3%)
        risk_free = 0.03
        sharpe = (annual_return - risk_free) / annual_vol if annual_vol > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 胜率
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
        
        # Calmar比率
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'annual_volatility': round(annual_vol * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'win_rate': round(win_rate * 100, 2),
            'calmar_ratio': round(calmar, 2),
            'num_trades': len(returns)
        }
    
    def _calculate_monthly_returns(self, returns):
        """计算月度收益"""
        if returns.empty:
            return {}
        
        monthly = {}
        for date, ret in returns.items():
            key = date.strftime('%Y-%m')
            monthly[key] = round(ret * 100, 2)
        
        return monthly
    
    def _calculate_drawdown(self, portfolio_value):
        """计算回撤序列"""
        df = pd.Series(portfolio_value)
        rolling_max = df.cummax()
        drawdown = (df - rolling_max) / rolling_max * 100
        
        return {
            'max': round(drawdown.min(), 2),
            'current': round(drawdown.iloc[-1], 2)
        }
    
    def _print_results(self, performance):
        """打印回测结果"""
        print("\n" + "="*60)
        print("📈 回测结果")
        print("="*60)
        
        print(f"\n🎯 收益率:")
        print(f"   总收益: {performance['total_return']}%")
        print(f"   年化收益: {performance['annual_return']}%")
        print(f"   年化波动: {performance['annual_volatility']}%")
        
        print(f"\n📊 风险指标:")
        print(f"   夏普比率: {performance['sharpe_ratio']}")
        print(f"   最大回撤: {performance['max_drawdown']}%")
        print(f"   Calmar比率: {performance['calmar_ratio']}")
        
        print(f"\n💰 交易统计:")
        print(f"   交易次数: {performance['num_trades']}")
        print(f"   胜率: {performance['win_rate']}%")
        
        print("\n" + "="*60)
    
    def compare_strategies(self, etf_tickers, start_date=None, end_date=None):
        """对比多个策略"""
        strategies = ['momentum', 'dual_momentum', 'risk_parity', 'advanced']
        results = {}
        
        for strategy in strategies:
            print(f"\n🔄 回测策略: {strategy}")
            result = self.run_backtest(etf_tickers, strategy, start_date, end_date)
            if 'error' not in result:
                results[strategy] = result['performance']
        
        # 打印对比结果
        print("\n" + "="*80)
        print("📊 策略对比")
        print("="*80)
        print(f"{'策略':<20} {'年化收益':<12} {'年化波动':<12} {'夏普比率':<10} {'最大回撤':<10}")
        print("-"*80)
        
        for name, perf in results.items():
            print(f"{name:<20} {perf['annual_return']:>+.1f}%     {perf['annual_volatility']:>6.1f}%     {perf['sharpe_ratio']:>6.2f}    {perf['max_drawdown']:>6.1f}%")
        
        print("="*80)
        
        return results
    
    def save_results(self, filepath='output/backtest_results.json'):
        """保存回测结果"""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 转换numpy类型为Python类型
        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.float64):
                return float(obj)
            elif isinstance(obj, np.int64):
                return int(obj)
            elif isinstance(obj, pd.Series):
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj
        
        results = convert(self.results)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ 回测结果已保存到: {filepath}")
        
        return filepath


# 运行回测
if __name__ == '__main__':
    # 测试ETF池
    etf_pool = [
        'XLK', 'XLV', 'XLF', 'XLY', 'XLE', 'XLI', 'XLB', 'XLRE', 'XLC', 'XLP', 'SMH',
        'EWY', 'EWZ', 'EEM',
        'GPIQ', 'XDTE', 'RDTE', 'QYLD'
    ]
    
    # 创建回测器
    backtester = ETFBacktester(initial_capital=100000)
    
    # 运行对比
    results = backtester.compare_strategies(
        etf_pool,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2026, 3, 1)
    )

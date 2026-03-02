"""
高级ETF轮动策略模块
- 多因子模型 (动量 + 风险 + 相关性 + 质量)
- 双动量 (相对动量 + 绝对趋势过滤)
- 风险平价权重配置
- 波动率缩放
"""

import numpy as np
import pandas as pd
from datetime import datetime
from config import STRATEGY_CONFIG


class AdvancedETFRotator:
    def __init__(self):
        self.config = STRATEGY_CONFIG
        
    def calculate_advanced_signals(self, etf_data, price_history=None):
        """计算高级信号"""
        signals = {}
        
        # 计算相关矩阵(如果有多日价格数据)
        correlation_matrix = self._calculate_correlation_matrix(price_history) if price_history else {}
        
        for ticker, data in etf_data.items():
            if not data:
                continue
                
            # 1. 相对动量因子 (Relative Momentum)
            relative_momentum = self._calculate_relative_momentum(data, etf_data)
            
            # 2. 绝对动量因子 (Absolute Momentum / Trend Filter)
            absolute_momentum = self._calculate_absolute_momentum(data)
            
            # 3. 风险因子 (低波动)
            risk_factor = self._calculate_risk_factor(data)
            
            # 4. 质量因子 (收益稳定性)
            quality_factor = self._calculate_quality_factor(data)
            
            # 5. 相关性因子 (与组合低相关)
            correlation_factor = self._calculate_correlation_factor(ticker, correlation_matrix)
            
            # 综合评分 (可调整权重)
            weights = {
                'momentum': 0.30,      # 动量
                'absolute': 0.15,     # 趋势过滤
                'risk': 0.20,        # 低波动
                'quality': 0.15,     # 质量
                'correlation': 0.20  # 低相关性
            }
            
            composite_score = (
                relative_momentum * weights['momentum'] +
                absolute_momentum * weights['absolute'] +
                risk_factor * weights['risk'] +
                quality_factor * weights['quality'] +
                correlation_factor * weights['correlation']
            )
            
            # 计算波动率调整后的仓位
            vol_scaled_position = self._calculate_volatility_scaling(data)
            
            signals[ticker] = {
                'ticker': ticker,
                'name': data['name'],
                'category': data['category'],
                'current_price': data['current_price'],
                'return_5d': data['return_5d'],
                'return_20d': data['return_20d'],
                'return_60d': data['return_60d'],
                'volatility_20d': data['volatility_20d'],
                
                # 因子得分
                'relative_momentum': round(relative_momentum, 2),
                'absolute_momentum': round(absolute_momentum, 2),
                'risk_factor': round(risk_factor, 2),
                'quality_factor': round(quality_factor, 2),
                'correlation_factor': round(correlation_factor, 2),
                
                # 综合评分
                'composite_score': round(composite_score, 2),
                
                # 波动率缩放仓位
                'vol_scaled_position': round(vol_scaled_position, 4),
                
                # 交易信号
                'signal': self._generate_signal(absolute_momentum, composite_score)
            }
            
        return signals
    
    def _calculate_relative_momentum(self, data, all_data):
        """相对动量: ETF vs 平均市场收益"""
        avg_market_return = np.mean([d['return_20d'] for d in all_data.values() if d])
        return data['return_20d'] - avg_market_return
    
    def _calculate_absolute_momentum(self, data):
        """绝对动量/趋势过滤: 使用200日均线判断趋势"""
        # 简化: 使用60日收益作为趋势代理
        r60 = data['return_60d']
        
        if r60 > 5:  # 强势上涨
            return 100
        elif r60 > 0:  # 温和上涨
            return 50
        elif r60 > -5:  # 温和下跌
            return 0
        else:  # 强势下跌
            return -50
    
    def _calculate_risk_factor(self, data):
        """风险因子: 低波动率得分高"""
        vol = data['volatility_20d']
        if vol == 0:
            return 50
        
        # 波动率越低越好 (反转)
        # 假设平均波动率20%，低于它给高分
        avg_vol = 20
        if vol < avg_vol:
            return ((avg_vol - vol) / avg_vol) * 100
        else:
            return -((vol - avg_vol) / avg_vol) * 50
    
    def _calculate_quality_factor(self, data):
        """质量因子: 收益稳定性"""
        # 简化: 使用5日和20日收益一致性
        r5 = data['return_5d']
        r20 = data['return_20d']
        
        # 如果方向一致，质量高
        if r5 > 0 and r20 > 0:
            return 80
        elif r5 < 0 and r20 < 0:
            return 60
        elif r20 > 0:
            return 40
        else:
            return 20
    
    def _calculate_correlation_factor(self, ticker, correlation_matrix):
        """相关性因子: 与其他ETF低相关得分高"""
        if not correlation_matrix or ticker not in correlation_matrix:
            return 50  # 默认中等
        
        # 计算与所有其他ETF的平均相关性
        corrs = []
        for other_ticker, corr in correlation_matrix[ticker].items():
            if other_ticker != ticker:
                corrs.append(corr)
        
        if not corrs:
            return 50
        
        avg_corr = np.mean(corrs)
        
        # 低相关性 = 高分 (假设平均相关0.5)
        if avg_corr < 0.3:
            return 100
        elif avg_corr < 0.5:
            return 70
        elif avg_corr < 0.7:
            return 40
        else:
            return 10
    
    def _calculate_correlation_matrix(self, price_history):
        """计算价格相关性矩阵"""
        if not price_history or len(price_history) < 10:
            return {}
        
        # 转换为DataFrame
        df = pd.DataFrame(price_history)
        if df.empty:
            return {}
        
        # 计算收益率相关性
        returns = df.pct_change().dropna()
        
        if returns.empty or returns.shape[1] < 2:
            return {}
        
        corr_matrix = returns.corr().to_dict()
        return corr_matrix
    
    def _calculate_volatility_scaling(self, data):
        """波动率缩放仓位"""
        vol = data['volatility_20d']
        if vol == 0 or vol > 50:
            return 0.5  # 默认半仓
        
        # 目标波动率15%
        target_vol = 15
        scaling = target_vol / vol
        
        # 限制在0.2-2.0之间
        return min(max(scaling, 0.2), 2.0)
    
    def _generate_signal(self, absolute_momentum, composite_score):
        """生成交易信号"""
        # 绝对动量必须为正(趋势向上)
        if absolute_momentum < 0:
            return 'SELL'
        
        if composite_score > 60:
            return 'BUY'
        elif composite_score > 30:
            return 'HOLD'
        else:
            return 'WATCH'
    
    def calculate_risk_parity_weights(self, signals):
        """风险平价权重计算"""
        # 基于波动率的权重
        
        positions = []
        
        for ticker, data in signals.items():
            if data['signal'] in ['BUY', 'HOLD'] and data['volatility_20d'] > 0:
                inv_vol = 1 / data['volatility_20d']
                positions.append({
                    'ticker': ticker,
                    'inv_vol': inv_vol,
                    'vol_scaled_weight': data.get('vol_scaled_position', 1.0)
                })
        
        if not positions:
            return {}
        
        # 计算权重
        total_inv_vol = sum(p['inv_vol'] for p in positions)
        
        weights = {}
        for p in positions:
            base_weight = p['inv_vol'] / total_inv_vol
            # 结合波动率缩放
            weights[p['ticker']] = round(base_weight * p['vol_scaled_weight'], 4)
        
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v/total, 4) for k, v in weights.items()}
        
        return weights
    
    def calculate_mean_variance_portfolio(self, signals, risk_aversion=1.0):
        """均值方差优化组合 (简化版)"""
        # 这是一个简化实现
        # 完整实现需要历史收益数据和协方差矩阵
        
        positions = []
        
        for ticker, data in signals.items():
            if data['signal'] in ['BUY', 'HOLD']:
                positions.append({
                    'ticker': ticker,
                    'expected_return': data['composite_score'] / 100,  # 简化期望收益
                    'volatility': data['volatility_20d'] / 100,       # 简化波动率
                })
        
        if not positions:
            return {}
        
        # 简化: 使用风险调整后的权重
        scores = []
        for p in positions:
            # 夏普比率-like
            if p['volatility'] > 0:
                score = (p['expected_return'] / p['volatility']) - risk_aversion * p['volatility']
            else:
                score = 0
            scores.append(score)
        
        # Softmax归一化
        scores_exp = np.exp(np.array(scores) - np.max(scores))
        weights = scores_exp / scores_exp.sum()
        
        return {p['ticker']: round(w, 4) for p, w in zip(positions, weights)}
    
    def generate_advanced_recommendations(self, signals, etf_data, price_history=None):
        """生成高级轮动建议"""
        if not signals:
            return {'error': '无信号数据'}
        
        # 计算权重配置
        risk_parity_weights = self.calculate_risk_parity_weights(signals)
        mean_var_weights = self.calculate_mean_variance_portfolio(signals)
        
        # 分类ETF
        sector_etfs = {k: v for k, v in signals.items() 
                      if v['category'] in ['科技', '医疗', '金融', '消费', '能源', 
                                           '工业', '原材料', '房地产', '通信', '必需消费', '半导体']}
        
        emerging_etfs = {k: v for k, v in signals.items() 
                        if v['category'] in ['韩国', '巴西', '新兴市场']}
        
        hedge_etfs = {k: v for k, v in signals.items() 
                     if v['category'] in ['备兑看涨', '0DTE备兑', '0DTE备兑小盘', '纳指备兑']}
        
        # 获取各类别Top
        top_sector = self._get_top_n(sector_etfs, 3)
        top_emerging = self._get_top_n(emerging_etfs, 1)
        top_hedge = self._get_top_n(hedge_etfs, 2)
        
        # 筛选有买入信号的ETF
        buy_signals = {k: v for k, v in signals.items() if v['signal'] == 'BUY'}
        hold_signals = {k: v for k, v in signals.items() if v['signal'] == 'HOLD'}
        
        recommendations = {
            'generated_at': datetime.now().isoformat(),
            'strategy': 'Advanced Multi-Factor',
            
            # 信号摘要
            'summary': {
                'buy_signals': list(buy_signals.keys()),
                'hold_signals': list(hold_signals.keys()),
                'total_etfs': len(signals)
            },
            
            # 轮动建议
            'sector_rotation': {
                'recommendations': top_sector[:3] if top_sector else [],
                'category': '行业ETF'
            },
            
            'emerging_market': {
                'recommendation': top_emerging[0] if top_emerging else None,
                'category': '新兴市场'
            },
            
            'hedge_positions': {
                'recommendations': top_hedge[:2] if top_hedge else [],
                'category': '防御/收益ETF'
            },
            
            # 权重配置
            'weights': {
                'risk_parity': risk_parity_weights,
                'mean_variance': mean_var_weights,
                'note': '风险平价 或 均值方差优化权重'
            },
            
            # 完整排名
            'all_rankings': self._get_full_rankings(signals),
            
            # 止损检查
            'stop_loss_watch': self._check_stop_loss(signals),
            
            # 因子分析
            'factor_analysis': self._generate_factor_report(signals)
        }
        
        return recommendations
    
    def _get_top_n(self, etfs_dict, n):
        if not etfs_dict:
            return []
        sorted_etfs = sorted(etfs_dict.values(), 
                            key=lambda x: x['composite_score'], 
                            reverse=True)
        return sorted_etfs[:n]
    
    def _get_full_rankings(self, signals):
        return sorted(signals.values(), key=lambda x: x['composite_score'], reverse=True)
    
    def _check_stop_loss(self, signals):
        warning = []
        force = []
        
        for ticker, data in signals.items():
            ret = data['return_20d']
            if ret <= -10:
                force.append({'ticker': ticker, 'return_20d': ret, 'action': '强制平仓'})
            elif ret <= -7:
                warning.append({'ticker': ticker, 'return_20d': ret, 'action': '关注'})
        
        return {'warning': warning, 'force_exit': force}
    
    def _generate_factor_report(self, signals):
        """生成因子分析报告"""
        # 找出每个因子得分最高的ETF
        factors = ['relative_momentum', 'risk_factor', 'quality_factor', 'correlation_factor']
        
        report = {}
        for factor in factors:
            if signals:
                top_etf = max(signals.values(), key=lambda x: x.get(factor, 0))
                report[factor] = {
                    'top_etf': top_etf['ticker'],
                    'score': top_etf.get(factor, 0)
                }
        
        return report


# 向后兼容
class ETFRotator(AdvancedETFRotator):
    """保留原接口"""
    pass

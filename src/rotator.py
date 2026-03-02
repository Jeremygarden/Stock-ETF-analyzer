"""
ETF轮动逻辑模块
基于动量的行业ETF轮动策略
"""

from datetime import datetime
from config import STRATEGY_CONFIG


class ETFRotator:
    def __init__(self):
        self.config = STRATEGY_CONFIG
        
    def calculate_signals(self, etf_data):
        """计算所有ETF的信号"""
        signals = {}
        
        for ticker, data in etf_data.items():
            if not data:
                continue
                
            # 综合动量评分 (20日为主，5日为辅)
            momentum_score = (
                data['return_20d'] * 0.7 +
                data['return_5d'] * 0.3
            )
            
            # 动量强度评分
            momentum_strength = self._calculate_momentum_strength(data)
            
            # 趋势评分
            trend_score = self._calculate_trend_score(data)
            
            # 风险调整收益 (简化版夏普比率概念)
            risk_adj_score = self._calculate_risk_adjusted_score(data)
            
            # 综合评分
            composite_score = (
                momentum_score * 0.4 +
                momentum_strength * 0.2 +
                trend_score * 0.2 +
                risk_adj_score * 0.2
            )
            
            signals[ticker] = {
                'ticker': ticker,
                'name': data['name'],
                'category': data['category'],
                'current_price': data['current_price'],
                'return_5d': data['return_5d'],
                'return_20d': data['return_20d'],
                'return_60d': data['return_60d'],
                'volatility_20d': data['volatility_20d'],
                'volume_change': data['volume_change'],
                'momentum_score': round(momentum_score, 2),
                'momentum_strength': round(momentum_strength, 2),
                'trend_score': round(trend_score, 2),
                'risk_adj_score': round(risk_adj_score, 2),
                'composite_score': round(composite_score, 2),
            }
            
        return signals
    
    def _calculate_momentum_strength(self, data):
        """计算动量强度(动量是否在加速)"""
        ret_5 = data['return_5d']
        ret_20 = data['return_20d']
        
        # 5日收益年化 vs 20日收益年化
        # 如果短期强于中期，说明动量在加速
        if ret_20 == 0:
            return 0
        return ((ret_5 / 5) / (ret_20 / 20)) * 50
    
    def _calculate_trend_score(self, data):
        """计算趋势评分(短期 > 中期 > 长期)"""
        r5 = data['return_5d']
        r20 = data['return_20d']
        r60 = data['return_60d']
        
        score = 0
        if r5 > 0: score += 1
        if r20 > 0: score += 2
        if r60 > 0: score += 1
        
        # 趋势一致性
        if r5 > r20 > r60 or r5 < r20 < r60:
            score += 1
            
        return score * 10
    
    def _calculate_risk_adjusted_score(self, data):
        """计算风险调整收益(简化版)"""
        ret = data['return_20d']
        vol = data['volatility_20d']
        
        if vol == 0:
            return 0
            
        # 收益/波动率 (简化夏普)
        return (ret / vol) * 20
    
    def generate_recommendations(self, signals):
        """生成轮动建议"""
        if not signals:
            return {'error': '无信号数据'}
            
        # 按类别分组
        sector_etfs = {k: v for k, v in signals.items() 
                      if v['category'] in ['科技', '医疗', '金融', '消费', '能源', 
                                           '工业', '原材料', '房地产', '通信', '必需消费', '半导体']}
        
        emerging_etfs = {k: v for k, v in signals.items() 
                        if v['category'] in ['韩国', '巴西', '新兴市场']}
        
        hedge_etfs = {k: v for k, v in signals.items() 
                     if v['category'] in ['备兑看涨', '0DTE备兑', '0DTE备兑小盘', '纳指备兑']}
        
        # 各类别排序
        top_sector = self._get_top_n(sector_etfs, 3)
        top_emerging = self._get_top_n(emerging_etfs, 1)
        top_hedge = self._get_top_n(hedge_etfs, 2)
        
        # 组合建议
        recommendations = {
            'generated_at': datetime.now().isoformat(),
            'summary': self._generate_summary(top_sector, top_emerging, top_hedge),
            'sector_rotation': {
                'strongest': top_sector[:3] if top_sector else [],
                'note': '基于20日动量轮动'
            },
            'emerging_market': {
                'top_pick': top_emerging[0] if top_emerging else None,
                'note': '新兴市场配置'
            },
            'hedge_positions': {
                'recommended': top_hedge[:2] if top_hedge else [],
                'note': '防御性/收益型配置'
            },
            'all_rankings': self._get_full_rankings(signals),
            'stop_loss_watch': self._check_stop_loss(signals)
        }
        
        return recommendations
    
    def _get_top_n(self, etfs_dict, n):
        """获取Top N"""
        if not etfs_dict:
            return []
        sorted_etfs = sorted(etfs_dict.values(), 
                            key=lambda x: x['composite_score'], 
                            reverse=True)
        return sorted_etfs[:n]
    
    def _get_full_rankings(self, signals):
        """获取完整排名"""
        sorted_signals = sorted(signals.values(), 
                               key=lambda x: x['composite_score'], 
                               reverse=True)
        return sorted_signals
    
    def _check_stop_loss(self, signals):
        """检查止损信号"""
        stop_loss_warning = []
        stop_loss_force = []
        
        for ticker, data in signals.items():
            ret = data['return_20d']
            if ret <= -10:
                stop_loss_force.append({
                    'ticker': ticker,
                    'return_20d': ret,
                    'action': '强制平仓'
                })
            elif ret <= -7:
                stop_loss_warning.append({
                    'ticker': ticker,
                    'return_20d': ret,
                    'action': '关注'
                })
                
        return {
            'warning': stop_loss_warning,
            'force_exit': stop_loss_force
        }
    
    def _generate_summary(self, sector, emerging, hedge):
        """生成摘要"""
        sector_names = [s['ticker'] for s in sector[:3]] if sector else []
        emerging_name = emerging[0]['ticker'] if emerging else '无'
        hedge_names = [h['ticker'] for h in hedge[:2]] if hedge else []
        
        return {
            'sector_picks': sector_names,
            'emerging_pick': emerging_name,
            'hedge_picks': hedge_names
        }

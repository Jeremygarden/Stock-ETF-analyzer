"""
ETF多策略量化引擎 (Strategy Engine)
====================================

统一的策略管理和因子计算引擎，支持多策略切换和扩展。

当前策略:
- 策略一 (strategy1): 长期动量策略
    双动量(CSMOM+TSMOM) + 基本面(价值/质量/成长) + 波动率
- 策略二 (strategy2): 短期机会策略
    日内收益 + 技术指标(ADX/CCI/BB) + 风险预警 + 流动性

扩展新策略:
1. 在 STRATEGY_X_FACTORS 中定义因子组和权重
2. 在 __init__ 中添加策略选择分支
3. 运行: python main.py --mode strategyX

依赖模块:
- etf_fundamentals.py: 基本面穿透计算 + 缓存
- config.py: ETF池配置

Author: Financer AI
Date: 2026-03-02
Updated: 2026-03-03 (重命名 dual_strategy → strategy_engine)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional
import yfinance as yf
from datetime import datetime

# 基本面穿透模块
try:
    from etf_fundamentals import get_fundamental_factors
    HAS_FUNDAMENTALS = True
except ImportError:
    HAS_FUNDAMENTALS = False


class StrategyEngine:
    """
    ETF多策略量化引擎
    
    管理多套策略的因子配置、计算和评分。
    支持动态切换策略，便于后续扩展新策略。
    
    使用:
        engine = StrategyEngine(strategy=1)  # 长期动量
        engine = StrategyEngine(strategy=2)  # 短期机会
    """
    
    # ==================== 策略一配置 ====================
    # 长期动量策略 - 双动量增强版
    # 核心思路:
    # - CSMOM (横截面动量): 在ETF池中横向排名，取Top 20%
    # - TSMOM (时序动量): 检查绝对动量是否为正，若为负则不持有
    #
    # 因子相关性优化 (2026-03-03):
    # - 删除 ret_20d (与ret_60d相关0.95)
    # - 删除 atr_ratio (与vol_20相关0.97)
    # - 删除 cci (与bb_pos相关0.97)
    STRATEGY_1_FACTORS = {
        'dual_momentum': {
            'factors': ['csmom_rank', 'tsmom_signal', 'relative_momentum', 'absolute_momentum'],
            'weight': 0.35,
            'description': '双动量 - CSMOM横截面排名 + TSMOM趋势确认'
        },
        'momentum': {
            'factors': ['momentum_1m', 'momentum_accel'],
            'weight': 0.15,
            'description': '动量因子 - 短期动量+动量加速度'
        },
        'value': {
            'factors': ['earnings_yield'],
            'weight': 0.10,
            'description': '价值因子 - 估值水平'
        },
        'quality': {
            'factors': ['roe', 'net_margin'],
            'weight': 0.15,
            'description': '质量因子 - 盈利能力'
        },
        'growth': {
            'factors': ['earnings_growth'],
            'weight': 0.10,
            'description': '成长因子 - 业绩增长'
        },
        'volatility': {
            'factors': ['vol_20', 'bb_pos'],
            'weight': 0.15,
            'description': '波动率因子 - 波动率+布林带位置'
        }
    }
    
    # ==================== 策略二配置 ====================
    # 短期机会策略 - 适合捕捉短期交易机会
    #
    # 因子相关性优化 (2026-03-03):
    # - 删除 cci (与bb_pos相关0.97), 用adx替代趋势判断
    STRATEGY_2_FACTORS = {
        'short_term': {
            'factors': ['ret_intraday', 'ret_1d'],
            'weight': 0.20,
            'description': '短期收益 - 日内和日度收益'
        },
        'technical': {
            'factors': ['adx', 'bb_pos', 'dist_ma10', 'cci', 'mfi'],
            'weight': 0.25,
            'description': '技术指标 - 趋势强度+布林带+均线偏离+通道+资金流'
        },
        'risk': {
            'factors': ['kurt_20', 'skew_20'],
            'weight': 0.15,
            'description': '风险因子 - 极端风险预警'
        },
        'momentum': {
            'factors': ['absolute_momentum'],
            'weight': 0.15,
            'description': '动量因子 - 趋势确认'
        },
        'liquidity': {
            'factors': ['trading_volume', 'turnover_change'],
            'weight': 0.25,
            'description': '流动性因子 - 成交量+换手率变化'
        }
    }
    
    def __init__(self, strategy: int = 1):
        """
        初始化策略模型
        
        Args:
            strategy: 1 或 2
        """
        self.strategy = strategy
        self.factor_config = self.STRATEGY_1_FACTORS if strategy == 1 else self.STRATEGY_2_FACTORS
    
    def calculate_all_factors(self, ticker: str, period: str = '2y') -> Dict:
        """
        计算单只ETF的所有因子(完整24因子)
        
        包含:
        - 收益率因子
        - 均值回归因子
        - 动量/趋势因子
        - 波动率因子
        - 成交量因子
        - 风险分布因子
        - 日内因子
        
        Args:
            ticker: ETF代码
            period: 数据周期
            
        Returns:
            Dict: 因子字典
        """
        factors = {'ticker': ticker}
        
        try:
            # 数据获取
            etf = yf.Ticker(ticker)
            hist = etf.history(period=period)
            info = etf.info
            
            if hist.empty:
                return {'ticker': ticker, 'error': 'No data'}
            
            prices = hist['Close']
            returns = prices.pct_change().dropna()
            volumes = hist['Volume']
            highs = hist['High']
            lows = hist['Low']
            opens = hist['Open']
            
            # ===== 1. 收益率因子 (4个) =====
            # 1日收益率
            if len(prices) >= 2:
                factors['ret_1d'] = round(returns.iloc[-1] * 100, 2)
            
            # 5日收益率
            if len(prices) >= 6:
                factors['ret_5d'] = round((prices.iloc[-1] / prices.iloc[-6] - 1) * 100, 2)
            
            # 20日收益率
            if len(prices) >= 21:
                factors['ret_20d'] = round((prices.iloc[-1] / prices.iloc[-21] - 1) * 100, 2)
            
            # 60日收益率
            if len(prices) >= 61:
                factors['ret_60d'] = round((prices.iloc[-1] / prices.iloc[-61] - 1) * 100, 2)
            
            # ===== 2. 均值回归因子 (4个) =====
            # 价格偏离均线
            if len(prices) >= 10:
                ma10 = prices.rolling(10).mean().iloc[-1]
                factors['dist_ma10'] = round(prices.iloc[-1] - ma10, 2)
            
            if len(prices) >= 20:
                ma20 = prices.rolling(20).mean().iloc[-1]
                factors['dist_ma20'] = round(prices.iloc[-1] - ma20, 2)
            
            if len(prices) >= 60:
                ma60 = prices.rolling(60).mean().iloc[-1]
                factors['dist_ma60'] = round(prices.iloc[-1] - ma60, 2)
            
            # Z-score
            if len(prices) >= 60:
                mean60 = prices.rolling(60).mean().iloc[-1]
                std60 = prices.rolling(60).std().iloc[-1]
                if std60 > 0:
                    factors['zscore_60'] = round((prices.iloc[-1] - mean60) / std60, 2)
            
            # ===== 3. 动量/趋势指标 (4个) =====
            # ADX (简化版)
            if len(prices) >= 14:
                factors['adx'] = self._calculate_adx(prices, highs, lows)
            
            # RSI-14
            if len(returns) >= 14:
                factors['rsi_14'] = self._calculate_rsi(returns)
            
            # MACD
            if len(prices) >= 26:
                factors['macd'], factors['macd_hist'] = self._calculate_macd(prices)
            
            # CCI
            if len(prices) >= 14:
                factors['cci'] = self._calculate_cci(prices, highs, lows)
            
            # ===== 4. 波动率因子 (4个) =====
            # 20日波动率
            if len(returns) >= 20:
                factors['vol_20'] = round(returns.tail(20).std() * np.sqrt(252) * 100, 2)
                factors['volatility_1m'] = factors['vol_20']
            
            # ATR比率
            if len(prices) >= 14:
                factors['atr_ratio'] = self._calculate_atr_ratio(hist)
            
            # 布林带位置
            if len(prices) >= 20:
                factors['bb_pos'] = self._calculate_bb_position(prices)
            
            # GK波动率
            if len(returns) >= 20:
                factors['gk_vol_20'] = self._calculate_gk_volatility(returns)
            
            # ===== 5. 成交量/资金流 (3个) =====
            # 成交量比
            if len(volumes) >= 20:
                avg_vol = volumes.tail(20).mean()
                if avg_vol > 0:
                    factors['vol_ratio'] = round(volumes.iloc[-1] / avg_vol, 2)
                    factors['trading_volume'] = round(np.log(avg_vol + 1), 2)
            
            # MFI
            if len(hist) >= 14:
                factors['mfi'] = self._calculate_mfi(hist)
            
            # 换手率变化
            if len(volumes) >= 60:
                recent = volumes.tail(20).mean()
                older = volumes.iloc[-60:-20].mean()
                if older > 0:
                    factors['turnover_change'] = round((recent / older - 1) * 100, 2)
            
            # ===== 6. 风险/分布因子 (2个) =====
            # 偏度
            if len(returns) >= 20:
                factors['skew_20'] = round(returns.tail(20).skew(), 3)
                factors['skewness'] = factors['skew_20']
            
            # 峰度
            if len(returns) >= 20:
                factors['kurt_20'] = round(returns.tail(20).kurtosis(), 3)
                factors['kurtosis'] = factors['kurt_20']
            
            # ===== 7. 日内因子 (4个) =====
            # 隔夜收益
            if len(opens) >= 2:
                factors['ret_overnight'] = round((opens.iloc[-1] / prices.iloc[-2] - 1) * 100, 3)
            
            # 日内收益
            if len(prices) >= 1 and len(opens) >= 1:
                factors['ret_intraday'] = round((prices.iloc[-1] / opens.iloc[-1] - 1) * 100, 3)
            
            # 上影线
            if len(highs) >= 1 and len(opens) >= 1 and len(prices) >= 1:
                factors['shadow_up'] = round((highs.iloc[-1] - max(opens.iloc[-1], prices.iloc[-1])) / prices.iloc[-1] * 100, 3)
            
            # 下影线
            if len(lows) >= 1 and len(opens) >= 1 and len(prices) >= 1:
                factors['shadow_down'] = round((min(opens.iloc[-1], prices.iloc[-1]) - lows.iloc[-1]) / prices.iloc[-1] * 100, 3)
            
            # ===== 8. 动量因子(兼容) =====
            if 'ret_5d' in factors:
                factors['momentum_1m'] = factors['ret_5d']
            if 'ret_20d' in factors:
                factors['momentum_3m'] = factors['ret_20d']
            if 'ret_60d' in factors:
                factors['momentum_6m'] = factors['ret_60d']
            
            # 动量加速度
            if 'ret_5d' in factors and 'ret_20d' in factors:
                factors['momentum_accel'] = round(factors['ret_5d'] - factors['ret_20d'], 2)
            
            # ===== 9. 双动量因子 (Dual Momentum) =====
            # TSMOM (时序动量): 检查20日动量是否为正
            if 'ret_20d' in factors:
                factors['tsmom_signal'] = 1 if factors['ret_20d'] > 0 else 0
                factors['absolute_momentum'] = factors['tsmom_signal']
            
            # TSMOM 6个月确认
            if 'ret_60d' in factors:
                factors['tsmom_6m'] = 1 if factors['ret_60d'] > 0 else 0
            
            # 相对动量 (CSMOM基础): 6个月收益作为横截面排名依据
            if 'ret_60d' in factors:
                factors['relative_momentum'] = factors['ret_60d']
            
            # CSMOM排名稍后计算 (需要全部ETF数据)
            factors['csmom_rank'] = 0  # 临时值，后续批量计算
            
            # ===== 9. 基本面因子 (穿透持仓计算) =====
            # 优先使用etf_fundamentals模块的缓存数据
            if HAS_FUNDAMENTALS:
                fund_factors = get_fundamental_factors(ticker)
                factors['earnings_yield'] = fund_factors.get('earnings_yield', 0)
                factors['roe'] = fund_factors.get('roe', 0)
                factors['net_margin'] = fund_factors.get('net_margin', 0)
                factors['earnings_growth'] = fund_factors.get('earnings_growth', 0)
            else:
                # 降级: 尝试从yfinance info获取
                if 'peRatio' in info and info['peRatio'] and info['peRatio'] > 0:
                    factors['earnings_yield'] = round(100 / info['peRatio'], 2)
                else:
                    factors['earnings_yield'] = 0
                
                if 'returnOnEquity' in info and info['returnOnEquity']:
                    factors['roe'] = round(info['returnOnEquity'] * 100, 2)
                else:
                    factors['roe'] = 0
                
                if 'profitMargins' in info and info['profitMargins']:
                    factors['net_margin'] = round(info['profitMargins'] * 100, 2)
                else:
                    factors['net_margin'] = 0
                
                if 'earningsGrowth' in info and info['earningsGrowth']:
                    factors['earnings_growth'] = round(info['earningsGrowth'] * 100, 2)
                else:
                    factors['earnings_growth'] = 0
            
            # 市值
            if 'totalAssets' in info and info['totalAssets']:
                factors['size'] = round(np.log(info['totalAssets'] + 1), 2)
            else:
                factors['size'] = 0
            
            factors['success'] = True
            
        except Exception as e:
            factors['error'] = str(e)
        
        return factors
    
    # ==================== 辅助计算函数 ====================
    
    def _calculate_adx(self, prices, highs, lows, period: int = 14) -> float:
        """
        计算真正的ADX (Average Directional Index)
        
        Wilder's ADX公式:
        1. 计算+DM和-DM (方向变动)
        2. 计算TR (真实波幅)
        3. 平滑+DI和-DI
        4. 计算DX = |+DI - -DI| / (+DI + -DI)
        5. ADX = DX的平滑均值
        
        ADX值解读:
        - 0-20: 趋势极弱或无趋势
        - 20-40: 趋势开始形成
        - 40-60: 强趋势
        - 60+: 极强趋势
        """
        try:
            if len(prices) < period * 2:
                return 0
            
            # 1. 计算+DM和-DM
            high_diff = highs.diff()
            low_diff = -lows.diff()  # 注意取负
            
            plus_dm = pd.Series(0.0, index=highs.index)
            minus_dm = pd.Series(0.0, index=highs.index)
            
            # +DM: 当高点上升 > 低点下降，且高点上升 > 0
            cond_plus = (high_diff > low_diff) & (high_diff > 0)
            plus_dm[cond_plus] = high_diff[cond_plus]
            
            # -DM: 当低点下降 > 高点上升，且低点下降 > 0
            cond_minus = (low_diff > high_diff) & (low_diff > 0)
            minus_dm[cond_minus] = low_diff[cond_minus]
            
            # 2. 计算TR (真实波幅)
            tr1 = highs - lows
            tr2 = abs(highs - prices.shift(1))
            tr3 = abs(lows - prices.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # 3. Wilder平滑 (等价于EMA with alpha=1/period)
            atr = tr.ewm(alpha=1/period, min_periods=period).mean()
            plus_dm_smooth = plus_dm.ewm(alpha=1/period, min_periods=period).mean()
            minus_dm_smooth = minus_dm.ewm(alpha=1/period, min_periods=period).mean()
            
            # 4. 计算+DI和-DI
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            
            # 5. 计算DX和ADX
            di_sum = plus_di + minus_di
            di_sum = di_sum.replace(0, np.nan)
            dx = 100 * abs(plus_di - minus_di) / di_sum
            
            adx = dx.ewm(alpha=1/period, min_periods=period).mean()
            
            result = adx.iloc[-1]
            if np.isnan(result):
                return 0
            return round(result, 1)
        except:
            return 0
    
    def _calculate_rsi(self, returns, period: int = 14) -> float:
        """
        计算RSI (Relative Strength Index)
        
        使用Wilder平滑方法:
        - 先用SMA计算初始值
        - 后续用EMA平滑
        
        RSI值解读:
        - 0-30: 超卖
        - 30-70: 正常
        - 70-100: 超买
        """
        if len(returns) < period:
            return 50
        
        # 分离涨跌
        gains = returns.copy()
        losses = returns.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        # Wilder平滑 (EMA with alpha=1/period)
        avg_gain = gains.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1/period, min_periods=period).mean()
        
        if avg_loss.iloc[-1] == 0:
            return 100
        
        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 1)
    
    def _calculate_macd(self, prices, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            
            return round(macd_line.iloc[-1], 2), round(histogram.iloc[-1], 2)
        except:
            return 0, 0
    
    def _calculate_cci(self, prices, highs, lows, period: int = 20):
        """计算CCI"""
        try:
            if len(prices) < period:
                return 0
            
            tp = (highs + lows + prices) / 3
            sma = tp.rolling(period).mean()
            mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
            
            cci = (tp.iloc[-1] - sma.iloc[-1]) / (0.015 * mad.iloc[-1])
            return round(cci, 1)
        except:
            return 0
    
    def _calculate_atr_ratio(self, hist, period: int = 14):
        """计算ATR比率"""
        try:
            high, low, close = hist['High'], hist['Low'], hist['Close']
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean().iloc[-1]
            
            if close.iloc[-1] > 0:
                return round(atr / close.iloc[-1] * 100, 2)
            return 0
        except:
            return 0
    
    def _calculate_bb_position(self, prices, period: int = 20, num_std: float = 2):
        """计算布林带位置"""
        try:
            sma = prices.rolling(period).mean().iloc[-1]
            std = prices.rolling(period).std().iloc[-1]
            upper = sma + num_std * std
            lower = sma - num_std * std
            
            if upper != lower:
                pos = (prices.iloc[-1] - lower) / (upper - lower)
                return round(pos, 3)
            return 0.5
        except:
            return 0.5
    
    def _calculate_gk_volatility(self, returns, lookback: int = 20):
        """计算Garman-Klass波动率"""
        try:
            if len(returns) < lookback:
                return 0
            
            # 简化的GK波动率
            return round(returns.tail(lookback).std() * np.sqrt(252) * 100, 2)
        except:
            return 0
    
    def _calculate_mfi(self, hist, period: int = 14):
        """计算MFI"""
        try:
            tp = (hist['High'] + hist['Low'] + hist['Close']) / 3
            mf = tp * hist['Volume']
            
            positive_flow = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
            negative_flow = mf.where(tp < tp.shift(1), 0).rolling(period).sum()
            
            if negative_flow.iloc[-1] == 0:
                return 100
            
            mr = positive_flow.iloc[-1] / negative_flow.iloc[-1]
            mfi = 100 - (100 / (1 + mr))
            return round(mfi, 1)
        except:
            return 50
    
    # ==================== 策略计算 ====================
    
    def calculate_strategy_score(self, factor_data: Dict) -> Dict:
        """
        计算指定策略的综合得分
        
        Args:
            factor_data: 因子数据字典
            
        Returns:
            Dict: 包含各类因子得分和综合得分的字典
        """
        scores = {}
        total_weight = 0
        
        for factor_group, config in self.factor_config.items():
            group_score = 0
            valid_count = 0
            
            for factor in config['factors']:
                if factor in factor_data and factor_data[factor] is not None:
                    value = factor_data[factor]
                    
                    # 特殊处理某些因子(反向或特殊逻辑)
                    if factor in ['vol_20', 'volatility_1m', 'kurt_20']:
                        # 波动率和峰度: 越低越好(反向)
                        # 归一化到0-1
                        group_score += max(0, 1 - abs(value) / 100)
                    elif factor == 'skew_20':
                        # 负偏度是风险信号
                        group_score += max(0, 1 - abs(min(0, value)) / 5)
                    elif factor in ['dist_ma10', 'dist_ma20', 'dist_ma60']:
                        # 偏离度: 绝对值越小越好
                        group_score += max(0, 1 - abs(value) / (factor_data.get('price', 100) or 100))
                    else:
                        # 其他因子: 直接使用
                        group_score += value
                    
                    valid_count += 1
            
            if valid_count > 0:
                group_score = group_score / valid_count
                # 标准化
                if factor_group in ['volatility', 'risk']:
                    # 反向因子
                    scores[factor_group] = round(group_score * config['weight'] * 0.5, 4)
                else:
                    scores[factor_group] = round((group_score + 50) * config['weight'], 4)
            else:
                scores[factor_group] = 0
            
            total_weight += config['weight']
        
        # 综合得分
        composite = sum(scores.values()) / total_weight if total_weight > 0 else 0
        
        return {
            'strategy': self.strategy,
            'factor_scores': scores,
            'composite_score': round(composite, 2),
            'config': {k: v['description'] for k, v in self.factor_config.items()}
        }
    
    def check_risk_signals(self, factor_data: Dict) -> Dict:
        """
        检查风险信号
        
        Returns:
            Dict: 包含风险等级和具体信号
        """
        signals = []
        risk_level = 'LOW'
        
        # 极端风险检查 (策略二)
        if self.strategy == 2:
            if factor_data.get('kurt_20', 0) > 3:
                signals.append('极端波动 (kurt_20>3)')
                risk_level = 'HIGH'
            
            if factor_data.get('skew_20', 0) < 0:
                signals.append('负偏度预警 (skew<0)')
                if risk_level != 'HIGH':
                    risk_level = 'MEDIUM'
        
        # 超买超卖
        if factor_data.get('rsi_14', 50) > 70:
            signals.append('RSI超买 (>70)')
        elif factor_data.get('rsi_14', 50) < 30:
            signals.append('RSI超卖 (<30)')
        
        # 布林带极端位置
        bb = factor_data.get('bb_pos', 0.5)
        if bb > 0.9:
            signals.append('布林带上轨')
        elif bb < 0.1:
            signals.append('布林带下轨')
        
        return {
            'risk_level': risk_level,
            'signals': signals,
            'recommendation': 'REDUCE' if risk_level == 'HIGH' else ('CAUTION' if risk_level == 'MEDIUM' else 'OK')
        }
    
    def get_recommended_factors(self) -> List[str]:
        """获取当前策略的所有因子列表"""
        factors = []
        for config in self.factor_config.values():
            factors.extend(config['factors'])
        return list(set(factors))


def calculate_portfolio_scores(tickers: List[str], strategy: int = 1) -> pd.DataFrame:
    """
    计算多只ETF的策略得分
    
    优化流程:
    1. 收集所有ETF的原始因子
    2. 横截面Z-score标准化 (统一量纲)
    3. 基于标准化后的因子计算综合得分
    4. CSMOM排名 + TSMOM过滤
    
    Args:
        tickers: ETF代码列表
        strategy: 1 或 2
        
    Returns:
        DataFrame: 包含因子和得分的矩阵
    """
    import time
    
    model = StrategyEngine(strategy=strategy)
    
    # ===== 第1阶段: 收集所有ETF原始因子 =====
    all_factors = []
    for ticker in tickers:
        print(f"  计算 {ticker}...")
        factors = model.calculate_all_factors(ticker)
        if factors.get('success'):
            all_factors.append(factors)
        time.sleep(0.2)
    
    if not all_factors:
        return pd.DataFrame()
    
    # ===== 第2阶段: Z-score标准化 =====
    # 需要标准化的因子列表(排除二值/分类因子)
    numeric_factors = [
        'ret_1d', 'ret_5d', 'ret_20d', 'ret_60d',
        'dist_ma10', 'dist_ma20', 'dist_ma60', 'zscore_60',
        'adx', 'rsi_14', 'macd', 'macd_hist', 'cci',
        'vol_20', 'atr_ratio', 'bb_pos', 'gk_vol_20',
        'vol_ratio', 'mfi', 'kurt_20', 'skew_20',
        'ret_overnight', 'ret_intraday', 'shadow_up', 'shadow_down',
        'momentum_1m', 'momentum_3m', 'momentum_6m', 'momentum_accel',
        'relative_momentum', 'earnings_yield', 'roe', 'net_margin',
        'earnings_growth', 'trading_volume', 'size', 'turnover_change'
    ]
    
    # 不参与标准化的因子 (二值信号)
    binary_factors = ['tsmom_signal', 'absolute_momentum', 'tsmom_6m', 'csmom_rank']
    
    # 构建原始因子矩阵
    factor_matrix = {}
    for f in numeric_factors:
        values = [d.get(f, np.nan) for d in all_factors]
        factor_matrix[f] = values
    
    factor_df = pd.DataFrame(factor_matrix)
    
    # Z-score标准化: (x - mean) / std
    # 对方差为0的因子(如全为0的基本面因子)，标准化后仍为0
    factor_z = pd.DataFrame(index=factor_df.index, columns=factor_df.columns)
    zscore_info = {}
    
    for col in factor_df.columns:
        vals = factor_df[col].dropna()
        if len(vals) > 0 and vals.std() > 1e-8:
            factor_z[col] = (factor_df[col] - vals.mean()) / vals.std()
            zscore_info[col] = {'mean': round(vals.mean(), 4), 'std': round(vals.std(), 4), 'status': 'OK'}
        else:
            factor_z[col] = 0
            zscore_info[col] = {'mean': 0, 'std': 0, 'status': 'ZERO_VARIANCE'}
    
    # 打印标准化信息
    zero_var = [k for k, v in zscore_info.items() if v['status'] == 'ZERO_VARIANCE']
    if zero_var:
        print(f"\n  ⚠️ 零方差因子(已跳过): {', '.join(zero_var)}")
    
    # ===== 第3阶段: 基于Z-score计算综合得分 =====
    # 反向因子列表: 值越小越好
    reverse_factors = ['vol_20', 'volatility_1m', 'kurt_20', 'atr_ratio', 'gk_vol_20']
    
    results = []
    for i, factor_data in enumerate(all_factors):
        ticker = factor_data['ticker']
        
        # 用标准化后的因子计算得分
        scores = {}
        total_weight = 0
        
        for factor_group, config in model.factor_config.items():
            group_score = 0
            valid_count = 0
            
            for factor in config['factors']:
                # 二值因子直接使用
                if factor in binary_factors:
                    value = factor_data.get(factor, 0)
                    if value is not None:
                        group_score += float(value)
                        valid_count += 1
                    continue
                
                # 数值因子使用Z-score
                if factor in factor_z.columns:
                    z_val = factor_z.loc[i, factor]
                    if pd.notna(z_val):
                        z_val = float(z_val)
                        # 反向因子取负
                        if factor in reverse_factors:
                            z_val = -z_val
                        # skew_20: 正偏度好(右尾厚)
                        if factor == 'skew_20':
                            z_val = z_val  # 正偏度 → 正z → 高分
                        group_score += z_val
                        valid_count += 1
            
            if valid_count > 0:
                group_avg = group_score / valid_count
                scores[factor_group] = round(group_avg * config['weight'], 4)
            else:
                scores[factor_group] = 0
            
            total_weight += config['weight']
        
        # 综合Z-score得分 → 转换为0-100分
        raw_score = sum(scores.values()) / total_weight if total_weight > 0 else 0
        # Z-score范围大约-3到+3，映射到0-100
        composite = round(max(0, min(100, 50 + raw_score * 15)), 1)
        
        risk_result = model.check_risk_signals(factor_data)
        
        row = {
            'ticker': ticker,
            'composite_score': composite,
            'risk_level': risk_result['risk_level'],
            'recommendation': risk_result['recommendation'],
            'tsmom_signal': factor_data.get('tsmom_signal', 0),
            'relative_momentum': factor_data.get('relative_momentum', 0),
            'raw_zscore': round(raw_score, 4),
        }
        
        # 添加关键因子原始值 (供展示)
        for factor in model.get_recommended_factors():
            row[f'{factor}'] = factor_data.get(factor, 0)
        
        # 添加因子组得分
        for fg, fs in scores.items():
            row[f'score_{fg}'] = fs
        
        results.append(row)
    
    df = pd.DataFrame(results)
    
    # ===== 第4阶段: CSMOM横截面排名 =====
    if 'relative_momentum' in df.columns and len(df) > 0:
        df['csmom_rank'] = df['relative_momentum'].rank(pct=True) * 100
        
        # 双动量过滤: TSMOM为负的ETF大幅降分
        if 'tsmom_signal' in df.columns:
            df.loc[df['tsmom_signal'] == 0, 'composite_score'] *= 0.3
    
    return df.sort_values('composite_score', ascending=False)


# ===== 测试 =====
if __name__ == '__main__':
    # 测试策略一
    print("="*60)
    print("策略一: 长期动量策略")
    print("="*60)
    
    model1 = StrategyEngine(strategy=1)
    print(f"因子配置: {model1.factor_config.keys()}")
    
    # 测试单只ETF
    factors = model1.calculate_all_factors('XLK')
    print(f"\nXLK因子示例: ret_20d={factors.get('ret_20d')}, rsi_14={factors.get('rsi_14')}")
    
    score1 = model1.calculate_strategy_score(factors)
    print(f"综合得分: {score1['composite_score']}")
    
    # 测试策略二
    print("\n" + "="*60)
    print("策略二: 短期机会策略")
    print("="*60)
    
    model2 = StrategyEngine(strategy=2)
    score2 = model2.calculate_strategy_score(factors)
    print(f"综合得分: {score2['composite_score']}")
    
    risk = model2.check_risk_signals(factors)
    print(f"风险信号: {risk}")


# ===== 向后兼容别名 =====
DualStrategyModel = StrategyEngine

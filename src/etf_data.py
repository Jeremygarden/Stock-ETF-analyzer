"""
ETF数据获取模块
使用yfinance获取ETF价格数据
"""

import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import time


class ETFDataFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        
    def fetch_all_etfs(self):
        """获取所有ETF的数据"""
        from config import ETF_CONFIG
        
        all_etfs = {}
        all_etfs.update(ETF_CONFIG['sector_etfs'])
        all_etfs.update(ETF_CONFIG['emerging_etfs'])
        all_etfs.update(ETF_CONFIG['option_income_etfs'])
        
        etf_data = {}
        
        for ticker, info in all_etfs.items():
            print(f"  获取 {ticker} 数据...")
            data = self.fetch_etf_data(ticker, info)
            if data:
                etf_data[ticker] = data
            time.sleep(0.3)  # 避免请求过快
            
        return etf_data
    
    def fetch_etf_data(self, ticker, info):
        """获取单个ETF的数据"""
        try:
            etf = yf.Ticker(ticker)
            
            # 获取历史价格(过去90天)
            hist = etf.history(period='90d')
            
            if hist.empty:
                print(f"  ⚠️ {ticker} 无数据")
                return None
            
            # 计算各种指标
            prices = hist['Close']
            
            # 动量指标
            returns_5d = self._calculate_return(prices, 5)
            returns_20d = self._calculate_return(prices, 20)
            returns_60d = self._calculate_return(prices, 60)
            
            # 波动率
            volatility_20d = self._calculate_volatility(prices, 20)
            
            # 成交量变化
            volume_change = self._calculate_volume_change(hist, 20)
            
            # 当前价格
            current_price = prices.iloc[-1]
            
            return {
                'ticker': ticker,
                'name': info.get('name', info.get('category', '')),
                'category': info.get('category', ''),
                'current_price': round(current_price, 2),
                'return_5d': round(returns_5d, 2),
                'return_20d': round(returns_20d, 2),
                'return_60d': round(returns_60d, 2),
                'volatility_20d': round(volatility_20d, 2),
                'volume_change': round(volume_change, 2),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"  ❌ {ticker} 获取失败: {e}")
            return None
    
    def _calculate_return(self, prices, period):
        """计算指定周期的收益率"""
        if len(prices) < period:
            return 0
        return ((prices.iloc[-1] / prices.iloc[-period]) - 1) * 100
    
    def _calculate_volatility(self, prices, period):
        """计算波动率(年化)"""
        if len(prices) < period:
            return 0
        returns = prices.pct_change().dropna()
        if len(returns) < period:
            return 0
        return returns.tail(period).std() * (252 ** 0.5) * 100
    
    def _calculate_volume_change(self, hist, period):
        """计算成交量变化"""
        if len(hist) < period:
            return 0
        recent_vol = hist['Volume'].tail(period).mean()
        older_vol = hist['Volume'].iloc[-period*2:-period].mean()
        if older_vol == 0:
            return 0
        return ((recent_vol / older_vol) - 1) * 100
    
    def fetch_price_history(self, tickers, days=90):
        """获取历史价格用于相关性计算"""
        import pandas as pd
        
        try:
            all_prices = {}
            
            for ticker in tickers:
                try:
                    etf = yf.Ticker(ticker)
                    hist = etf.history(period=f'{days}d')
                    if not hist.empty:
                        all_prices[ticker] = hist['Close']
                except:
                    continue
                import time
                time.sleep(0.2)
            
            if all_prices:
                df = pd.DataFrame(all_prices)
                return df.to_dict()
            
        except Exception as e:
            print(f"获取历史价格失败: {e}")
        
        return {}


# 测试用
if __name__ == '__main__':
    fetcher = ETFDataFetcher()
    data = fetcher.fetch_all_etfs()
    print(f"\n获取了 {len(data)} 个ETF的数据")

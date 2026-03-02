"""
ETF轮动系统配置文件 v3.0
- 多数据源配置
- 因子配置
- 策略参数
"""

# ============== 数据源配置 ==============
DATA_SOURCE_CONFIG = {
    'primary': 'yfinance',  # 主要数据源
    'fallback': [],  # 备用数据源
    'cache_ttl': 300,  # 缓存时间(秒)
    'rate_limit': {
        'yfinance': 2,  # 请求间隔(秒)
        'alphavantage': 5,
        'fmp': 0.5,
    }
}

# ============== ETF池配置 ==============
ETF_CONFIG = {
    # 美国行业ETF (11个)
    'sector_etfs': {
        'XLK': {'name': 'Technology Select Sector', 'category': '科技', 'segment': 'GICS'},
        'XLV': {'name': 'Health Care Select Sector', 'category': '医疗', 'segment': 'GICS'},
        'XLF': {'name': 'Financial Select Sector', 'category': '金融', 'segment': 'GICS'},
        'XLY': {'name': 'Consumer Discretionary', 'category': '消费', 'segment': 'GICS'},
        'XLE': {'name': 'Energy Select Sector', 'category': '能源', 'segment': 'GICS'},
        'XLI': {'name': 'Industrial Select Sector', 'category': '工业', 'segment': 'GICS'},
        'XLB': {'name': 'Materials Select Sector', 'category': '原材料', 'segment': 'GICS'},
        'XLRE': {'name': 'Real Estate Select Sector', 'category': '房地产', 'segment': 'GICS'},
        'XLC': {'name': 'Communication Services', 'category': '通信', 'segment': 'GICS'},
        'XLP': {'name': 'Consumer Staples', 'category': '必需消费', 'segment': 'GICS'},
        'SMH': {'name': 'VanEck Semiconductor', 'category': '半导体', 'segment': ' thematic'},
    },
    
    # 新兴市场ETF (3个)
    'emerging_etfs': {
        'EWY': {'name': 'iShares MSCI South Korea', 'category': '韩国', 'segment': 'EM'},
        'EWZ': {'name': 'iShares MSCI Brazil', 'category': '巴西', 'segment': 'EM'},
        'EEM': {'name': 'iShares MSCI Emerging Markets', 'category': '新兴市场', 'segment': 'EM'},
    },
    
    # 期权收益/对冲型ETF (4个)
    'option_income_etfs': {
        'GPIQ': {'name': 'Goldman Sachs Nasdaq-100 Premium Income', 'category': '备兑看涨', 'segment': 'Options'},
        'XDTE': {'name': 'S&P 500 0DTE Covered Call', 'category': '0DTE备兑', 'segment': 'Options'},
        'RDTE': {'name': 'Russell 2000 0DTE Covered Call', 'category': '0DTE备兑小盘', 'segment': 'Options'},
        'QYLD': {'name': 'Global X NASDAQ-100 Covered Call', 'category': '纳指备兑', 'segment': 'Options'},
    },
    
    # 基准ETF (用于对比)
    'benchmark_etfs': {
        'SPY': {'name': 'SPDR S&P 500', 'category': '大盘', 'segment': 'Benchmark'},
        'QQQ': {'name': 'Invesco QQQ', 'category': '纳指', 'segment': 'Benchmark'},
        'IWM': {'name': 'iShares Russell 2000', 'category': '小盘', 'segment': 'Benchmark'},
        'DIA': {'name': 'SPDR Dow Jones', 'category': '道指', 'segment': 'Benchmark'},
    }
}

# ============== 因子配置 ==============
FACTOR_CONFIG = {
    # 动量因子
    'momentum': {
        'periods': [5, 10, 20, 60, 120, 250],
        'weights': {
            'short': 0.2,   # 5日
            'medium': 0.5,   # 20日
            'long': 0.3,    # 60日
        },
        'use_acceleration': True,  # 是否使用动量加速度
    },
    
    # 波动率因子
    'volatility': {
        'periods': [20, 60, 120],
        'low_vol_threshold': 15,  # 低波动阈值
        'use_regime': True,  # 是否使用波动率状态
    },
    
    # 价值因子
    'value': {
        'metrics': ['dividend_yield', 'pe_ratio', 'pb_ratio'],
        'use_inverse': True,  # 低PE = 高价值
    },
    
    # 质量因子
    'quality': {
        'metrics': ['expense_ratio', 'aum', 'beta'],
        'weights': {
            'low_expense': 0.5,
            'high_aum': 0.3,
            'low_beta': 0.2,
        }
    },
    
    # 相关性因子
    'correlation': {
        'benchmarks': ['SPY', 'QQQ', 'TLT'],
        'use_regime_correlation': True,
    }
}

# ============== 策略配置 ==============
STRATEGY_CONFIG = {
    # 动量参数
    'momentum': {
        'lookback_period': 20,  # 回看周期
        'rebalance_frequency': 'monthly',  # 再平衡频率
        'top_n': 3,  # 持仓数量
    },
    
    # 双动量参数
    'dual_momentum': {
        'relative_period': 20,  # 相对动量周期
        'absolute_period': 60,  # 绝对动量周期
        'absolute_threshold': 0,  # 绝对动量阈值(>0才买入)
        'min_momentum': -5,  # 最低动量要求
    },
    
    # 风险平价参数
    'risk_parity': {
        'target_volatility': 0.15,  # 目标波动率
        'volatility_period': 60,  # 波动率计算周期
        'max_weight': 0.30,  # 单个ETF最大权重
        'min_weight': 0.05,  # 单个ETF最小权重
    },
    
    # 止损参数
    'stop_loss': {
        'warning': -7,    # 警告线
        'hard': -10,      # 硬止损
        'trailing': -5,   # 追踪止损
    },
    
    # 组合权重
    'weights': {
        'sector': 0.65,     # 行业ETF权重
        'emerging': 0.15,   # 新兴市场权重
        'hedge': 0.20,     # 对冲ETF权重
    }
}

# ============== 回测配置 ==============
BACKTEST_CONFIG = {
    'initial_capital': 100000,
    'start_date': '2023-01-01',
    'end_date': None,  # None = 今天
    
    # 防止过拟合
    'walk_forward': {
        'train_period': 18,  # 训练期(月)
        'test_period': 6,    # 测试期(月)
        'step': 3,          # 滚动步长
    },
    
    'monte_carlo': {
        'n_simulations': 1000,
        'n_periods': 24,
    },
    
    'bootstrap': {
        'n_bootstrap': 500,
        'confidence_level': 0.95,
    },
    
    'metrics': [
        'total_return',
        'annual_return',
        'annual_volatility',
        'sharpe_ratio',
        'sortino_ratio',
        'max_drawdown',
        'calmar_ratio',
        'var_95',
        'cvar_95',
        'skewness',
        'kurtosis',
        'win_rate',
    ]
}

# ============== 通知配置 ==============
NOTIFIER_CONFIG = {
    'discord_webhook': '',  # Discord webhook URL
    'enable_console': True,
    'signal_file': 'output/latest.json',
    'email': {
        'enabled': False,
        'smtp_server': '',
        'smtp_port': 587,
        'from_addr': '',
        'to_addrs': [],
    }
}

# ============== API Keys ==============
# 请在环境变量中设置以下API keys
# export ALPHAVANTAGE_API_KEY="your_key"
# export FMP_API_KEY="your_key"

API_KEYS = {
    'alphavantage': '',  # https://www.alphavantage.co/support/#api-key
    'fmp': '',          # https://financialmodelingprep.com/developer/docs
}

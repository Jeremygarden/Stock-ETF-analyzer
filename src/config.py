"""
ETF轮动系统配置文件
"""

# ETF池配置
ETF_CONFIG = {
    # 美国行业ETF
    'sector_etfs': {
        'XLK': {'name': 'Technology Select Sector', 'category': '科技'},
        'XLV': {'name': 'Health Care Select Sector', 'category': '医疗'},
        'XLF': {'name': 'Financial Select Sector', 'category': '金融'},
        'XLY': {'name': 'Consumer Discretionary', 'category': '消费'},
        'XLE': {'name': 'Energy Select Sector', 'category': '能源'},
        'XLI': {'name': 'Industrial Select Sector', 'category': '工业'},
        'XLB': {'name': 'Materials Select Sector', 'category': '原材料'},
        'XLRE': {'name': 'Real Estate Select Sector', 'category': '房地产'},
        'XLC': {'name': 'Communication Services', 'category': '通信'},
        'XLP': {'name': 'Consumer Staples', 'category': '必需消费'},
        'SMH': {'name': 'VanEck Semiconductor', 'category': '半导体'},
    },
    
    # 新兴市场ETF
    'emerging_etfs': {
        'EWY': {'name': 'iShares MSCI South Korea', 'category': '韩国'},
        'EWZ': {'name': 'iShares MSCI Brazil', 'category': '巴西'},
        'EEM': {'name': 'iShares MSCI Emerging Markets', 'category': '新兴市场'},
    },
    
    # 期权收益/对冲型ETF
    'option_income_etfs': {
        'GPIQ': {'name': 'Goldman Sachs Nasdaq-100 Premium Income', 'category': '备兑看涨'},
        'XDTE': {'name': 'S&P 500 0DTE Covered Call', 'category': '0DTE备兑'},
        'RDTE': {'name': 'Russell 2000 0DTE Covered Call', 'category': '0DTE备兑小盘'},
        'QYLD': {'name': 'Global X NASDAQ-100 Covered Call', 'category': '纳指备兑'},
    }
}

# 策略配置
STRATEGY_CONFIG = {
    # 动量参数
    'momentum_periods': {
        'short': 5,    # 短期动量(5日)
        'medium': 20,  # 中期动量(20日)
        'long': 60,    # 长期动量(60日)
    },
    
    # 轮动参数
    'rotation': {
        'top_n': 3,           # 每组选取Top N
        'rebalance_day': 1,   # 每周一(0=周日,1=周一...)
        'min_momentum': -5,   # 最低动量门槛(%)
    },
    
    # 止损参数
    'stop_loss': {
        'warning': -7,    # 警告线
        '强制平仓': -10,   # 强制平仓线
    },
    
    # 新兴市场权重
    'emerging_weight': 0.15,  # 新兴市场占总仓位比例
    
    # 对冲ETF配置
    'hedge_weight': 0.20,    # 期权对冲ETF占总仓位比例
}

# 通知配置
NOTIFIER_CONFIG = {
    'discord_webhook': os.environ.get('DISCORD_WEBHOOK', ''),
    'enable_console': True,
    'signal_file': os.path.join(os.path.dirname(__file__), 'output', 'latest.json')
}

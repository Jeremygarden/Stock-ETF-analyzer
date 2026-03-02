# 📊 Stock ETF Analyzer - 美股ETF轮动系统

一个专业的美股行业ETF轮动分析系统，支持多因子量化模型、策略回测和自动信号推送。

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## ✨ 功能特性

- **多因子量化模型**: 24因子专业量化体系
- **智能轮动策略**: 动量/双动量/风险平价/多因子策略
- **回测系统**: 完整回测 + 防止过拟合检验
- **自动运行**: 定时任务 + Discord消息推送

## 📁 项目结构

```
etf-rotator/
├── main.py                 # 主程序入口
├── requirements.txt        # Python依赖
├── README.md              # 项目文档
├── LICENSE                # MIT许可证
├── output/                # 输出结果目录
│   └── latest.json        # 最新信号
└── src/
    ├── config.py          # 配置文件
    ├── data_source.py    # 数据源模块
    ├── etf_data.py       # ETF数据获取
    ├── rotator.py        # 轮动策略
    ├── advanced_rotator.py # 高级轮动(多因子)
    ├── factor_analysis.py  # 因子分析工具
    ├── twenty_four_factors.py # 24因子模型
    ├── backtest.py       # 回测模块
    ├── backtest_metrics.py # 高级回测指标
    └── notifier.py       # 通知模块
```

## 🚀 快速开始

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/Jeremygarden/Stock-ETF-analyzer.git
cd Stock-ETF-analyzer

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行

```bash
# 24因子分析
python main.py --mode factor24

# 基础轮动信号
python main.py --mode rotation

# 策略回测
python main.py --mode backtest

# 高级回测(防止过拟合)
python main.py --mode backtest-advanced --strategy dual_momentum
```

## 📊 ETF池

### 美国行业ETF (11个)
| 代码 | 名称 | 类别 |
|------|------|------|
| XLK | Technology Select Sector | 科技 |
| XLV | Health Care Select Sector | 医疗 |
| XLF | Financial Select Sector | 金融 |
| XLY | Consumer Discretionary | 消费 |
| XLE | Energy Select Sector | 能源 |
| XLI | Industrial Select Sector | 工业 |
| XLB | Materials Select Sector | 原材料 |
| XLRE | Real Estate Select Sector | 房地产 |
| XLC | Communication Services | 通信 |
| XLP | Consumer Staples | 必需消费 |
| SMH | VanEck Semiconductor | 半导体 |

### 新兴市场ETF (3个)
| 代码 | 名称 | 类别 |
|------|------|------|
| EWY | iShares MSCI South Korea | 韩国 |
| EWZ | iShares MSCI Brazil | 巴西 |
| EEM | iShares MSCI Emerging Markets | 新兴市场 |

### 期权收益ETF (4个)
| 代码 | 名称 | 策略 |
|------|------|------|
| GPIQ | Goldman Sachs Nasdaq-100 Premium Income | Buy-write |
| XDTE | S&P 500 0DTE Covered Call | 0DTE备兑 |
| RDTE | Russell 2000 0DTE Covered Call | 0DTE备兑 |
| QYLD | Global X NASDAQ-100 Covered Call | 纳指备兑 |

## 🧮 24因子模型

### 因子分类

| 类别 | 数量 | 因子 |
|------|------|------|
| 🔥 动量 | 6 | momentum_1m, momentum_3m, momentum_6m, momentum_accel, relative_momentum, absolute_momentum |
| 💰 价值 | 4 | dividend_yield, earnings_yield, book_value, cashflow |
| ✅ 质量 | 5 | roe, roa, gross_margin, net_margin, asset_turnover |
| 📈 成长 | 3 | revenue_growth, earnings_growth, roe_change |
| 📉 波动率 | 3 | volatility_1m, volatility_3m, vol_change |
| 📊 规模 | 1 | size |
| 💧 流动性 | 2 | trading_volume, turnover_change |

### 因子处理流程

1. **数据获取** → 从Yahoo Finance获取价格、基本面数据
2. **去极值(Winsorize)** → 1%-99%分位数裁剪
3. **标准化(Z-score)** → 均值0, 标准差1
4. **中性化** → 去除规模因子影响
5. **加权综合** → 各类因子按权重求和

## 📈 策略说明

### 支持的策略

| 策略 | 说明 | 夏普比率(回测) |
|------|------|----------------|
| momentum | 基础动量轮动 | 1.31 |
| dual_momentum | 双动量(相对+绝对) | 2.25 |
| risk_parity | 风险平价 | 0.57 |
| advanced | 多因子综合 | - |

### 策略参数

- **动量周期**: 20日
- **再平衡频率**: 每月
- **持仓数量**: Top 3-5
- **止损**: -7%警告 / -10%强制平仓

## 📊 回测指标

### 基础指标
- 总收益、年化收益、年化波动率
- 夏普比率、Sortino比率
- 最大回撤、Calmar比率

### 高级指标(防止过拟合)
- **Walk-forward**: 滚动训练/测试
- **Monte Carlo**: 1000次模拟
- **Bootstrap**: 95%置信区间
- **IC分析**: 因子预测能力

## 🔄 更新日志

### v3.1 (2026-03-02)
- ✅ 新增24因子量化模型
- ✅ 添加因子标准化/去极值/中性化
- ✅ 生成综合因子得分
- ✅ 因子分类展示

### v3.0 (2026-03-02)
- ✅ 专业数据源模块
- ✅ 多因子计算(动量/波动率/质量/价值)
- ✅ 因子IC分析
- ✅ 因子相关性矩阵

### v2.0 (2026-03-02)
- ✅ 多因子轮动策略
- ✅ 风险平价权重
- ✅ 止损机制
- ✅ 回测系统

### v1.0 (2026-03-02)
- ✅ 基础ETF池(18个)
- ✅ 动量轮动策略
- ✅ Discord推送
- ✅ Cron定时任务

## ⚙️ 配置

### 环境变量

```bash
# Discord Webhook (可选)
export DISCORD_WEBHOOK="your_webhook_url"

# API Keys (可选)
export ALPHAVANTAGE_API_KEY="your_key"
export FMP_API_KEY="your_key"
```

### 配置文件

编辑 `src/config.py`:
- `ETF_CONFIG`: ETF池配置
- `FACTOR_CONFIG`: 因子权重
- `STRATEGY_CONFIG`: 策略参数
- `BACKTEST_CONFIG`: 回测设置

## 📝 代码注释说明

本项目代码遵循以下注释规范:

```python
"""
模块功能描述
Author: 作者
Date: 创建日期
"""

class ClassName:
    """类功能描述"""
    
    def method_name(self, param: type) -> return_type:
        """
        方法功能描述
        
        Args:
            param: 参数说明
        
        Returns:
            返回值说明
        
        Example:
            >>> obj.method_name(value)
            result
        """
        # 重要步骤 1
        # 重要步骤 2
        pass
```

## 🐛 问题排查

### 常见问题

1. **yfinance数据获取失败**
   - 检查网络连接
   - 尝试增加请求间隔

2. **回测结果为空**
   - 检查ETF代码是否正确
   - 确认日期范围

3. **依赖安装失败**
   - 使用虚拟环境
   - 升级pip: `pip install --upgrade pip`

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Pull Request! 请确保:
- 代码符合注释规范
- 添加测试用例
- 更新文档

---

**免责声明**: 本系统仅供学习研究，不构成投资建议。使用前请自行评估风险。

# 📊 ETF轮动系统

美股行业ETF + 新兴市场 + 期权对冲型ETF 轮动策略

## 功能特性

- **多资产类别轮动**: 美国行业ETF、新兴市场ETF、期权收益ETF
- **动量策略**: 基于20日动量综合评分
- **自动止损**: 7%警告、10%强制平仓
- **多渠道通知**: 支持Discord webhook

## ETF池

### 美国行业ETF
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

### 新兴市场ETF
| 代码 | 名称 | 类别 |
|------|------|------|
| EWY | iShares MSCI South Korea | 韩国 |
| EWZ | iShares MSCI Brazil | 巴西 |
| EEM | iShares MSCI Emerging Markets | 新兴市场 |

### 期权收益/对冲ETF
| 代码 | 名称 | 策略 |
|------|------|------|
| GPIQ | Goldman Sachs Nasdaq-100 Premium Income | Buy-write |
| XDTE | S&P 500 0DTE Covered Call | 0DTE备兑 |
| RDTE | Russell 2000 0DTE Covered Call | 0DTE备兑 |
| QYLD | Global X NASDAQ-100 Covered Call | 纳指备兑 |

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 运行轮动分析
python main.py
```

## 配置

在 `src/config.py` 中修改:
- `ETF_CONFIG`: ETF池配置
- `STRATEGY_CONFIG`: 策略参数
- `NOTIFIER_CONFIG`: 通知设置

## 定时任务

设置Cron Job每周一执行:

```bash
# 每周一9:00自动运行
0 9 * * 1 cd /path/to/etf-rotator && python main.py >> /var/log/etf-rotator.log 2>&1
```

## 输出示例

```
📊 ETF轮动信号报告
============================================================

🟢 行业ETF推荐: XLK, SMH, XLY
🌏 新兴市场: EWY
🛡️ 防御配置: GPIQ, XDTE

📈 完整排名:
------------------------------------------------------------
排名 代码   名称                           20日%    综合分
------------------------------------------------------------
1   XLK    Technology Select Sector    +8.23%   +12.45
2   SMH    VanEck Semiconductor        +7.51%   +11.23
3   XLY    Consumer Discretionary      +5.12%   +9.87
...
```

## License

MIT

"""
信号通知模块
输出轮动信号到Discord/控制台
"""

import os
import json
from datetime import datetime


class SignalNotifier:
    def __init__(self):
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK', '')
        
    def send_signals(self, recommendations):
        """发送信号到各个渠道"""
        # 输出到控制台
        self._send_to_console(recommendations)
        
        # 如果有webhook，发送到Discord
        if self.webhook_url:
            self._send_to_discord(recommendations)
            
    def _send_to_console(self, recommendations):
        """输出到控制台"""
        print("\n" + "="*60)
        print("📊 ETF轮动信号报告")
        print("="*60)
        
        if 'error' in recommendations:
            print(f"❌ 错误: {recommendations['error']}")
            return
            
        summary = recommendations['summary']
        
        print(f"\n🟢 行业ETF推荐: {', '.join(summary['sector_picks'])}")
        print(f"🌏 新兴市场: {summary['emerging_pick']}")
        print(f"🛡️ 防御配置: {', '.join(summary['hedge_picks'])}")
        
        # 详细排名
        print("\n📈 完整排名:")
        print("-"*60)
        print(f"{'排名':<4} {'代码':<6} {'名称':<30} {'20日%':<8} {'综合分':<8}")
        print("-"*60)
        
        for i, etf in enumerate(recommendations['all_rankings'][:10], 1):
            name = etf['name'][:28] if len(etf['name']) > 28 else etf['name']
            print(f"{i:<4} {etf['ticker']:<6} {name:<30} {etf['return_20d']:>+7.2f}% {etf['composite_score']:>+7.2f}")
        
        # 止损提醒
        watch = recommendations.get('stop_loss_watch', {})
        if watch.get('warning') or watch.get('force_exit'):
            print("\n⚠️ 止损提醒:")
            for item in watch.get('warning', []):
                print(f"  {item['ticker']}: {item['return_20d']:.2f}% - 关注")
            for item in watch.get('force_exit', []):
                print(f"  {item['ticker']}: {item['return_20d']:.2f}% - 强制平仓!")
        
        print("\n" + "="*60)
        
    def _send_to_discord(self, recommendations):
        """发送到Discord"""
        import requests
        
        if 'error' in recommendations:
            return
            
        summary = recommendations['summary']
        
        # 构建embed消息
        embed = {
            "title": "📊 ETF轮动信号",
            "description": f"生成时间: {recommendations['generated_at'][:19]}",
            "color": 3066993,  # 绿色
            "fields": [
                {
                    "name": "🔥 行业ETF推荐",
                    "value": ", ".join(summary['sector_picks']) or "无",
                    "inline": True
                },
                {
                    "name": "🌏 新兴市场",
                    "value": summary['emerging_pick'],
                    "inline": True
                },
                {
                    "name": "🛡️ 防御配置",
                    "value": ", ".join(summary['hedge_picks']) or "无",
                    "inline": True
                }
            ]
        }
        
        # 添加完整排名
        rankings = "\n".join([
            f"{i+1}. {e['ticker']} ({e['return_20d']:+.1f}%)"
            for i, e in enumerate(recommendations['all_rankings'][:5])
        ])
        
        embed["fields"].append({
            "name": "📈 Top 5",
            "value": rankings
        })
        
        # 检查止损
        watch = recommendations.get('stop_loss_watch', {})
        if watch.get('warning') or watch.get('force_exit'):
            warning_text = "\n".join([
                f"⚠️ {item['ticker']}: {item['return_20d']:.1f}%"
                for item in watch.get('warning', []) + watch.get('force_exit', [])
            ])
            embed["fields"].append({
                "name": "🛑 止损提醒",
                "value": warning_text
            })
        
        data = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code == 204:
                print("✅ Discord消息已发送")
            else:
                print(f"⚠️ Discord发送失败: {response.status_code}")
        except Exception as e:
            print(f"❌ Discord发送错误: {e}")

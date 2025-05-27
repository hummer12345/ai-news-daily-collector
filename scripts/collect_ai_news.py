#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Collector - メインスクリプト
毎日のAI関連ニュースを収集・要約し、レポートを生成する
"""

import os
import json
import asyncio
import requests
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import anthropic
from utils import (
    setup_logging, 
    load_config, 
    save_json, 
    load_json,
    APIUsageTracker
)

class AINewsCollector:
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.usage_tracker = APIUsageTracker()
        self.logger = setup_logging()
        
        # 設定読み込み
        self.config = load_config()
        
        # 出力ディレクトリ作成
        self.reports_dir = Path('reports')
        self.docs_dir = Path('docs/reports')
        self.data_dir = Path('docs/data')
        
        for dir_path in [self.reports_dir, self.docs_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def fetch_ai_news_feeds(self) -> List[Dict]:
        """AI関連RSSフィードから最新ニュースを取得"""
        feeds = [
            'https://feeds.feedburner.com/oreilly/radar/ai',
            'https://techcrunch.com/category/artificial-intelligence/feed/',
            'https://www.artificialintelligence-news.com/feed/',
            'https://venturebeat.com/ai/feed/',
            'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml'
        ]
        
        all_articles = []
        
        for feed_url in feeds:
            try:
                self.logger.info(f"Fetching feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # 各フィードから最新5件
                    # 24時間以内の記事のみ
                    published = getattr(entry, 'published_parsed', None)
                    if published:
                        pub_date = datetime(*published[:6])
                        if datetime.now() - pub_date > timedelta(days=2):
                            continue
                    
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', '')[:300],
                        'published': entry.get('published', ''),
                        'source': feed.feed.get('title', 'Unknown'),
                        'tags': [tag.term for tag in getattr(entry, 'tags', [])]
                    }
                    all_articles.append(article)
                    
            except Exception as e:
                self.logger.error(f"Error fetching {feed_url}: {e}")
                continue
        
        # 重複除去（タイトルベース）
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title_clean = article['title'].lower().strip()
            if title_clean not in seen_titles:
                seen_titles.add(title_clean)
                unique_articles.append(article)
        
        self.logger.info(f"Collected {len(unique_articles)} unique articles")
        return unique_articles[:15]  # 最大15記事
    
    async def create_summary_with_batch(self, articles: List[Dict]) -> Optional[str]:
        """Batch API + プロンプトキャッシュを使用した要約生成"""
        
        if not articles:
            return None
            
        articles_text = "\\n\\n".join([
            f"【{i+1}】 {article['title']}\\n"
            f"ソース: {article['source']}\\n"
            f"要約: {article['summary']}\\n"
            f"URL: {article['link']}"
            for i, article in enumerate(articles)
        ])
        
        # キャッシュ対象のベースプロンプト
        cached_prompt = """
以下のAI関連ニュースを分析して、日本語で包括的な要約レポートを作成してください。

# 出力形式

## 🔥 今日の注目AIニュース

### ⭐ 最重要ニュース
最も重要で影響力の大きいニュース1-2件を詳しく解説してください。

### 📈 注目トレンド  
業界で話題になっている重要なニュース2-3件を簡潔にまとめてください。

### 💡 その他の話題
その他の興味深いニュースやトレンドを紹介してください。

## 📊 技術・市場分析

### 技術的進歩
今日発表された技術的な進歩や革新について分析してください。

### 市場・ビジネスへの影響
企業活動、投資、市場動向への影響を分析してください。

## 🔮 今後の展望
これらのニュースから見える今後のAI業界の動向や注目ポイントを予測してください。

---

# 指示
- 各セクションは具体的で分かりやすく記述
- 重要なポイントは**太字**で強調  
- 読み手の関心を引く魅力的な文章で
- 技術的な内容も一般読者に分かりやすく説明
"""
        
        try:
            # Batch API リクエスト作成
            batch_request = {
                "custom_id": f"ai-news-{datetime.now().strftime('%Y%m%d')}",
                "method": "POST",
                "url": "/v1/messages",
                "body": {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 3000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": cached_prompt,
                                    "cache_control": {"type": "ephemeral"}
                                },
                                {
                                    "type": "text",
                                    "text": f"\\n\\n=== 今日収集したニュース ===\\n{articles_text}"
                                }
                            ]
                        }
                    ]
                }
            }
            
            # バッチジョブ送信
            self.logger.info("Submitting batch job...")
            batch_job = self.client.batches.create(requests=[batch_request])
            
            # 処理完了まで待機
            max_wait_time = 600  # 10分
            wait_time = 0
            
            while wait_time < max_wait_time:
                status = self.client.batches.retrieve(batch_job.id)
                self.logger.info(f"Batch status: {status.request_counts}")
                
                if status.request_counts.completed > 0:
                    # 結果取得
                    result_response = self.client.batches.list_results(batch_job.id)
                    if result_response.data:
                        result = result_response.data[0]
                        if hasattr(result, 'result') and result.result:
                            summary = result.result.content[0].text
                            
                            # 使用量記録
                            usage = getattr(result.result, 'usage', None)
                            if usage:
                                self.usage_tracker.log_usage(
                                    input_tokens=usage.input_tokens,
                                    output_tokens=usage.output_tokens,
                                    cache_hit=getattr(usage, 'cache_read_input_tokens', 0) > 0,
                                    batch_mode=True
                                )
                            
                            return summary
                elif status.request_counts.failed > 0:
                    self.logger.error("Batch job failed")
                    break
                    
                await asyncio.sleep(30)
                wait_time += 30
            
            self.logger.warning("Batch job timed out, falling back to regular API")
            return await self.create_summary_regular(articles)
            
        except Exception as e:
            self.logger.error(f"Batch API error: {e}")
            return await self.create_summary_regular(articles)
    
    async def create_summary_regular(self, articles: List[Dict]) -> Optional[str]:
        """通常APIでの要約生成（フォールバック）"""
        
        articles_text = "\\n\\n".join([
            f"【{i+1}】 {article['title']}\\n"
            f"ソース: {article['source']}\\n"
            f"要約: {article['summary']}\\n"
            f"URL: {article['link']}"
            for i, article in enumerate(articles)
        ])
        
        prompt = f"""
以下のAI関連ニュースを分析して、日本語で包括的な要約レポートを作成してください：

{articles_text}

# 出力形式

## 🔥 今日の注目AIニュース

### ⭐ 最重要ニュース
### 📈 注目トレンド  
### 💡 その他の話題

## 📊 技術・市場分析

### 技術的進歩
### 市場・ビジネスへの影響

## 🔮 今後の展望

重要なポイントは**太字**で強調し、読み手の関心を引く魅力的な文章でお願いします。
"""
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary = response.content[0].text
            
            # 使用量記録
            self.usage_tracker.log_usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_hit=False,
                batch_mode=False
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Regular API error: {e}")
            return None
    
    def save_report(self, summary: str, articles: List[Dict]) -> str:
        """レポートをMarkdownファイルとして保存"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # メインレポート作成
        report_content = f"""# 🤖 AI News Daily Report - {today}

{summary}

---

## 📰 収集したニュース一覧

"""
        
        for i, article in enumerate(articles, 1):
            report_content += f"""
### {i}. {article['title']}

- **ソース**: {article['source']}
- **公開日**: {article.get('published', 'N/A')}
- **リンク**: [記事を読む]({article['link']})
- **概要**: {article['summary']}

"""
        
        report_content += f"""
---

**レポート生成時刻**: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}  
**処理記事数**: {len(articles)}件  
**システム**: GitHub Actions + Claude API
"""
        
        # ファイル保存
        report_path = self.reports_dir / f"ai-news-{today}.md"
        docs_report_path = self.docs_dir / f"ai-news-{today}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        with open(docs_report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Report saved: {report_path}")
        return str(report_path)
    
    def send_notifications(self, summary: str, report_url: str):
        """通知を送信"""
        
        # Slack通知
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            try:
                short_summary = summary[:800] + "..." if len(summary) > 800 else summary
                payload = {
                    "text": f"📰 *AI News Daily - {datetime.now().strftime('%Y/%m/%d')}*\\n\\n{short_summary}\\n\\n📊 詳細レポート: {report_url}",
                    "username": "AI News Bot",
                    "icon_emoji": ":robot_face:"
                }
                
                response = requests.post(slack_webhook, json=payload, timeout=10)
                if response.status_code == 200:
                    self.logger.info("Slack notification sent successfully")
                else:
                    self.logger.warning(f"Slack notification failed: {response.status_code}")
            except Exception as e:
                self.logger.error(f"Error sending Slack notification: {e}")
        
        # Discord通知
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if discord_webhook:
            try:
                embed = {
                    "embeds": [{
                        "title": f"🤖 AI News Daily - {datetime.now().strftime('%Y/%m/%d')}",
                        "description": summary[:2000],
                        "color": 3447003,
                        "timestamp": datetime.now().isoformat(),
                        "footer": {"text": "Powered by GitHub Actions + Claude API"},
                        "fields": [
                            {"name": "📊 詳細レポート", "value": f"[Webサイトで読む]({report_url})", "inline": False}
                        ]
                    }]
                }
                
                response = requests.post(discord_webhook, json=embed, timeout=10)
                if response.status_code in [200, 204]:
                    self.logger.info("Discord notification sent successfully")
                else:
                    self.logger.warning(f"Discord notification failed: {response.status_code}")
            except Exception as e:
                self.logger.error(f"Error sending Discord notification: {e}")
    
    async def run_daily_collection(self):
        """毎日のニュース収集を実行"""
        self.logger.info(f"Starting AI news collection: {datetime.now()}")
        
        try:
            # 1. ニュース収集
            articles = self.fetch_ai_news_feeds()
            
            if not articles:
                self.logger.warning("No articles found, exiting")
                return
            
            # 2. 要約生成（Batch API優先）
            summary = await self.create_summary_with_batch(articles)
            
            if not summary:
                self.logger.error("Failed to generate summary")
                return
            
            # 3. レポート保存
            report_path = self.save_report(summary, articles)
            
            # 4. 統計情報保存
            stats = {
                "date": datetime.now().isoformat(),
                "articles_count": len(articles),
                "sources": list(set(article['source'] for article in articles)),
                "report_path": report_path,
                "usage": self.usage_tracker.get_daily_stats()
            }
            save_json(stats, f"reports/stats-{datetime.now().strftime('%Y-%m-%d')}.json")
            
            # 5. 通知送信
            report_url = f"https://hummer12345.github.io/ai-news-daily-collector/reports/ai-news-{datetime.now().strftime('%Y-%m-%d')}.html"
            self.send_notifications(summary, report_url)
            
            # 6. JSONデータ保存（website生成用）
            data = {
                "summary": summary,
                "articles": articles,
                "generated_at": datetime.now().isoformat(),
                "stats": stats
            }
            save_json(data, f"docs/data/latest.json")
            
            self.logger.info("Daily AI news collection completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in daily collection: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    collector = AINewsCollector()
    asyncio.run(collector.run_daily_collection())
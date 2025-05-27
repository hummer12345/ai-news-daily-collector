# 🤖 AI News Daily Collector

毎日自動更新されるAIニュース要約システム - GitHub Actions + Claude API + GitHub Pages で実現

[![Daily AI News](https://github.com/hummer12345/ai-news-daily-collector/actions/workflows/daily-ai-news.yml/badge.svg)](https://github.com/hummer12345/ai-news-daily-collector/actions/workflows/daily-ai-news.yml)

## 🌟 特徴

- **🔄 完全自動化**: GitHub Actionsで毎日午前9時（JST）に自動実行
- **🤖 AI要約**: Claude APIで高品質な日本語要約を生成
- **💰 低コスト**: 月額約100円で運用可能（Batch API使用）
- **📱 モバイル対応**: GitHub Pagesで美しいWebサイトを自動生成
- **🔔 通知機能**: Slack/Discord通知に対応
- **📊 コスト監視**: API使用量とコストを自動追跡

## 🚀 ライブデモ

**Webサイト**: https://hummer12345.github.io/ai-news-daily-collector/

## 💰 コスト内訳

| サービス | 月額料金 | 説明 |
|---------|---------|------|
| GitHub Actions | **無料** | 月2,000分の無料枠内 |
| Claude API (Batch) | **約100円** | 50%割引適用 |
| GitHub Pages | **無料** | Webサイトホスティング |
| **合計** | **約100円** | |

## 🛠️ セットアップ手順

### 1. リポジトリをフォーク

1. このリポジトリの「Fork」ボタンをクリック
2. 自分のGitHubアカウントにフォーク

### 2. GitHub Secretsを設定

`Settings` → `Secrets and variables` → `Actions` で以下を追加：

| Secret名 | 説明 | 必須 |
|---------|------|-----|
| `ANTHROPIC_API_KEY` | Claude APIキー | ✅ |
| `SLACK_WEBHOOK_URL` | Slack通知用WebhookURL | ❌ |
| `DISCORD_WEBHOOK_URL` | Discord通知用WebhookURL | ❌ |

#### Claude APIキーの取得方法

1. [Anthropic Console](https://console.anthropic.com/) にアクセス
2. アカウント作成・ログイン
3. 「API Keys」からAPIキーを生成
4. 生成されたキーをGitHub Secretsに設定

### 3. GitHub Pagesを有効化

1. リポジトリの `Settings` → `Pages`
2. Source: `Deploy from a branch`
3. Branch: `gh-pages` / `/ (root)`
4. Save

### 4. 初回実行

1. `Actions` タブに移動
2. 「Daily AI News Collection」ワークフローを選択
3. 「Run workflow」で手動実行
4. 正常動作を確認

## 📋 実行スケジュール

- **毎日 09:00 JST** に自動実行
- **手動実行** も可能（Actionsタブから）
- **処理時間** : 約3-5分

## 📊 生成されるコンテンツ

### Webサイト構成

```
https://your-username.github.io/ai-news-daily-collector/
├── index.html          # トップページ（最新レポート）
├── reports/            # 個別レポートページ
│   ├── ai-news-2025-05-27.html
│   └── ai-news-2025-05-28.html
└── styles.css         # カスタムスタイル
```

### 出力例

#### 📰 日次レポート形式

```markdown
# 🤖 AI News Daily Report - 2025-05-27

## 🔥 今日の注目AIニュース

### ⭐ 最重要ニュース
**OpenAI、新型GPTモデル発表** - 推論能力が大幅向上...

### 📈 注目トレンド  
**Google、Gemini 2.0をリリース** - マルチモーダル機能強化...

## 📊 技術・市場分析
...
```

## 🔧 カスタマイズ

### ニュースソースの追加

`scripts/collect_ai_news.py` の `feeds` リストに追加：

```python
feeds = [
    'https://feeds.feedburner.com/oreilly/radar/ai',
    'https://techcrunch.com/category/artificial-intelligence/feed/',
    # 新しいフィードを追加
    'https://your-custom-feed.com/rss'
]
```

### 実行頻度の変更

`.github/workflows/daily-ai-news.yml` の cron を変更：

```yaml
schedule:
  - cron: '0 0 * * *'     # 毎日
  - cron: '0 0 * * 1'     # 毎週月曜
  - cron: '0 0 1 * *'     # 毎月1日
```

### 通知設定

#### Slack通知の設定

1. Slackワークスペースで「Incoming Webhooks」アプリを追加
2. WebhookURLを取得
3. GitHub Secretsに `SLACK_WEBHOOK_URL` として設定

#### Discord通知の設定

1. Discordサーバーでチャンネル設定 → インテグレーション → Webhook
2. WebhookURLを取得
3. GitHub Secretsに `DISCORD_WEBHOOK_URL` として設定

## 🔍 高度な機能

### API最適化

- **Batch API**: 50%のコスト削減
- **プロンプトキャッシュ**: （1日複数回実行時に90%削減）
- **コスト監視**: 使用量とコストの自動追跡

### エラーハンドリング

- APIエラー時の自動リトライ
- フォールバック機能（Batch API → 通常API）
- 詳細なログ出力

## 📈 監視・メンテナンス

### ログの確認

GitHub Actionsの実行ログで以下を監視：

- 収集記事数
- API使用量・コスト
- 処理時間
- エラー発生状況

### 月次コストレビュー

生成される統計ファイルでコストを確認：

```json
{
  "date": "2025-05-27",
  "total_cost_usd": 0.023,
  "estimated_monthly_cost": 0.69,
  "total_requests": 1,
  "cache_hits": 0,
  "batch_requests": 1
}
```

## 🤝 コントリビューション

バグ報告や機能提案は Issue または Pull Request でお願いします。

### 開発環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/hummer12345/ai-news-daily-collector.git
cd ai-news-daily-collector

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
export ANTHROPIC_API_KEY="your_api_key_here"

# ローカル実行
python scripts/collect_ai_news.py
```

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## 🙏 謝辞

- [Anthropic](https://www.anthropic.com/) - Claude APIの提供
- [GitHub](https://github.com/) - Actions と Pages の無料提供
- コミュニティの皆様 - フィードバックと改善提案

---

**🚀 毎日のAI情報収集を自動化して、トレンドに乗り遅れないようにしましょう！**
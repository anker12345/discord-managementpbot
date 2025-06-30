# Discordサーバー管理Bot (Discord Server Management Bot)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.0+-blue.svg)](https://discordpy.readthedocs.io/en/stable/)

サーバーの初期構築から日々のロール管理、セキュリティ維持までを1つのBotで実現するための、多機能・高効率なDiscord Botです。

---

## 📖 概要 (Overview)

このBotは、Discordサーバーのセットアップと運営を劇的に効率化することを目的としています。特に、以下のような課題を解決します。

*   **サーバーの初期構築が面倒**: `config.yaml`ファイル1つで、チャンネル・カテゴリ・権限を持つロール（基幹ロール）のすべてを一度に構築します。
*   **ロール管理が複雑化する**: サーバーの権限構造を司る「**基幹ロール**」と、ユーザーの興味を示す「**サブロール**」を明確に分離。安全かつ柔軟なロール管理を実現します。
*   **日々の運用コストが高い**: 新規メンバーへの対応（ウェルカムゲート）、リアクションによるロール付与、サーバー内のイベントログ記録などを自動化し、管理者の負担を大幅に軽減します。

## ✨ 主な機能 (Key Features)

*   **YAMLによるサーバー構築**: 1つの設定ファイルからサーバーの骨格を何度でも再現。
*   **2階層のロール管理システム**: 安全な「基幹ロール」と柔軟な「サブロール」の分離。
*   **柔軟なリアクションロール**: 専用コマンドで、いつでもリアクションとロールの紐付けを管理。
*   **ウェルカムゲート**: 新規参加者を安全にオンボーディング。
*   **高機能な監査ログ**: メッセージの編集・削除などを記録し、ログの自動削除機能で運用も容易。
*   **テンプレート機能**: 現在のサーバー構成をYAMLファイルとしてエクスポート可能。

## 🚀 導入方法 (Installation)

### 1. リポジトリをクローン
```bash
git clone https://github.com/anker12345/discord-managementpbot.git
cd discord-managementpbot
```

### 2. 必要なライブラリをインストール
```bash
pip install -r requirements.txt
```

### 3. Discord Botのトークンを取得
[Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、Botを有効化してTOKENをコピーします。

### 4. 設定ファイルの準備
`.env`ファイルを作成し、取得したBotトークンを記述します。
```bash
cp .env.example .env
# .env ファイルを編集してBotトークンを設定
```

`config.yaml`ファイルを作成し、[設定例](#⚙️-設定-configyaml)を参考に記述します。
```bash
cp templates/example_config.yaml config.yaml
# config.yaml ファイルを編集してサーバー設定を調整
```

### 5. Botを起動
```bash
python main.py
```

## ⚙️ 設定 (`config.yaml`)

Botの動作は `config.yaml` ファイルで制御されます。詳細な設定例は [templates/example_config.yaml](templates/example_config.yaml) をご覧ください。

### 基本構造

```yaml
# サーバー名（ドキュメント用）
server_name: "New Community Server"

# 基幹ロール（権限を持つロール）の一覧
roles:
  - name: "👑運営"
    color: "#e67e22"
    permission_set: "administrator"
  - name: "🛡️モデレーター"
    color: "#3498db"
    permission_set: "moderator"
  - name: "🗣️メンバー"
    color: "#2ecc71"
    permission_set: "member"
  - name: "🔒未認証"
    color: "#7f8c8d"
    permission_set: "muted"

# チャンネルとカテゴリの一覧
channels:
  - category: "ようこそ"
    items:
      - name: "📜はじめに"
        type: "text"
        permissions:
          - role: "🔒未認証"
            allow: ["view_channel", "read_message_history"]
          - role: "@everyone"
            deny: ["view_channel"]

# ウェルカムゲート機能の設定
welcome_gate:
  enabled: true
  channel: "📜はじめに"
  initial_role: "🔒未認証"
  final_role: "🗣️メンバー"
  message: |
    ## サーバーへようこそ！
    ルールをよく読み、同意される方は下の「✅同意する」ボタンを押してください。

# ログ機能の設定
logging:
  enabled: true
  log_channel: "監査ログ"
  auto_delete_days: 7
  events:
    - "message_delete"
    - "message_edit"
    - "member_join"
    - "member_leave"
```

## 🕹️ コマンド一覧 (Commands)

### サーバー構築・管理

| コマンド | 説明 |
| :--- | :--- |
| `/setup [force]` | `config.yaml`に基づきサーバー全体（チャンネル、基幹ロール）を構築・再構築します。 |
| `/template save <名前>` | 現在のサーバー構成を`config.yaml`形式で保存します。 |
| `/template export [名前]` | 現在のサーバー構成をYAMLファイルとして出力します。 |

### サブロールとリアクションロール管理

| コマンド | 説明 |
| :--- | :--- |
| `/role create <名前> [色]` | 権限を持たない**サブロール**を1つ作成します。（例: `/role create ゲーム好き #3498db`） |
| `/role delete <ロール>` | 指定した**サブロール**を削除します。 |
| `/role list` | サーバー内のサブロール一覧を表示します。 |
| `/role info <ロール>` | 指定したロールの詳細情報を表示します。 |
| `/rr add <メッセージID> <絵文字> <ロール>` | 指定したメッセージに、リアクションと**サブロール**の紐付けを追加します。 |
| `/rr remove <メッセージID> <絵文字>` | 設定済みのリアクションロールの紐付けを解除します。 |
| `/rr list` | 設定されているリアクションロールの一覧を表示します。 |
| `/rr clear <メッセージID>` | 指定したメッセージのリアクションロールをすべて削除します。 |

## 🏗️ プロジェクト構成 (Project Structure)

```
discord-managementbot/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                    # メインエントリーポイント
├── config.yaml               # Bot設定ファイル
├── config/                   # 設定管理
│   ├── __init__.py
│   ├── config_loader.py     # 設定ファイル読み込み
│   └── permissions.py       # 権限セット定義
├── bot/                      # Botコア
│   ├── __init__.py
│   └── bot.py               # メインBotクラス
├── cogs/                     # 機能別コマンド群
│   ├── __init__.py
│   ├── setup.py            # サーバーセットアップ
│   ├── role_management.py  # ロール管理
│   ├── reaction_roles.py   # リアクションロール
│   ├── template.py         # テンプレート機能
│   └── logging.py          # ログ機能
├── database/                 # データベース
│   ├── __init__.py
│   ├── models.py           # データモデル
│   └── database.py         # データベース操作
├── utils/                    # ユーティリティ
│   ├── __init__.py
│   ├── helpers.py          # ヘルパー関数
│   ├── validators.py       # バリデーション
│   └── logger.py           # ログ設定
├── templates/                # 設定テンプレート
│   └── example_config.yaml
└── logs/                     # ログ出力先
    └── .gitkeep
```

## 🔧 環境変数 (Environment Variables)

`.env` ファイルで以下の設定を行います：

```bash
# Discord Bot Token（必須）
DISCORD_BOT_TOKEN=your_bot_token_here

# データベース設定
DATABASE_URL=discord_bot.db

# ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# 開発用ギルドID（オプション）
DEV_GUILD_ID=
```

## 📋 必要な権限 (Required Permissions)

Botが正常に動作するためには、以下の権限が必要です：

### 基本権限
- **ロールの管理**: サブロールの作成・削除
- **チャンネルの管理**: チャンネルとカテゴリの作成・編集
- **メッセージの管理**: ログ機能での履歴確認
- **リアクションの追加**: リアクションロール機能

### 推奨権限
- **管理者**: サーバーセットアップ機能を使用する場合
- **監査ログの表示**: ログ機能での詳細な監視

## 🛠️ 開発・カスタマイズ (Development)

### 新しい機能の追加

1. `cogs/` ディレクトリに新しいCogファイルを作成
2. `bot/bot.py` の `setup_hook()` メソッドで新しいCogを読み込み
3. 必要に応じて `database/models.py` にデータモデルを追加

### 権限セットのカスタマイズ

`config/permissions.py` の `PermissionManager.PERMISSION_SETS` を編集して、独自の権限セットを定義できます。

### ログ機能の拡張

`cogs/logging.py` に新しいイベントリスナーを追加して、監視対象を拡張できます。

## 🤝 コントリビュート (Contributing)

このプロジェクトへの貢献に興味を持っていただきありがとうございます！
バグ報告、機能追加の提案、プルリクエストなど、あらゆる形の協力を歓迎します。

1.  まず、Issueを立てて、提案や修正について議論しましょう。
2.  このリポジトリをフォーク(Fork)してください。
3.  あなたの変更内容のためのブランチを作成します (`git checkout -b feature/AmazingFeature`)。
4.  変更をコミットします (`git commit -m 'Add some AmazingFeature'`)。
5.  ブランチにプッシュします (`git push origin feature/AmazingFeature`)。
6.  プルリクエスト(Pull Request)を作成してください。

## 📜 ライセンス (License)

このプロジェクトはMITライセンスの下で公開されています。詳細は `LICENSE` ファイルをご覧ください。

## 🆘 サポート (Support)

- **バグ報告**: [GitHub Issues](https://github.com/anker12345/discord-managementpbot/issues)
- **機能要望**: [GitHub Issues](https://github.com/anker12345/discord-managementpbot/issues)
- **質問**: [GitHub Discussions](https://github.com/anker12345/discord-managementpbot/discussions)

## 📝 更新履歴 (Changelog)

### v1.0.0
- 初回リリース
- YAMLベースのサーバー構築機能
- 2階層ロール管理システム
- リアクションロール機能
- ウェルカムゲート機能
- 監査ログ機能
- テンプレート機能

---

*This README was generated based on a collaborative requirements definition process.*
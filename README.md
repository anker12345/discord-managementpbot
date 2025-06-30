# Discordサーバー管理Bot (Discord Server Management Bot)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

1.  **リポジトリをクローン**
    ```bash
    git clone https://github.com/anker12345/discord-managementpbot.git
    cd discord-managementpbot
    ```

2.  **必要なライブラリをインストール**
    `requirements.txt`を作成し、必要なライブラリを記述してから、以下のコマンドを実行してください。
    ```bash
    pip install -r requirements.txt
    ```
    (例: `discord.py`, `PyYAML` など)

3.  **Discord Botのトークンを取得**
    [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、Botを有効化してTOKENをコピーします。

4.  **設定ファイルの準備**
    `.env`ファイルを作成し、取得したBotトークンを記述します。
    ```
    # .env
    DISCORD_BOT_TOKEN="ここにあなたのBotトークンを貼り付け"
    ```
    `config.yaml`ファイルを作成し、後述する[設定](#⚙️-設定-configyaml)を記述します。

5.  **Botを起動**
    ```bash
    python main.py
    ```

## ⚙️ 設定 (`config.yaml`)

Botの動作は `config.yaml` ファイルで制御されます。以下は設定例です。

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
      - name: "ロール選択"
        type: "text"

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
  auto_delete_days: 7 # 7日経過したログは自動削除
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
| `/setup` | `config.yaml`に基づきサーバー全体（チャンネル、基幹ロール）を構築・再構築します。 |
| `/template save <名前>` | 現在のサーバー構成を`config.yaml`形式で出力します。 |

### サブロールとリアクションロール管理

| コマンド | 説明 |
| :--- | :--- |
| `/role create <名前> [色]` | 権限を持たない**サブロール**を1つ作成します。（例: `/role create ゲーム好き #3498db`） |
| `/rr add <メッセージID> <絵文字> <ロール名>` | 指定したメッセージに、リアクションと**サブロール**の紐付けを追加します。 |
| `/rr remove <メッセージID> <絵文字>` | 設定済みのリアクションロールの紐付けを解除します。 |
| `/rr list` | 設定されているリアクションロールの一覧を表示します。 |

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

-----

*This README was generated based on a collaborative requirements definition process.*

# CSV科目マッピング処理ツール

CSVファイルの科目マッピング処理と貸借対照表形式への変換を行うPythonツールです。

## 機能

- **科目マッピング**: 設定ファイルに基づいてCSVの科目名を標準的な名称に変換
- **貸借対照表変換**: 縦持ちデータを貸借対照表形式に変換
- **複数形式対応**: balance_seat.csv形式とjpcrp形式の両方に対応
- **設定ファイル**: JSON形式をサポート
- **動的列検出**: 項目名と値の列を自動検出

## インストール

### 必要な依存関係

```bash
pip install pandas
```

または、uvを使用する場合：

```bash
uv sync
```

## 使用方法

### 基本的な使用方法

```bash
# 通常の科目マッピング処理
python main.py --input balance_seat.csv --config config.json

# 貸借対照表形式での変換
python main.py --input balance_seat.csv --config config.json --format bs

# 出力ファイル名を指定
python main.py --input balance_seat.csv --config config.json --output result.csv

# 詳細ログを有効にする
python main.py --input balance_seat.csv --config config.json --verbose

# ドライラン（実際の処理は行わず、内容確認のみ）
python main.py --input balance_seat.csv --config config.json --dry-run
```

### コマンドラインオプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| `--input` | `-i` | 入力CSVファイルのパス | 必須 |
| `--config` | `-c` | 設定ファイルのパス | `config.json` |
| `--output` | `-o` | 出力CSVファイルのパス | `MMDDHHMM.csv` |
| `--format` | `-f` | 出力形式（standard/bs） | `standard` |
| `--verbose` | `-v` | 詳細ログ出力 | 無効 |
| `--dry-run` | - | ドライラン実行 | 無効 |

## 設定ファイル

### 設定ファイル形式

JSON形式で設定できます。

#### 主要設定項目

```json
{
  "input": {
    "file_encoding": "utf-16",
    "delimiter": "\t",
    "header_row": 1
  },
  "output": {
    "file_encoding": "utf-8",
    "delimiter": ",",
    "include_unmapped": true
  },
  "account_mapping": {
    "流動負債": {
      "支払手形": "支払手形、設備関係支手（または支払手形中のリース・商社・メーカー等）",
      "買掛金": "買掛金"
    }
  },
  "balance_sheet": {
    "account_mapping": {
      "現金及び預金": ["現金及び預金"],
      "受取手形及び売掛金": ["受取手形及び売掛金"]
    }
  }
}
```

### 設定項目詳細

- **input**: 入力ファイル設定
  - `file_encoding`: ファイルエンコーディング
  - `delimiter`: 区切り文字
  - `header_row`: ヘッダー行番号

- **output**: 出力ファイル設定
  - `file_encoding`: 出力エンコーディング
  - `delimiter`: 出力区切り文字
  - `include_unmapped`: マッピングされない項目も含める

- **account_mapping**: 科目マッピング定義
- **balance_sheet**: 貸借対照表変換設定

## ファイル構成

```
.
├── main.py              # メインプログラム
├── processor.py         # CSV処理コア機能
├── bs_transformer.py    # 貸借対照表変換機能
├── config.json          # JSON設定ファイル
├── pyproject.toml       # Python プロジェクト設定
├── README.md           # このファイル
└── .gitignore          # Git除外設定
```

## 対応ファイル形式

### 1. balance_seat.csv形式
- エンコーディング: UTF-16
- 区切り文字: タブ
- 列: コンテキストID、項目名、値など

### 2. jpcrp形式
- エンコーディング: UTF-16
- 区切り文字: タブ
- 時点情報による期間フィルタリング

## 出力形式

### 1. standard形式
元のCSV構造を維持しつつ、科目名のマッピングを適用

### 2. bs形式（貸借対照表）
25列の貸借対照表レイアウトで出力
- 階層構造（大分類、中分類、小分類）
- 金額は第9列に配置
- 同一科目の合算処理

## 開発

### 環境設定

```bash
# uvを使用（推奨）
uv sync

# または pip を使用
pip install -r requirements.txt
```

### テスト実行

```bash
# 設定確認（ドライラン）
python main.py --input sample.csv --config config.json --dry-run --verbose

# 実際の処理
python main.py --input sample.csv --config config.json --format bs --verbose
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要求は、GitHubのIssueでお知らせください。
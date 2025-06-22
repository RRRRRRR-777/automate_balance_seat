import pandas as pd
import json
import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

class CSVProcessor:
    def __init__(self, config_path: str):
        """
        CSVプロセッサーの初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config = self._load_config(config_path)
        self.account_mapping = self._flatten_account_mapping()
        self._setup_logging()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルを読み込む（JSON形式）"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"設定ファイルの読み込みエラー: {e}")

    def _flatten_account_mapping(self) -> Dict[str, str]:
        """階層化された科目マッピングを平坦化する"""
        flattened = {}
        account_mapping = self.config.get('account_mapping', {})

        for category, mappings in account_mapping.items():
            for sl_account, general_account in mappings.items():
                flattened[sl_account] = general_account

        return flattened

    def _setup_logging(self):
        """ログ設定をセットアップ"""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        CSVファイルを読み込む

        Args:
            file_path: CSVファイルのパス

        Returns:
            DataFrame: 読み込んだデータ
        """
        input_config = self.config.get('input', {})

        try:
            df = pd.read_csv(
                file_path,
                encoding=input_config.get('file_encoding', 'utf-8'),
                delimiter=input_config.get('delimiter', '\t'),
                header=input_config.get('header_row', 1) - 1  # 0ベースのインデックス
            )

            self.logger.info(f"CSVファイルを読み込みました: {file_path}")
            self.logger.info(f"データ形状: {df.shape}")
            self.logger.info(f"列名: {list(df.columns)}")

            return df

        except FileNotFoundError:
            raise FileNotFoundError(f"入力ファイルが見つかりません: {file_path}")
        except Exception as e:
            raise ValueError(f"CSVファイルの読み込みエラー: {e}")

    def _is_target_column(self, column_name: str) -> bool:
        """処理対象の列かどうかを判定"""
        processing_config = self.config.get('processing_columns', {})
        target_patterns = processing_config.get('target_columns', [])
        exclude_patterns = processing_config.get('exclude_columns', [])

        # 除外パターンにマッチする場合は対象外
        for pattern in exclude_patterns:
            if re.search(pattern, column_name, re.IGNORECASE):
                return False

        # 対象パターンが指定されていない場合は全て対象
        if not target_patterns:
            return True

        # 対象パターンにマッチする場合は対象
        for pattern in target_patterns:
            if re.search(pattern, column_name, re.IGNORECASE):
                return True

        return False

    def _apply_account_mapping(self, value: Any) -> str:
        """単一の値に科目マッピングを適用"""
        if pd.isna(value) or value == "":
            return value

        str_value = str(value).strip()

        # 完全一致での検索
        if str_value in self.account_mapping:
            return self.account_mapping[str_value]

        # 部分一致での検索（SLデフォルト科目が含まれている場合）
        for sl_account, general_account in self.account_mapping.items():
            if sl_account in str_value:
                self.logger.debug(f"部分一致でマッピング: '{str_value}' -> '{general_account}'")
                return general_account

        # マッピングが見つからない場合は元の値を返す
        return str_value

    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        データに変換処理を適用

        Args:
            df: 入力データ

        Returns:
            DataFrame: 変換後のデータ
        """
        transformed_df = df.copy()
        mapping_stats = {
            'total_transformations': 0,
            'mapped_items': [],
            'unmapped_items': set()
        }

        # 処理対象列を特定
        target_columns = [col for col in df.columns if self._is_target_column(col)]
        self.logger.info(f"処理対象列: {target_columns}")

        # 各列に科目マッピングを適用
        for column in target_columns:
            self.logger.info(f"列 '{column}' を処理中...")

            original_values = transformed_df[column].copy()
            transformed_df[column] = transformed_df[column].apply(self._apply_account_mapping)

            # 変換統計を記録
            for i, (original, transformed) in enumerate(zip(original_values, transformed_df[column])):
                if original != transformed and not pd.isna(original):
                    mapping_stats['total_transformations'] += 1
                    mapping_stats['mapped_items'].append({
                        'row': i + 1,
                        'column': column,
                        'original': original,
                        'transformed': transformed
                    })
                elif not pd.isna(original) and str(original).strip() != "":
                    # マッピングされなかった項目を記録
                    mapping_stats['unmapped_items'].add(str(original).strip())

        # 統計情報をログ出力
        self._log_mapping_stats(mapping_stats)

        return transformed_df

    def _log_mapping_stats(self, stats: Dict[str, Any]):
        """マッピング統計をログ出力"""
        log_config = self.config.get('logging', {})

        if log_config.get('show_mapping_stats', True):
            self.logger.info(f"変換統計: {stats['total_transformations']}件の変換を実行")

            if log_config.get('show_unmapped_items', True) and stats['unmapped_items']:
                self.logger.warning(f"マッピングされなかった項目 ({len(stats['unmapped_items'])}件):")
                for item in sorted(stats['unmapped_items']):
                    self.logger.warning(f"  - {item}")

    def save_csv(self, df: pd.DataFrame, output_path: str):
        """
        変換後のデータをCSVファイルに保存

        Args:
            df: 保存するデータ
            output_path: 出力ファイルパス
        """
        output_config = self.config.get('output', {})

        # 既存ファイルの重複チェック
        if Path(output_path).exists():
            raise FileExistsError(f"出力ファイルが既に存在します: {output_path}")

        try:
            df.to_csv(
                output_path,
                encoding=output_config.get('file_encoding', 'utf-8'),
                sep=output_config.get('delimiter', ','),
                index=False
            )

            self.logger.info(f"変換済みデータを保存しました: {output_path}")
            self.logger.info(f"出力データ形状: {df.shape}")

        except Exception as e:
            raise ValueError(f"CSVファイルの保存エラー: {e}")

    def process(self, input_path: str, output_path: str) -> pd.DataFrame:
        """
        全体の処理フローを実行

        Args:
            input_path: 入力ファイルパス
            output_path: 出力ファイルパス

        Returns:
            DataFrame: 変換後のデータ
        """
        self.logger.info("CSV処理を開始します")

        # データ読み込み
        df = self.load_csv(input_path)

        # データ変換
        transformed_df = self.transform_data(df)

        # データ保存
        self.save_csv(transformed_df, output_path)

        self.logger.info("CSV処理が完了しました")
        return transformed_df

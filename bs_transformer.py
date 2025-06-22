import pandas as pd
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class BSItem:
    """貸借対照表項目クラス"""
    level: int  # 階層レベル (0:大分類, 1:中分類, 2:小分類)
    name: str   # 項目名
    value: str  # 金額（文字列、カンマ区切り）
    note: str   # 注記番号

class BalanceSheetTransformer:
    """貸借対照表形式への変換クラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config
        self.bs_config = config.get('balance_sheet', {})
        self.logger = logging.getLogger(__name__)
        
        # 貸借対照表の構造定義
        self.bs_structure = self._load_bs_structure()
        
    def _load_bs_structure(self) -> Dict[str, Any]:
        """貸借対照表の構造を読み込む"""
        return self.bs_config.get('structure', {
            '資産の部': {
                '流動資産': [
                    '現金及び預金',
                    'コールローン',
                    '受取手形及び売掛金',
                    '有価証券',
                    '棚卸資産',
                    '営業貸付金',
                    '銀行業における貸出金',
                    'その他',
                    '貸倒引当金',
                    '流動資産合計'
                ],
                '固定資産': {
                    '有形固定資産': [
                        '建物及び構築物（純額）',
                        '工具、器具及び備品（純額）',
                        '土地',
                        'リース資産（純額）',
                        '建設仮勘定',
                        'その他（純額）',
                        '有形固定資産合計'
                    ],
                    '無形固定資産': [
                        'のれん',
                        'ソフトウエア',
                        'リース資産',
                        'その他',
                        '無形固定資産合計'
                    ],
                    '投資その他の資産': [
                        '投資有価証券',
                        '退職給付に係る資産',
                        '繰延税金資産',
                        '差入保証金',
                        '店舗賃借仮勘定',
                        'その他',
                        '貸倒引当金',
                        '投資その他の資産合計'
                    ]
                },
                '固定資産合計': None,
                '資産合計': None
            },
            '負債の部': {
                '流動負債': [
                    '支払手形及び買掛金',
                    '銀行業における預金',
                    '短期借入金',
                    '1年内返済予定の長期借入金',
                    '1年内償還予定の社債',
                    'コマーシャル・ペーパー',
                    'リース債務',
                    '未払法人税等',
                    '契約負債',
                    '賞与引当金',
                    '店舗閉鎖損失引当金',
                    'ポイント引当金',
                    '設備関係支払手形',
                    'その他',
                    '流動負債合計'
                ],
                '固定負債': [
                    '社債',
                    '長期借入金',
                    'リース債務',
                    '繰延税金負債',
                    '役員退職慰労引当金',
                    '店舗閉鎖損失引当金',
                    '偶発損失引当金',
                    '利息返還損失引当金',
                    '退職給付に係る負債',
                    '資産除去債務',
                    '長期預り保証金',
                    '保険契約準備金',
                    'その他',
                    '固定負債合計'
                ],
                '負債合計': None
            }
        })
    
    def clean_amount_value(self, value: str) -> str:
        """
        金額値のクリーニング（※記号除去と数値抽出）
        
        Args:
            value: 元の値
            
        Returns:
            str: クリーニング後の値
        """
        if pd.isna(value) or value == "":
            return ""
        
        str_value = str(value)
        
        # 数値パターンを検索（負の値も対応）
        # パターン: 数字、カンマ、マイナス記号を含む数値
        number_patterns = re.findall(r'[△-]?[\d,]+', str_value)
        
        if number_patterns:
            # 最初に見つかった数値パターンを使用
            cleaned = number_patterns[0]
            
            # △記号をマイナス記号に変換
            if cleaned.startswith('△'):
                cleaned = '-' + cleaned[1:]
            
            return cleaned
        
        return ""
    
    def format_amount(self, amount: str) -> str:
        """
        金額をフォーマット（カンマ区切り、百万円単位変換）
        
        Args:
            amount: 金額文字列
            
        Returns:
            str: フォーマット済み金額
        """
        if not amount or amount == "":
            return ""
        
        try:
            # カンマを除去して数値に変換
            clean_amount = amount.replace(',', '')
            
            # マイナス記号の処理
            is_negative = clean_amount.startswith('-')
            if is_negative:
                clean_amount = clean_amount[1:]
            
            # 数値変換
            num_value = float(clean_amount)
            
            # 百万円単位に変換（割り切れる場合のみ）
            if num_value >= 1000000 and num_value % 1000000 == 0:
                num_value = int(num_value / 1000000)
                if is_negative:
                    return f"{num_value * -1:,}"
                else:
                    return f"{num_value:,}"
            else:
                # 元の値をそのままカンマ区切りで返す
                if is_negative:
                    return f"-{int(num_value):,}"
                else:
                    return f"{int(num_value):,}"
                
        except (ValueError, TypeError):
            # 数値でない場合はそのまま返す
            return str(amount)
    
    def extract_note_numbers(self, value: str) -> str:
        """
        注記番号を抽出
        
        Args:
            value: 元の値
            
        Returns:
            str: 注記番号（例: "※6,※8"）
        """
        if pd.isna(value) or value == "":
            return ""
        
        # ※記号とその後の数字・カンマ・スペースを抽出
        notes = re.findall(r'※[0-9,\s]*', str(value))
        if notes:
            return ''.join(notes).strip()
        
        return ""
    
    def map_item_to_bs_account(self, item_name: str, amount: str) -> Optional[BSItem]:
        """
        項目名を貸借対照表科目にマッピング
        
        Args:
            item_name: 項目名
            amount: 金額
            
        Returns:
            Optional[BSItem]: マッピング結果
        """
        # 項目名のデータ型チェック
        if pd.isna(item_name) or item_name == "":
            return None
        
        # 項目名を文字列に変換
        item_name_str = str(item_name).strip()
        if not item_name_str:
            return None
        
        # 設定ファイルからマッピングを取得
        mapping = self.bs_config.get('account_mapping', {})
        
        # 金額のクリーニング
        note = self.extract_note_numbers(amount)
        clean_amount = self.clean_amount_value(amount)
        formatted_amount = self.format_amount(clean_amount)
        
        # 完全一致検索
        for bs_account, source_patterns in mapping.items():
            if isinstance(source_patterns, list):
                for pattern in source_patterns:
                    if isinstance(pattern, str) and pattern in item_name_str:
                        return BSItem(
                            level=self._get_account_level(bs_account),
                            name=bs_account,
                            value=formatted_amount,
                            note=note
                        )
            elif isinstance(source_patterns, str):
                if source_patterns in item_name_str:
                    return BSItem(
                        level=self._get_account_level(bs_account),
                        name=bs_account,
                        value=formatted_amount,
                        note=note
                    )
        
        return None
    
    def _get_account_level(self, account_name: str) -> int:
        """
        科目名から階層レベルを判定
        
        Args:
            account_name: 科目名
            
        Returns:
            int: 階層レベル
        """
        # 合計項目は中分類レベル
        if '合計' in account_name:
            return 1
            
        # 大分類項目
        major_categories = ['資産の部', '負債の部', '純資産の部', '流動資産', '固定資産', '流動負債', '固定負債']
        if account_name in major_categories:
            return 0
            
        # その他は小分類
        return 2
    
    def transform_to_balance_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        縦持ちデータを貸借対照表形式に変換
        
        Args:
            df: 入力データフレーム
            
        Returns:
            pd.DataFrame: 貸借対照表形式のデータフレーム
        """
        self.logger.info("貸借対照表形式への変換を開始します")
        
        # データフレーム情報をログ出力
        self.logger.info(f"入力データ形状: {df.shape}")
        self.logger.info(f"列名: {list(df.columns)}")
        
        # 当期末のデータのみを抽出（複数条件でフィルタリング）
        current_year_df = df.copy()
        
        # 条件1: コンテキストIDがある場合
        if 'コンテキストID' in df.columns:
            current_year_mask = df['コンテキストID'].str.contains('CurrentYear|Current', na=False, case=False)
            current_year_df = df[current_year_mask].copy()
            self.logger.info(f"コンテキストID条件でフィルタ: {len(current_year_df)}件")
        
        # 条件2: 相対年度がある場合
        elif '相対年度' in df.columns:
            current_year_mask = (df['相対年度'] == '当期') | (df['相対年度'] == '当期末')
            current_year_df = df[current_year_mask].copy()
            self.logger.info(f"相対年度条件でフィルタ: {len(current_year_df)}件")
            
        # 条件3: 時点情報がある場合（jpcrp形式）
        elif any(col for col in df.columns if 'Instant' in col or 'Quarter' in col):
            # 四半期末時点や年度末時点のデータを抽出
            instant_cols = [col for col in df.columns if 'Instant' in col or 'Quarter' in col]
            if instant_cols:
                # 当期四半期末または当期年度末のデータを抽出
                mask = pd.Series([False] * len(df))
                for col in instant_cols:
                    if 'Current' in str(df[col].iloc[0]) if len(df) > 0 else False:
                        mask = mask | df[col].str.contains('Current', na=False, case=False)
                
                if mask.any():
                    current_year_df = df[mask].copy()
                    self.logger.info(f"時点情報条件でフィルタ: {len(current_year_df)}件")
        
        # フィルタ結果をログ出力
        self.logger.info(f"当期末データ: {len(current_year_df)}件")
        
        # 項目名と値の列を動的に検出
        item_name_col = self._detect_item_name_column(current_year_df)
        value_col = self._detect_value_column(current_year_df)
        
        self.logger.info(f"項目名列: {item_name_col}")
        self.logger.info(f"値列: {value_col}")
        
        if not item_name_col or not value_col:
            self.logger.warning("項目名または値の列が見つかりません")
            # 空の貸借対照表を返す
            return self._convert_to_csv_format([])
        
        # 貸借対照表項目のマッピング（同じ科目名でグループ化）
        bs_items_dict = {}
        mapped_count = 0
        
        for _, row in current_year_df.iterrows():
            item_name = row[item_name_col] if pd.notna(row[item_name_col]) else ""
            value = str(row[value_col]) if pd.notna(row[value_col]) else ""
            
            bs_item = self.map_item_to_bs_account(item_name, value)
            if bs_item:
                # 同じ科目名でグループ化
                key = bs_item.name
                if key not in bs_items_dict:
                    bs_items_dict[key] = []
                bs_items_dict[key].append(bs_item)
                mapped_count += 1
        
        self.logger.info(f"マッピング済み項目: {mapped_count}件")
        self.logger.info(f"ユニーク科目数: {len(bs_items_dict)}件")
        
        # 貸借対照表構造に基づいて整理
        bs_table = self._build_balance_sheet_structure_with_grouping(bs_items_dict)
        
        # CSV形式に変換
        return self._convert_to_csv_format(bs_table)
    
    def _build_balance_sheet_structure_with_grouping(self, bs_items_dict: Dict[str, List[BSItem]]) -> List[List[str]]:
        """
        貸借対照表の構造を構築（グループ化されたアイテム用）
        
        Args:
            bs_items_dict: 科目名でグループ化されたBSアイテム辞書
            
        Returns:
            List[List[str]]: 貸借対照表の行データ
        """
        # 合算処理を行ったアイテム辞書を作成
        consolidated_items = {}
        
        for account_name, items_list in bs_items_dict.items():
            if items_list:
                # 同じ科目の値を合算
                total_amount = 0
                has_valid_amount = False
                
                for item in items_list:
                    if item.value and item.value.strip():
                        try:
                            clean_value = item.value.replace(',', '')
                            if clean_value.startswith('-'):
                                amount = -float(clean_value[1:])
                            else:
                                amount = float(clean_value)
                            total_amount += amount
                            has_valid_amount = True
                        except (ValueError, TypeError):
                            continue
                
                if has_valid_amount:
                    # 合算した値で新しいBSItemを作成
                    formatted_amount = f"{int(total_amount):,}" if total_amount == int(total_amount) else f"{total_amount:,.0f}"
                    consolidated_items[account_name] = BSItem(
                        level=items_list[0].level,
                        name=account_name,
                        value=formatted_amount,
                        note=""  # 注記は出力しない
                    )
        
        bs_rows = []
        
        # 資産の部を構築
        bs_rows.extend(self._build_section_with_grouping('資産の部', consolidated_items))
        
        # 空行を追加
        bs_rows.append([''] * 25)
        
        # 負債の部を構築
        bs_rows.extend(self._build_section_with_grouping('負債の部', consolidated_items))
        
        return bs_rows
    
    def _build_section_with_grouping(self, section_name: str, item_dict: Dict[str, BSItem]) -> List[List[str]]:
        """
        セクション（資産の部、負債の部）を構築（グループ化対応）
        
        Args:
            section_name: セクション名
            item_dict: 項目辞書
            
        Returns:
            List[List[str]]: セクションの行データ
        """
        rows = []
        structure = self.bs_structure.get(section_name, {})
        
        # セクションヘッダー
        rows.append([section_name] + [''] * 24)
        
        for category, subcategories in structure.items():
            if isinstance(subcategories, dict):
                # 中分類ヘッダー
                rows.append(['', category] + [''] * 23)
                
                for subcat, items in subcategories.items():
                    if isinstance(items, list):
                        # 小分類ヘッダー
                        rows.append(['', '', subcat] + [''] * 22)
                        
                        # 項目追加
                        for item_name in items:
                            rows.extend(self._add_item_row_with_grouping(item_name, item_dict, level=3))
                    else:
                        # 項目追加
                        rows.extend(self._add_item_row_with_grouping(subcat, item_dict, level=2))
                        
            elif isinstance(subcategories, list):
                # 中分類ヘッダー
                rows.append(['', category] + [''] * 23)
                
                # 項目追加
                for item_name in subcategories:
                    rows.extend(self._add_item_row_with_grouping(item_name, item_dict, level=3))
                    
            else:
                # 合計項目
                rows.extend(self._add_item_row_with_grouping(category, item_dict, level=1))
        
        return rows
    
    def _add_item_row_with_grouping(self, item_name: str, item_dict: Dict[str, BSItem], level: int) -> List[List[str]]:
        """
        項目行を追加（グループ化対応）
        
        Args:
            item_name: 項目名
            item_dict: 項目辞書
            level: 階層レベル
            
        Returns:
            List[List[str]]: 項目行データ
        """
        item = item_dict.get(item_name)
        
        # 空の行を作成（25列）
        row = [''] * 25
        
        # 階層に応じて配置（イオンBS_original.csvと同じ構造）
        if level == 1:  # 大分類
            row[0] = item_name
        elif level == 2:  # 中分類
            row[1] = item_name
        elif level == 3:  # 小分類（第3列目に配置）
            row[2] = item_name
        
        # 金額を表示（第9列目）
        if item and item.value:
            row[9] = f'"{item.value}"'
        
        return [row]

    def _build_balance_sheet_structure(self, bs_items: List[BSItem]) -> List[List[str]]:
        """
        貸借対照表の構造を構築
        
        Args:
            bs_items: 貸借対照表項目リスト
            
        Returns:
            List[List[str]]: 貸借対照表の行データ
        """
        # 項目を辞書化（検索用）
        item_dict = {item.name: item for item in bs_items}
        
        bs_rows = []
        
        # 資産の部を構築
        bs_rows.extend(self._build_section('資産の部', item_dict))
        
        # 空行を追加
        bs_rows.append([''] * 25)
        
        # 負債の部を構築
        bs_rows.extend(self._build_section('負債の部', item_dict))
        
        return bs_rows
    
    def _build_section(self, section_name: str, item_dict: Dict[str, BSItem]) -> List[List[str]]:
        """
        セクション（資産の部、負債の部）を構築
        
        Args:
            section_name: セクション名
            item_dict: 項目辞書
            
        Returns:
            List[List[str]]: セクションの行データ
        """
        rows = []
        structure = self.bs_structure.get(section_name, {})
        
        # セクションヘッダー
        rows.append([section_name] + [''] * 24)
        
        for category, subcategories in structure.items():
            if isinstance(subcategories, dict):
                # 中分類ヘッダー
                rows.append(['', category] + [''] * 23)
                
                for subcat, items in subcategories.items():
                    if isinstance(items, list):
                        # 小分類ヘッダー
                        rows.append(['', '', subcat] + [''] * 22)
                        
                        # 項目追加
                        for item_name in items:
                            rows.extend(self._add_item_row(item_name, item_dict, level=3))
                    else:
                        # 項目追加
                        rows.extend(self._add_item_row(subcat, item_dict, level=2))
                        
            elif isinstance(subcategories, list):
                # 中分類ヘッダー
                rows.append(['', category] + [''] * 23)
                
                # 項目追加
                for item_name in subcategories:
                    rows.extend(self._add_item_row(item_name, item_dict, level=2))
                    
            else:
                # 合計項目
                rows.extend(self._add_item_row(category, item_dict, level=1))
        
        return rows
    
    def _add_item_row(self, item_name: str, item_dict: Dict[str, BSItem], level: int) -> List[List[str]]:
        """
        項目行を追加
        
        Args:
            item_name: 項目名
            item_dict: 項目辞書
            level: 階層レベル
            
        Returns:
            List[List[str]]: 項目行データ
        """
        # 合算処理：同じ科目名の項目をすべて取得して合算
        matching_items = [item for key, item in item_dict.items() if key == item_name]
        
        # 空の行を作成（25列）
        row = [''] * 25
        
        # 階層に応じて配置（イオンBS_original.csvと同じ構造）
        if level == 1:  # 大分類
            row[0] = item_name
        elif level == 2:  # 中分類
            row[1] = item_name
        elif level == 3:  # 小分類（第3列目に配置）
            row[2] = item_name
        
        # 金額の合算と表示（第9列目）
        if matching_items:
            total_amount = 0
            has_valid_amount = False
            
            for item in matching_items:
                if item.value and item.value.strip():
                    try:
                        # カンマを除去して数値変換
                        clean_value = item.value.replace(',', '')
                        if clean_value.startswith('-'):
                            amount = -float(clean_value[1:])
                        else:
                            amount = float(clean_value)
                        total_amount += amount
                        has_valid_amount = True
                    except (ValueError, TypeError):
                        continue
            
            if has_valid_amount:
                # 金額をフォーマット
                formatted_amount = f"{int(total_amount):,}" if total_amount.is_integer() else f"{total_amount:,.0f}"
                if total_amount < 0:
                    formatted_amount = f"△{abs(int(total_amount)):,}"
                
                row[9] = f'"{formatted_amount}"'
        
        return [row]
    
    def _detect_item_name_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        項目名列を動的に検出
        
        Args:
            df: データフレーム
            
        Returns:
            Optional[str]: 項目名列名
        """
        # 優先順位順に検索
        candidates = ['項目名', '科目名', '勘定科目', 'Element', 'ElementName']
        
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        
        # パターンマッチング
        for col in df.columns:
            if any(pattern in col for pattern in ['項目', '科目', '勘定', 'Element']):
                return col
        
        # 最初の文字列型列を使用
        for col in df.columns:
            if df[col].dtype == 'object':
                return col
        
        return None
    
    def _detect_value_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        値列を動的に検出
        
        Args:
            df: データフレーム
            
        Returns:
            Optional[str]: 値列名
        """
        # 優先順位順に検索
        candidates = ['値', '金額', 'Value', 'Amount', '残高']
        
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        
        # パターンマッチング
        for col in df.columns:
            if any(pattern in col for pattern in ['値', '金額', 'Value', 'Amount']):
                return col
        
        # 数値っぽい列を検索
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                return col
            # 文字列だが数値が含まれている列
            elif df[col].dtype == 'object':
                # サンプルの値をチェック
                sample_values = df[col].dropna().head(10)
                numeric_count = 0
                for val in sample_values:
                    val_str = str(val).replace(',', '').replace('△', '-').strip()
                    try:
                        float(val_str)
                        numeric_count += 1
                    except:
                        pass
                
                if numeric_count > len(sample_values) * 0.5:  # 半分以上が数値
                    return col
        
        return None

    def _convert_to_csv_format(self, bs_table: List[List[str]]) -> pd.DataFrame:
        """
        貸借対照表をCSV形式に変換
        
        Args:
            bs_table: 貸借対照表データ
            
        Returns:
            pd.DataFrame: CSV形式のデータフレーム
        """
        # 列数を25に統一
        standardized_rows = []
        for row in bs_table:
            if len(row) < 25:
                row.extend([''] * (25 - len(row)))
            elif len(row) > 25:
                row = row[:25]
            standardized_rows.append(row)
        
        # データフレーム作成（ヘッダーなし）
        df = pd.DataFrame(standardized_rows)
        
        self.logger.info(f"貸借対照表変換完了: {len(df)}行")
        
        return df
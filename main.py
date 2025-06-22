#!/usr/bin/env python3
"""
CSV科目マッピング処理ツール

使用例:
    python main.py --input balance_seat.csv --config config.json
    python main.py --input balance_seat.csv --config config.json --output custom_name.csv
"""

import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path
from processor import CSVProcessor
from bs_transformer import BalanceSheetTransformer


def generate_output_filename(base_name: str = None) -> str:
    """
    出力ファイル名を生成（MMDDHHMM.csv形式）

    Args:
        base_name: ベースとなるファイル名（指定されない場合は現在日時を使用）

    Returns:
        str: 生成されたファイル名
    """
    if base_name:
        return base_name

    now = datetime.now()
    timestamp = now.strftime("%m%d%H%M")
    return f"{timestamp}.csv"


def validate_file_paths(input_path: str, config_path: str, output_path: str):
    """
    ファイルパスの妥当性を検証

    Args:
        input_path: 入力ファイルパス
        config_path: 設定ファイルパス
        output_path: 出力ファイルパス

    Raises:
        FileNotFoundError: 入力ファイルまたは設定ファイルが存在しない場合
        FileExistsError: 出力ファイルが既に存在する場合
    """
    # 入力ファイルの存在確認
    if not Path(input_path).exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

    # 設定ファイルの存在確認
    if not Path(config_path).exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    # 出力ファイルの重複確認
    if Path(output_path).exists():
        raise FileExistsError(f"出力ファイルが既に存在します: {output_path}")


def setup_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数のパーサーを設定"""
    parser = argparse.ArgumentParser(
        description="CSVファイルの科目マッピング処理を実行します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --input balance_seat.csv --config config.json
  %(prog)s --input balance_seat.csv --config config.json --output result.csv
  %(prog)s --input balance_seat.csv --config config.json --verbose
        """
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="入力CSVファイルのパス"
    )

    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="設定ファイルのパス（デフォルト: config.json）"
    )

    parser.add_argument(
        "--output", "-o",
        help="出力CSVファイルのパス（指定しない場合は MMDDHHMM.csv 形式で自動生成）"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細なログ出力を有効にする"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際の処理は行わず、処理内容のみを表示する"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["standard", "bs"],
        default="standard",
        help="出力形式（standard: 通常の科目マッピング、bs: 貸借対照表形式）"
    )

    return parser


def setup_logging(verbose: bool = False):
    """ログ設定をセットアップ"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """メイン処理"""
    # コマンドライン引数の解析
    parser = setup_argument_parser()
    args = parser.parse_args()

    # ログ設定
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # 出力ファイル名の決定
        if args.format == "bs":
            # 貸借対照表形式の場合もMMDDHHmm.csv形式
            output_path = args.output or generate_output_filename()
        else:
            # 通常形式の場合は既存ロジック
            output_path = args.output or generate_output_filename()

        logger.info("=== CSV処理開始 ===")
        logger.info(f"入力ファイル: {args.input}")
        logger.info(f"設定ファイル: {args.config}")
        logger.info(f"出力ファイル: {output_path}")
        logger.info(f"処理形式: {args.format}")

        if args.dry_run:
            logger.info("ドライラン モードで実行します")

        # ファイルパスの妥当性検証
        if not args.dry_run:
            validate_file_paths(args.input, args.config, output_path)

        if args.format == "bs":
            # 貸借対照表変換モード
            processor = CSVProcessor(args.config)
            bs_transformer = BalanceSheetTransformer(processor.config)

            if args.dry_run:
                # ドライランモード: 設定内容の確認のみ
                logger.info("貸借対照表変換設定が正常に読み込まれました")

                # 入力ファイルの読み込みテスト
                df = processor.load_csv(args.input)
                logger.info(f"入力データが正常に読み込まれました（{df.shape}）")
                logger.info("ドライランが完了しました")
            else:
                # 実際の処理実行
                df = processor.load_csv(args.input)
                result_df = bs_transformer.transform_to_balance_sheet(df)

                # CSVファイルに保存
                result_df.to_csv(output_path, index=False, header=False, encoding='utf-8')

                logger.info("=== 処理完了 ===")
                logger.info(f"処理結果: {result_df.shape[0]}行 x {result_df.shape[1]}列")
                logger.info(f"出力ファイル: {output_path}")
        else:
            # 通常の科目マッピングモード
            processor = CSVProcessor(args.config)

            if args.dry_run:
                # ドライランモード: 設定内容の確認のみ
                logger.info("設定ファイルが正常に読み込まれました")
                logger.info(f"マッピング定義数: {len(processor.account_mapping)}")

                # 入力ファイルの読み込みテスト
                df = processor.load_csv(args.input)
                logger.info(f"入力データが正常に読み込まれました（{df.shape}）")
                logger.info("ドライランが完了しました")

            else:
                # 実際の処理実行
                result_df = processor.process(args.input, output_path)

                logger.info("=== 処理完了 ===")
                logger.info(f"処理結果: {result_df.shape[0]}行 x {result_df.shape[1]}列")
                logger.info(f"出力ファイル: {output_path}")

    except FileNotFoundError as e:
        logger.error(f"ファイルエラー: {e}")
        sys.exit(1)

    except FileExistsError as e:
        logger.error(f"出力ファイルエラー: {e}")
        logger.error("既存ファイルの上書きはサポートされていません")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"データエラー: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

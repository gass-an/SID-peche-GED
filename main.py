from __future__ import annotations

import argparse
import logging
import sys
import time

import psycopg

from src.api.province_sud_client import ProvinceSudClient
from src.config import TABLES, load_settings, validate_table_name
from src.database.connection import check_connection, connect
from src.database.repository import find_json_columns, relation_statistics
from src.database.schema import reset_tables, validate_reset_scope
from src.extraction.peche_extractor import (
    DownloadResult,
    ExtractionResult,
    download_tables,
    import_table,
)
from src.extraction.progress import format_count, format_duration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import des données de pêche Province Sud")
    parser.add_argument("table", nargs="?", help="table unique à importer")
    parser.add_argument(
        "--depuis-json",
        "--from-json",
        action="store_true",
        help="saute le téléchargement et charge la base depuis data/raw",
    )
    args = parser.parse_args()
    if args.table:
        try:
            validate_table_name(args.table)
        except ValueError as exc:
            parser.error(str(exc))
    return args


def print_summary(
    downloads: list[DownloadResult],
    results: list[ExtractionResult],
    total_elapsed: float,
) -> None:
    print("\nExtraction terminée\n")
    print(f"{'Table':<34} | {'Pages':>7} | {'JSON':>12} | {'Base':>12} | {'Temps':>8}")
    print("-" * 84)
    downloads_by_table = {result.table: result for result in downloads}
    for result in results:
        download = downloads_by_table[result.table]
        pages = format_count(download.pages, 7) if download.pages else f"{'-':>7}"
        print(
            f"{result.table:<34} | {pages} | "
            f"{format_count(download.rows, 12)} | "
            f"{format_count(result.database_rows, 12)} | "
            f"{format_duration(download.elapsed_seconds + result.elapsed_seconds)}"
        )
        if result.child_table:
            print(
                f"{result.child_table:<34} | {'':>7} | {'':>12} | "
                f"{format_count(result.child_rows, 12)} | {'':>8}"
            )
    print("-" * 84)
    print(
        f"{'Temps global':<34} | {'':>7} | {'':>12} | {'':>12} | "
        f"{format_duration(total_elapsed)}"
    )
    print("\nToutes les tables ont été récupérées correctement.")


def run() -> int:
    started_at = time.monotonic()
    args = parse_args()
    try:
        settings = load_settings(require_api_key=not args.depuis_json)
    except ValueError as exc:
        logging.error("Configuration invalide : %s", exc)
        return 2
    selected_tables = [args.table] if args.table else TABLES

    try:
        validate_reset_scope(selected_tables)
        if args.depuis_json:
            logging.info("Mode JSON local : aucun appel à la source")
            missing = [
                settings.raw_data_dir / f"{table_name}.json"
                for table_name in selected_tables
                if not (settings.raw_data_dir / f"{table_name}.json").is_file()
            ]
            if missing:
                names = ", ".join(path.name for path in missing)
                raise FileNotFoundError(f"Fichiers JSON absents : {names}")
            downloads = [
                DownloadResult(
                    table_name,
                    0,
                    0,
                    (settings.raw_data_dir / f"{table_name}.json").stat().st_size,
                )
                for table_name in selected_tables
            ]
        else:
            logging.info("Phase 1/2 : téléchargement de l'instantané JSON")
            with ProvinceSudClient(settings.api_key, settings.http_timeout) as client:
                downloads = download_tables(
                    client, selected_tables, settings.raw_data_dir
                )
        pages_by_table = {result.table: result.pages for result in downloads}

        logging.info("Reconstruction et chargement de PostgreSQL depuis les JSON")
        with connect(settings) as connection:
            check_connection(connection)
            reset_tables(connection, selected_tables)
            results = []
            for table_name in selected_tables:
                results.append(
                    import_table(
                        connection,
                        table_name,
                        settings.raw_data_dir,
                        pages_by_table[table_name],
                    )
                )
                if args.depuis_json:
                    imported = results[-1]
                    index = selected_tables.index(table_name)
                    downloads[index] = DownloadResult(
                        table_name,
                        0,
                        imported.api_rows,
                        downloads[index].bytes_written,
                    )
            json_columns = find_json_columns(connection, selected_tables)
            if json_columns:
                raise RuntimeError(f"Colonnes JSON/JSONB encore présentes : {json_columns}")
            if not args.table:
                logging.info("Analyse des relations principales :")
                for relation, non_null, valid, orphans in relation_statistics(connection):
                    logging.info(
                        "%s — non nulles : %d, valides : %d, orphelines : %d",
                        relation, non_null, valid, orphans,
                    )
    except psycopg.OperationalError as exc:
        logging.error(
            "Impossible de se connecter à PostgreSQL.\n\n"
            "Vérifiez que le conteneur est démarré avec :\n\n"
            "docker compose up -d\n\nDétail : %s", exc,
        )
        return 1
    except Exception as exc:
        logging.error("Extraction interrompue : %s", exc)
        return 1

    print_summary(downloads, results, time.monotonic() - started_at)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(run())

#!/usr/bin/env python3
"""
ASC Analytics — скачивает App Downloads и Discovery & Engagement из App Store Connect API v2.

Использование:
    python3 asc_fetch_analytics.py --project ./ASA/asa-monitoring --asc-config ./ASO/config/asc_config.env
    python3 asc_fetch_analytics.py --project ./ASA/asa-monitoring --asc-config ./ASO/config/asc_config.env --days 7

Выходные файлы (в {project}/data/reports/):
    asc_downloads_YYYYMMDD.csv       — первичные загрузки по дате/стране/источнику
    asc_discovery_YYYYMMDD.csv       — impressions/page views/taps по источнику

Зависимости: pip install PyJWT requests
"""

import argparse
import csv
import gzip
import io
import json
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

try:
    import jwt
    import requests
except ImportError:
    print("Установи зависимости: pip install PyJWT requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def load_config(asc_config_path: str) -> dict:
    """Читает ASC_KEY_ID, ASC_ISSUER_ID, ASC_APP_ID из env-файла."""
    config = {}
    for line in Path(asc_config_path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip()
    required = ["ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_APP_ID"]
    for r in required:
        if not config.get(r):
            raise ValueError(f"Не найден {r} в {asc_config_path}")
    return config


def find_key_file(key_id: str, asc_config_path: str) -> Path:
    """Ищет AuthKey_{KEY_ID}.p8 рядом с конфигом."""
    config_dir = Path(asc_config_path).parent
    candidates = [
        config_dir / "asc_keys" / f"AuthKey_{key_id}.p8",
        config_dir / f"AuthKey_{key_id}.p8",
        Path.home() / ".config" / "aso-tools" / "keys" / f"AuthKey_{key_id}.p8",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Ключ AuthKey_{key_id}.p8 не найден. Ожидался в: {[str(c) for c in candidates]}"
    )


def make_token(config: dict, key_path: Path) -> str:
    private_key = key_path.read_text()
    payload = {
        "iss": config["ASC_ISSUER_ID"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 1200,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(
        payload, private_key, algorithm="ES256",
        headers={"kid": config["ASC_KEY_ID"]}
    )


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

BASE = "https://api.appstoreconnect.apple.com/v1"


def get(url, headers, **params):
    r = requests.get(url, headers=headers, params=params or None, timeout=20)
    r.raise_for_status()
    return r.json()


def post(url, headers, body):
    h = {**headers, "Content-Type": "application/json"}
    r = requests.post(url, headers=h, json=body, timeout=20)
    return r


def download_segment(url: str) -> str:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    if r.content[:2] == b"\x1f\x8b":
        return gzip.decompress(r.content).decode("utf-8")
    return r.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

# Report names we care about (matched by substring, case-insensitive)
DOWNLOAD_REPORT = "App Downloads Standard"
DISCOVERY_REPORT = "App Store Discovery and Engagement Standard"


def get_or_create_ongoing(app_id: str, headers: dict) -> str:
    """Возвращает ID существующего ONGOING-запроса или создаёт новый."""
    data = get(f"{BASE}/apps/{app_id}/analyticsReportRequests", headers)
    for req in data.get("data", []):
        if req["attributes"]["accessType"] == "ONGOING":
            return req["id"]

    # Создать новый
    body = {
        "data": {
            "type": "analyticsReportRequests",
            "attributes": {"accessType": "ONGOING"},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}},
        }
    }
    r = post(f"{BASE}/analyticsReportRequests", headers, body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Не удалось создать ONGOING: {r.text}")
    return r.json()["data"]["id"]


def find_report_id(request_id: str, report_name: str, headers: dict):
    data = get(f"{BASE}/analyticsReportRequests/{request_id}/reports", headers, limit=200)
    for rep in data.get("data", []):
        if rep["attributes"]["name"] == report_name:
            return rep["id"]
    return None


def get_instances(report_id: str, headers: dict) -> list[dict]:
    """Возвращает все доступные instances отчёта (каждый = один processingDate)."""
    data = get(f"{BASE}/analyticsReports/{report_id}/instances", headers, limit=50)
    return data.get("data", [])


def get_segment_url(instance_id: str, headers: dict):
    data = get(f"{BASE}/analyticsReportInstances/{instance_id}/segments", headers)
    segs = data.get("data", [])
    return segs[0]["attributes"]["url"] if segs else None


def parse_tsv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
    return list(reader)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_downloads(rows: list[dict]) -> dict:
    """
    Возвращает dict: (date, territory, source_type, download_type) → count

    Сырые строки отчёта разбиты по Device / App Version / Page Type / Pre-Order,
    поэтому одну (date, territory, source, download_type) комбинацию покрывают
    НЕСКОЛЬКО строк — их нужно СУММИРОВАТЬ, а не перезаписывать (иначе теряем
    установки: 26 вместо 55). Внутри одного instance это суммирование; across
    instances более поздний processingDate перезапишет весь per-date ключ
    (restatement), т.к. каждый instance полностью содержит свои даты.
    """
    result = {}
    for row in rows:
        key = (row["Date"], row["Territory"], row["Source Type"], row["Download Type"])
        result[key] = result.get(key, 0) + int(row["Counts"])
    return result


def aggregate_discovery(rows: list[dict]) -> dict:
    """
    Возвращает dict: (date, territory, source_type, event) → (counts, unique_counts)
    """
    result = {}
    for row in rows:
        key = (row["Date"], row["Territory"], row["Source Type"], row["Event"])
        c, u = result.get(key, (0, 0))
        result[key] = (c + int(row["Counts"]), u + int(row.get("Unique Counts", 0)))
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch ASC analytics data")
    parser.add_argument("--project", required=True, help="Папка проекта (asa-monitoring/)")
    parser.add_argument("--asc-config", required=True, help="Путь к asc_config.env")
    parser.add_argument("--days", type=int, default=7, help="Сколько последних дней включить (default: 7)")
    args = parser.parse_args()

    project_dir = Path(args.project)
    reports_dir = project_dir / "data"
    reports_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.asc_config)
    key_path = find_key_file(config["ASC_KEY_ID"], args.asc_config)
    token = make_token(config, key_path)
    headers = {"Authorization": f"Bearer {token}"}
    app_id = config["ASC_APP_ID"]

    cutoff = date.today() - timedelta(days=args.days)
    today_str = date.today().strftime("%Y%m%d")

    print(f"App ID: {app_id}")
    print(f"Период: {cutoff} — {date.today()}")

    # 1. ONGOING request
    print("\n[1/4] Получаю ONGOING запрос...")
    ongoing_id = get_or_create_ongoing(app_id, headers)
    print(f"  ONGOING ID: {ongoing_id}")

    # 2. Find report IDs
    print("[2/4] Ищу отчёты...")
    dl_report_id = find_report_id(ongoing_id, DOWNLOAD_REPORT, headers)
    disc_report_id = find_report_id(ongoing_id, DISCOVERY_REPORT, headers)
    if not dl_report_id or not disc_report_id:
        print(f"  ОШИБКА: не найдены отчёты. Downloads={dl_report_id}, Discovery={disc_report_id}")
        sys.exit(1)
    print(f"  Downloads: {dl_report_id}")
    print(f"  Discovery: {disc_report_id}")

    # 3. Download instances
    def fetch_report_data(report_id, label):
        instances = get_instances(report_id, headers)
        # Фильтруем по дате и берём только DAILY
        relevant = [
            i for i in instances
            if i["attributes"].get("granularity") == "DAILY"
            and i["attributes"].get("processingDate", "") >= str(cutoff)
        ]
        print(f"  {label}: {len(relevant)} instances из {len(instances)}")

        merged = {}
        for inst in sorted(relevant, key=lambda x: x["attributes"].get("processingDate", "")):
            proc_date = inst["attributes"]["processingDate"]
            url = get_segment_url(inst["id"], headers)
            if not url:
                print(f"    {proc_date}: нет данных (segment URL пустой)")
                continue
            content = download_segment(url)
            rows = parse_tsv(content)
            print(f"    {proc_date}: {len(rows)} строк")

            if label == "Downloads":
                chunk = aggregate_downloads(rows)
            else:
                chunk = aggregate_discovery(rows)
            # Позднейший файл перезаписывает (данные уточняются)
            merged.update(chunk)

        return merged

    print("[3/4] Скачиваю данные...")
    dl_data = fetch_report_data(dl_report_id, "Downloads")
    disc_data = fetch_report_data(disc_report_id, "Discovery")

    # 4. Save CSVs
    print("[4/4] Сохраняю...")

    dl_path = reports_dir / f"asc_downloads_{today_str}.csv"
    with open(dl_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "territory", "source_type", "download_type", "count"])
        for (date_, terr, src, dl_type), cnt in sorted(dl_data.items()):
            w.writerow([date_, terr, src, dl_type, cnt])
    print(f"  Saved: {dl_path}")

    disc_path = reports_dir / f"asc_discovery_{today_str}.csv"
    with open(disc_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "territory", "source_type", "event", "counts", "unique_counts"])
        for (date_, terr, src, event), (cnt, ucnt) in sorted(disc_data.items()):
            w.writerow([date_, terr, src, event, cnt, ucnt])
    print(f"  Saved: {disc_path}")

    # Quick summary
    asa_geos = {"DE", "AT", "CH"}
    ftd_total = sum(v for (d, t, s, dl), v in dl_data.items() if dl == "First-time download")
    ftd_asa_geo = sum(v for (d, t, s, dl), v in dl_data.items() if dl == "First-time download" and t in asa_geos)
    ftd_organic_other = ftd_total - ftd_asa_geo

    print(f"\n=== Сводка ===")
    print(f"First-time downloads всего: {ftd_total}")
    print(f"  DE/AT/CH: {ftd_asa_geo} (ASA + organic в кампейн-гео)")
    print(f"  Другие страны: {ftd_organic_other} (чистая органика)")

    by_src = defaultdict(int)
    for (d, t, s, dl), v in dl_data.items():
        if dl == "First-time download":
            by_src[s] += v
    print(f"\nПо источнику:")
    for src, cnt in sorted(by_src.items(), key=lambda x: -x[1]):
        print(f"  {src}: {cnt}")


if __name__ == "__main__":
    main()

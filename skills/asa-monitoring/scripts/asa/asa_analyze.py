#!/usr/bin/env python3
"""
asa_analyze.py — ASA Campaign Metrics Table

Usage:
    python3 asa_analyze.py \
        --metrics ./ASA/asa-monitoring/data/asa_metrics.csv \
        --unit-economics ./unit-economics/asa_pause_strategy.md \
        --amplitude ./amplitude_trials.csv \
        [--is-report ./ASA/asa-monitoring/data/is_report_latest.csv] \
        [--fetch-date 2026-05-11] \
        [--days 7]

Output:
    Таблица метрик по всем ENABLED кампаниям с impressions > 0.
    Решения о паузе/масштабировании принимаются отдельно на Этапе 2.
"""

import csv, re, sys, argparse
from collections import defaultdict
from datetime import date, timedelta


def parse_unit_economics(path):
    with open(path) as f:
        content = f.read()

    result = {}

    m = re.search(r'Max CPTrial[^|]*\|\s*\*?\*?\$?([\d.]+)', content)
    if m:
        result['max_cptrial'] = float(m.group(1))

    m = re.search(r'Proceeds per paid subscription\s*\|\s*\$?([\d.]+)', content)
    if m:
        result['proceeds'] = float(m.group(1))

    m = re.search(r'Trial.*?Paid conversion\s*\|\s*([\d.]+)%', content)
    if m:
        result['ttp_rate'] = float(m.group(1)) / 100

    if 'max_cptrial' not in result and 'proceeds' in result and 'ttp_rate' in result:
        result['max_cptrial'] = round(result['proceeds'] * result['ttp_rate'], 2)

    pause_thresholds = []
    for m in re.finditer(r'\|\s*[≤$]?\s*\$?([\d.]+)–?\$?([\d.]*)\s*\|[^|]+\|\s*После \*\*(\d+) installs', content):
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else float('inf')
        pause_at = int(m.group(3))
        pause_thresholds.append((lo, hi, pause_at))
    result['pause_thresholds'] = pause_thresholds

    if 'max_cptrial' not in result:
        raise ValueError(f"Не удалось найти Max CPTrial в {path}.")

    return result


def read_asa_metrics(path, fetch_date_str, days=7):
    target_end = fetch_date_str
    target_start = str(date.fromisoformat(fetch_date_str) - timedelta(days=days))

    with open(path) as f:
        rows = list(csv.DictReader(f))

    fd_rows = [r for r in rows if r['fetch_date'] == fetch_date_str]

    if not fd_rows:
        latest = max(r['fetch_date'] for r in rows)
        fd_rows = [r for r in rows if r['fetch_date'] == latest]
        print(f"[WARN] fetch_date {fetch_date_str} не найден, используем {latest}", file=sys.stderr)

    exact = [r for r in fd_rows if r['period_start'] == target_start and r['period_end'] == target_end]
    if exact:
        rows_to_use = exact
    else:
        max_period = max(
            (date.fromisoformat(r['period_end']) - date.fromisoformat(r['period_start'])).days
            for r in fd_rows
        )
        rows_to_use = [
            r for r in fd_rows
            if (date.fromisoformat(r['period_end']) - date.fromisoformat(r['period_start'])).days == max_period
        ]
        used_start = rows_to_use[0]['period_start'] if rows_to_use else '?'
        used_end = rows_to_use[0]['period_end'] if rows_to_use else '?'
        print(f"[INFO] Используем период {used_start} → {used_end} ({max_period}d)", file=sys.stderr)

    status_map = {r['campaign_id']: r.get('status', 'UNKNOWN') for r in fd_rows}

    camps = defaultdict(lambda: {
        'name': '', 'country': '', 'keyword': '', 'bid': 0.0,
        'impr': 0, 'taps': 0, 'inst': 0, 'spend': 0.0, 'status': 'UNKNOWN'
    })
    for r in rows_to_use:
        cid = r['campaign_id']
        d = camps[cid]
        d['name'] = r.get('campaign_name', '')
        d['country'] = r.get('country', '')
        d['keyword'] = r.get('keyword', '')
        d['bid'] = float(r.get('bid') or 0)
        d['impr'] += int(r.get('impressions') or 0)
        d['taps'] += int(r.get('taps') or 0)
        d['inst'] += int(r.get('installs') or 0)
        d['spend'] += float(r.get('spend') or 0)
        d['status'] = status_map.get(cid, 'UNKNOWN')

    return camps


def read_amplitude_trials(path):
    trials = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get('campaign_id', row.get('asa_campaign_id', '')).strip()
            t = row.get('trials', row.get('Total', '0')).strip()
            if cid and cid != '(none)':
                try:
                    trials[cid] = int(t)
                except ValueError:
                    pass
    return trials


def read_is_report(path):
    if not path:
        return {}

    kw_data = defaultdict(lambda: {'low': [], 'high': [], 'rank': None})
    with open(path) as f:
        for row in csv.DictReader(f):
            kw = row.get('searchTerm', '').lower()
            geo = row.get('countryOrRegion', '').upper()
            key = (kw, geo)
            try:
                kw_data[key]['low'].append(float(row['lowImpressionShare']))
                kw_data[key]['high'].append(float(row['highImpressionShare']))
                kw_data[key]['rank'] = row.get('rank', 'ONE')
            except (KeyError, ValueError):
                pass

    result = {}
    for (kw, geo), d in kw_data.items():
        if d['low']:
            avg_is = (sum(d['low']) / len(d['low']) + sum(d['high']) / len(d['high'])) / 2
            result[(kw, geo)] = {'is': avg_is, 'rank': d['rank']}
    return result


def run(args):
    ue = parse_unit_economics(args.unit_economics)
    print(f"[UE] Max CPTrial=${ue['max_cptrial']:.2f}  "
          f"Proceeds=${ue.get('proceeds','?')}  "
          f"TTP={ue.get('ttp_rate', '?')}", file=sys.stderr)

    fetch_date = args.fetch_date or str(date.today())
    days = args.days
    camps = read_asa_metrics(args.metrics, fetch_date, days=days)
    trials_map = read_amplitude_trials(args.amplitude)
    is_data = read_is_report(args.is_report)

    # Include PAUSED campaigns that have spend in the period (paused mid-period)
    visible = {cid: d for cid, d in camps.items()
               if d['status'] == 'ENABLED' or d['spend'] > 0}

    rows = []
    for cid, d in visible.items():
        trials = trials_map.get(cid, 0)
        cpi = round(d['spend'] / d['inst'], 2) if d['inst'] > 0 else None
        cptrial = round(d['spend'] / trials, 2) if trials > 0 else None
        ir = round(trials / d['inst'] * 100, 1) if d['inst'] > 0 and trials > 0 else None
        ipm = round(d['inst'] / d['impr'] * 1000, 1) if d['impr'] > 0 else 0
        kw = d['keyword'].lower()
        geo = d['country'].upper()
        is_info = is_data.get((kw, geo), {})
        is_val = is_info.get('is', None)
        rows.append({
            'name': d['name'],
            'status': d['status'],
            'country': d['country'],
            'impr': d['impr'],
            'taps': d['taps'],
            'inst': d['inst'],
            'spend': round(d['spend'], 2),
            'trials': trials,
            'ir': ir,
            'cpi': cpi,
            'cptrial': cptrial,
            'ipm': ipm,
            'is': is_val,
        })

    # Кампании с impressions, сортировка: сначала с триалами (по CPTrial), потом по installs, потом по impr
    with_impr = [r for r in rows if r['impr'] > 0]
    with_impr.sort(key=lambda x: (
        0 if x['trials'] > 0 else (1 if x['inst'] > 0 else 2),
        x['cptrial'] if x['cptrial'] else 9999,
        -x['inst'],
    ))

    without_impr = [r for r in rows if r['impr'] == 0]

    print()
    print(f"{'Кампания':<42} {'Geo':<3} {'Impr':>5} {'Inst':>5} {'Spend':>7} "
          f"{'Trials':>7} {'TR%':>5} {'CPI':>6} {'CPTrial':>8} {'IPM':>5} {'IS%':>5}")
    print("-" * 125)

    for r in with_impr:
        cpi_s   = f"${r['cpi']:.2f}" if r['cpi'] else "—"
        cpt_s   = f"${r['cptrial']:.2f}" if r['cptrial'] else "∞"
        tr_s    = f"{r['ir']:.0f}%" if r['ir'] else "—"
        is_s    = f"{r['is']*100:.0f}%" if r['is'] is not None else "—"
        paused  = " [P]" if r['status'] == 'PAUSED' else ""
        name_s  = (r['name'] + paused)[:42]
        print(f"{name_s:<42} {r['country']:<3} "
              f"{r['impr']:>5} {r['inst']:>5} ${r['spend']:>6.2f} "
              f"{r['trials']:>7} {tr_s:>5} {cpi_s:>6} {cpt_s:>8} {r['ipm']:>5.1f} {is_s:>5}")

    if without_impr:
        print(f"\n0 impressions: {len(without_impr)} кампаний — "
              + ", ".join(r['name'].replace('PS_DE_','').replace('PS_AT_','AT:').replace('PS_CH_','CH:')
                          for r in without_impr[:12])
              + ("..." if len(without_impr) > 12 else ""))

    total_spend  = sum(r['spend'] for r in rows)
    total_inst   = sum(r['inst'] for r in rows)
    total_trials = sum(r['trials'] for r in rows)
    print()
    n_enabled = sum(1 for r in rows if r['status'] == 'ENABLED')
    n_paused  = sum(1 for r in rows if r['status'] == 'PAUSED')
    print(f"{'='*60}")
    print(f"ENABLED: {n_enabled}  PAUSED со spend: {n_paused}  "
          f"(с impressions: {len(with_impr)}, без: {len(without_impr)})")
    print(f"Spend {days}d:    ${total_spend:.2f}")
    if total_inst:
        print(f"Installs {days}d:  {total_inst}   CPI: ${total_spend/total_inst:.2f}")
    if total_trials:
        avg_tr = round(total_trials / total_inst * 100, 1) if total_inst else 0
        print(f"Trials {days}d:   {total_trials}   TR: {avg_tr}%   CPTrial: ${total_spend/total_trials:.2f}")
    print(f"max_cptrial = ${ue['max_cptrial']:.2f}")


def main():
    parser = argparse.ArgumentParser(description='ASA Campaign Metrics')
    parser.add_argument('--metrics', required=True)
    parser.add_argument('--unit-economics', required=True)
    parser.add_argument('--amplitude', required=True)
    parser.add_argument('--is-report', default=None)
    parser.add_argument('--fetch-date', default=None)
    parser.add_argument('--days', default=7, type=int)
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()

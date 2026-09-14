

def parse_csv_file(file_path):
    import csv
    from io import StringIO
    
    # Skip header lines until we reach CSV data
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    csv_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '':
            csv_start = i + 1
            break
            
    csv_data = ''.join(lines[csv_start:])
    csv_reader = csv.DictReader(StringIO(csv_data))
    
    keyword_data = []
    for row in csv_reader:
        if row['Keyword'] == '': continue
        match_type = row['Match Type']
        keyword = row['Keyword']
        if match_type == "EXACT": keyword = f"[{keyword}]"
        keyword_dict = {
            'id': row['Keyword ID'],
            'groupId': row['Ad Group ID'],
            'keyword': keyword,
            'bid': float(row['CPT Bid']),
            'impressions': int(row['Impressions']),
            'installs': int(row['Installs (Total)']),
            'ttr': float(row['Taps']) / max(1, float(row['Impressions'])), # высчитываем сами для большей точности
            'avgCPA': float(row['Avg CPA (Total)'] or 0),
            'avgCPT': float(row['Average CPT'] or 0),
            "spends": float(row['Spend']),
            "taps": int(row['Taps']),
            'cr': float(row['Installs (Total)']) / max(1, float(row['Taps'])),
            'ii': float(row['Installs (Total)']) / max(1, float(row['Impressions'])),
        }
        keyword_data.append(keyword_dict)
        
    return keyword_data


def transform_asa_keywords(keywords: list[dict]):
    result = []
    for keyword in keywords:
        metadata = keyword['metadata']
        total = keyword['total']
        name = metadata['keyword']
        if metadata['matchType'] == 'EXACT': name = f"[{name}]"

        info = {
            'id': metadata['keywordId'],
            'groupId': metadata['adGroupId'],
            'keyword': name,
            'bid': float(metadata['bidAmount']['amount']),
            'impressions': total['impressions'],
            'installs': total['totalInstalls'],
            'ttr': total['ttr'], # taps / impressions
            'avgCPA': float(total['totalAvgCPI']['amount']),
            'avgCPT': float(total['avgCPT']['amount']),
            'spends': float(total['localSpend']['amount']),
            'taps': total['taps'],
            'cr': total['totalInstallRate'], # install / taps
        }
        info['ii'] = info['installs'] / max(1, info['impressions']) # install / impressions
        result.append(info)
    return result

def add_total_impressions(keywords: list[dict], keywords_total: list[dict]):
    keywords_dict_total = dict()
    if keywords_total:
        keywords_dict_total = {kw['keyword']:kw for kw in keywords_total}
    
    for kw in keywords:
        kw["impressions_total"] = keywords_dict_total[kw['keyword']]['impressions']
        kw["avgCPA_total"] = keywords_dict_total[kw['keyword']]['avgCPA']
        kw["avgCPT_total"] = keywords_dict_total[kw['keyword']]['avgCPT']
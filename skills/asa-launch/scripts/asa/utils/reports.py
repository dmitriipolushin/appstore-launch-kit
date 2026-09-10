symbols = "💚🟣👌🔽🔻❌"

def __get_symbol(bid, new_bid, multiplier):
    action = "?"
    if new_bid == 0: 
        action = symbols[5]
    elif new_bid > bid: 
        action = symbols[0] if multiplier > 1.15 else symbols[1]
    elif new_bid < bid: 
        action = symbols[4] if multiplier < 0.85 else symbols[3]
    elif new_bid == bid: 
        action = symbols[2]
    return action

def make_txt_report(sorted_keywords, output_path):
    final_str = ""
    total_up = 0
    total_down = 0
    total_remove = 0
    total_stable = 0
    max_text = max(sorted_keywords, key=lambda x:len(x['keyword']))['keyword']
    max_text_len = len(max_text)
    for item in sorted_keywords:
        cpa = item.get('avgCPA', 0)
        cpt = item.get('avgCPT', 0)
        cr = 100 * item.get('cr', 0)
        taps = item.get('taps', 0)
        ttr = 100 * taps / max(1, item.get('impressions', 0))
        install_per_impression = 100 * item.get('installs', 0) / max(1, item.get('impressions', 0))
        impr = item.get('impressions', 0)
        impr_t = item.get('impressions_total', 0)
        bid = item.get('bid', 0)
        score = item['score']
        key = item['keyword']
        space_count = max_text_len//3 - len(key)
        key = key + (" " * space_count)
        new_bid = item.get('new_bid', 0)
        multiplier = item.get('new_bid_multiplier', 1)
        spend = item.get('spends', 0)
        installs = item.get('installs', 0)
        action = __get_symbol(bid, new_bid, multiplier)
        if new_bid == 0:
            total_remove += 1
        elif new_bid > bid: 
            action = f"{action} {new_bid:.2f}"
            total_up += 1
        elif new_bid < bid: 
            action = f"{action} {new_bid:.2f}"
            total_down += 1
        elif new_bid == bid: 
            total_stable += 1
        str_row = f"{key} | Score: {score:.3f}; Bid: {bid}; Action: {action}; Avg CPA: {cpa:.2f}; Avg CPT: {cpt:.2f}; CR: {cr:.1f}%; TTR: {ttr:.2f}%; II: {install_per_impression:.2f}%; Taps: {taps}; Installs: {installs}; Impressions: {impr}; Impressions Total: {impr_t}; Spend: {spend:.2f}"
        final_str += str_row + "\n"

    info = f"{symbols[2]} - keep; {symbols[0]} - up 1.2; {symbols[4]} - down 0.8; {symbols[1]} - up 1.1; {symbols[3]} - down 0.9; {symbols[5]} - remove\n"
    info += f"Total Up: {total_up}; Total Down: {total_down}; Total Remove: {total_remove}; Total Stable: {total_stable}\n\n"
    final_str = info + final_str
    
    with open(output_path, "w") as file:
        file.write(final_str)


def float_to_str(value, precision=2):
    return f"{value:.{precision}f}".replace('.', ',')

def make_csv_report(sorted_keywords, output_path):
    import csv
    
    # Define CSV headers
    headers = ['Keyword', 'Group', 'Score', 'Current Bid', 'New Bid', 'Action', 'Multiplier', 
              'Avg CPA', 'Avg CPT', 'CR', 'TTR', "II", 'Taps', 'Installs', 'Impressions', 'Impressions Total', 'Spend']
    
    rows = []
    for item in sorted_keywords:
        cpa = item.get('avgCPA', 0)
        cpt = item.get('avgCPT', 0)
        cr = 100 * item.get('cr', 0)
        taps = item.get('taps', 0)
        ttr = 100 * taps / max(1, item.get('impressions', 0))
        install_per_impression = 100 * item.get('installs', 0) / max(1, item.get('impressions', 0))
        impr = item.get('impressions', 0)
        impr_t = item.get('impressions_total', 0)
        bid = item.get('bid', 0)
        score = item['score']
        key = item['keyword']
        new_bid = item.get('new_bid', 0)
        multiplier = item.get('new_bid_multiplier', 1)
        spend = item.get('spends', 0)
        installs = item.get('installs', 0)
        
        action = __get_symbol(bid, new_bid, multiplier)
        
        row = {
            'Keyword': key,
            'Group': item.get('groupId', 0),
            'Score': float_to_str(score, 3),
            'Current Bid': float_to_str(bid),
            'New Bid': float_to_str(new_bid),
            'Action': action,
            'Multiplier': float_to_str(multiplier),
            'Avg CPA': float_to_str(cpa),
            'Avg CPT': float_to_str(cpt),
            'CR': float_to_str(cr),
            'TTR': float_to_str(ttr, 4),
            "II": float_to_str(install_per_impression),
            'Taps': taps,
            'Impressions': impr,
            'Impressions Total': impr_t,
            'Installs': installs,
            'Spend': float_to_str(spend)
        }
        rows.append(row)
    
    # Write main data to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t',)
        writer.writeheader()
        writer.writerows(rows)
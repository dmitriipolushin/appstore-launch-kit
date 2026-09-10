import json, math
from math import isclose
from utils.reports import make_txt_report, make_csv_report
from utils.parsing_data import parse_csv_file
from settings import Settings

# Initialize settings at module level
all_settings = Settings()

def impressions_score(impressions, impressions_threshold):
    # 0 => 1, (>=impressions_threshold) => 0
    impr = max(1, min(impressions, impressions_threshold))
    score_normalized = math.log(impressions_threshold / impr) / math.log(impressions_threshold)
    return score_normalized # [0..1]

def cpa_score(cpa, target_cpa_range):
    if cpa <= 0:
        return 0.0
        
    if cpa <= target_cpa_range[0]:
        # Smoothly approach 1.0 for values below min target
        val = 1 - cpa / target_cpa_range[0]
        val = pow(val, 0.5)
        return 0.9 + 0.1 * val
        
    if cpa >= target_cpa_range[1]:
        # Smoothly approach 0.0 for values above max target
        return 0.1 * (target_cpa_range[1] / cpa)
        
    # Linear interpolation between target range
    range_size = target_cpa_range[1] - target_cpa_range[0]
    position = (cpa - target_cpa_range[0]) / range_size
    return 0.9 - (position * 0.8) # Scale between 0.9 and 0.1

def score_keywords(keyword_data):
    settings = all_settings.scoring
    for kw_data in keyword_data:
        impressions = float(kw_data.get('impressions_total', kw_data.get('impressions', 0)))
        ttr = float(kw_data.get('ttr', 0))
        avg_cpa = float(kw_data.get('avgCPA', 0))
        cr = float(kw_data.get('cr', 0)) # [0..1]
        cr = pow(cr, 0.5)

        # Calculate the scores using normalized values
        normalized_impressions = impressions_score(
            impressions, 
            settings.impressions_threshold
        )
        normalized_cpa = cpa_score(avg_cpa, settings.target_cpa)

        score = (
            normalized_impressions * settings.weight_impression +
            ttr * settings.weight_ttr +
            normalized_cpa * settings.weight_cpa +
            cr * settings.weight_cr
        )
        if score > 1.00:
            print("WTF; Score > 1.00:", kw_data['keyword'])
        kw_data['score'] = score

    return sorted(keyword_data, key=lambda x: x['score'], reverse=True)

def adjust_bids_by_percent(keywords: list[dict], percent: float):
    settings = all_settings.autobid
    for kw in keywords:
        val = kw['bid']
        new_val = round(kw['bid'] * percent, 2)
        if isclose(val, new_val):
            new_val += 0.01
        new_val = min(new_val, settings.bid_range[1])
        new_val = max(new_val, settings.bid_range[0])
        kw['new_bid'] = new_val
        kw['new_bid_multiplier'] = percent

    return keywords


def adjust_bids_by_value(keywords: list[dict], value: float|None = None, set_value: float|None = None):
    settings = all_settings.autobid
    for kw in keywords:
        val = kw['bid']
        if set_value:
            new_val = set_value
        else:
            new_val = round(kw['bid'] + value, 2)
        
        new_val = min(new_val, settings.bid_range[1])
        new_val = max(new_val, settings.bid_range[0])
        kw['new_bid'] = new_val
        kw['new_bid_multiplier'] = new_val / val

    return keywords

def adjust_bids(keywords: list[dict]):
    settings = all_settings.autobid
    updated_keywords = [dict(kw) for kw in keywords]
    score_keywords(updated_keywords)

    for kw in updated_keywords:
        score = kw['score']
        bid = kw['bid']
        avg_cpa = kw['avgCPA']
        avg_cpt = kw['avgCPT']
        impressions_total = kw.get('impressions_total', kw['impressions'])
        avg_cpa_total = kw['avgCPA_total']
        avg_cpt_total = kw['avgCPT_total']
        # if kw["keyword"] == "[philippines]":
        #     print()
        # if kw.get('spends', 0) > 0:
        #     print()

        multiplier = 1.0
        step = 0.1
        if settings.score_range[1] <= score: multiplier += step
        if settings.score_range[0] >= score: multiplier -= step
            
        if avg_cpa > 0.000001:
            if settings.target_cpa[0] >= avg_cpa: multiplier += step
            if settings.target_cpa[1] <= avg_cpa: multiplier -= step
        
        low_impressions = settings.impressions_range[0] >= impressions_total
        if multiplier < 1.01 and low_impressions:
            multiplier = settings.low_impressions_multiplier
            if bid * multiplier > 1.0: # more than 1 dollar
                multiplier = 1.0
        
        if avg_cpt > 0.0001 and not low_impressions and avg_cpa_total > 0.000001: 
            # чтобы ставка не улетала в космос
            cpt = max(avg_cpt, (avg_cpt+avg_cpt_total)*0.5)
            allow_coef = 2.5
            if settings.target_cpa[1] <= avg_cpa_total:
                allow_coef = 1.5
            elif settings.target_cpa[0] >= avg_cpa_total:
                allow_coef = 3.5
            max_multiplier = allow_coef * (cpt + 0.02) / bid
            if multiplier > max_multiplier:
                multiplier = max_multiplier

        new_bid = round(bid * multiplier, 2)
        new_bid = min(new_bid, settings.bid_range[1])

        if isclose(new_bid, bid) and not isclose(multiplier, 1.0):
            new_bid += 0.01 if multiplier > 1.0 else -0.01

        if new_bid < settings.bid_range[0]:
            new_bid = settings.bid_range[0]
            
        new_bid = round(new_bid, 2)
        
        kw['new_bid'] = new_bid
        kw['new_bid_multiplier'] = multiplier
    
    return updated_keywords


def main():
    keyword_data = parse_csv_file("caches/test_keywords.csv")
    keywords_adjusted_bids = adjust_bids(keyword_data)
    keywords_adjusted_bids.sort(key=lambda x: x['score'], reverse=True)

    make_txt_report(keywords_adjusted_bids, "./asa_data_processed.txt")
    make_csv_report(keywords_adjusted_bids, "./asa_data_processed.csv")

if __name__ == "__main__":
    main()
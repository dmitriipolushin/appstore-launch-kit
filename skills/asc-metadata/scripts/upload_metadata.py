#!/usr/bin/env python3
"""
Upload ASO metadata (title, subtitle, keywords) to App Store Connect.

Usage:
    python3 upload_metadata.py \
        --app-id 6757700411 \
        --key-id M88ZA99USJ \
        --issuer-id 78672159-... \
        --key-file path/to/AuthKey.p8 \
        --locales en-US:title:subtitle:keywords es-MX:title:subtitle:keywords ...

Or pass a JSON file with the same structure:
    --json-file metadata.json

JSON format:
    [{"locale": "en-US", "title": "...", "subtitle": "...", "keywords": "..."}, ...]
"""

import argparse
import json
import sys
import time

import jwt
import requests

BASE = "https://api.appstoreconnect.apple.com/v1"


def make_token(key_id, issuer_id, key_file):
    key = open(key_file).read()
    return jwt.encode(
        {"iss": issuer_id, "exp": int(time.time()) + 1200, "aud": "appstoreconnect-v1"},
        key,
        algorithm="ES256",
        headers={"kid": key_id},
    )


def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_editable_app_info(app_id, headers):
    r = requests.get(f"{BASE}/apps/{app_id}/appInfos", headers=headers)
    r.raise_for_status()
    for info in r.json()["data"]:
        attrs = info["attributes"]
        state = attrs.get("appStoreState") or attrs.get("state", "")
        if state == "PREPARE_FOR_SUBMISSION":
            return info["id"]
    raise ValueError(f"No PREPARE_FOR_SUBMISSION appInfo found for app {app_id}")


def get_editable_version_id(app_id, headers):
    r = requests.get(
        f"{BASE}/apps/{app_id}/appStoreVersions?filter[appStoreState]=PREPARE_FOR_SUBMISSION",
        headers=headers,
    )
    r.raise_for_status()
    data = r.json()["data"]
    if not data:
        raise ValueError(f"No PREPARE_FOR_SUBMISSION version for app {app_id}")
    return data[0]["id"]


def get_version_loc_ids(version_id, headers):
    r = requests.get(
        f"{BASE}/appStoreVersions/{version_id}/appStoreVersionLocalizations",
        headers=headers,
    )
    r.raise_for_status()
    return {item["attributes"]["locale"]: item["id"] for item in r.json()["data"]}


def get_info_loc_ids(app_info_id, headers):
    r = requests.get(f"{BASE}/appInfos/{app_info_id}/appInfoLocalizations", headers=headers)
    r.raise_for_status()
    return {item["attributes"]["locale"]: item["id"] for item in r.json()["data"]}


def update_version_loc(loc_id, headers, keywords=None, description=None, whats_new=None, promotional_text=None):
    attrs = {}
    if keywords is not None: attrs["keywords"] = keywords
    if description is not None: attrs["description"] = description
    if whats_new is not None: attrs["whatsNew"] = whats_new
    if promotional_text is not None: attrs["promotionalText"] = promotional_text
    if not attrs:
        return
    payload = {"data": {"type": "appStoreVersionLocalizations", "id": loc_id, "attributes": attrs}}
    r = requests.patch(f"{BASE}/appStoreVersionLocalizations/{loc_id}", headers=headers, json=payload)
    r.raise_for_status()


def create_version_loc(version_id, locale, headers, keywords=None, description=None):
    attrs = {"locale": locale}
    if keywords is not None: attrs["keywords"] = keywords
    if description is not None: attrs["description"] = description
    payload = {
        "data": {
            "type": "appStoreVersionLocalizations",
            "attributes": attrs,
            "relationships": {
                "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
            },
        }
    }
    r = requests.post(f"{BASE}/appStoreVersionLocalizations", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["data"]["id"]


def update_info_loc(loc_id, name, subtitle, headers):
    attrs = {}
    if name:
        attrs["name"] = name
    if subtitle:
        attrs["subtitle"] = subtitle
    if not attrs:
        return
    payload = {"data": {"type": "appInfoLocalizations", "id": loc_id, "attributes": attrs}}
    r = requests.patch(f"{BASE}/appInfoLocalizations/{loc_id}", headers=headers, json=payload)
    r.raise_for_status()


def create_info_loc(app_info_id, locale, name, subtitle, headers):
    payload = {
        "data": {
            "type": "appInfoLocalizations",
            "attributes": {"locale": locale, "name": name or "", "subtitle": subtitle or ""},
            "relationships": {
                "appInfo": {"data": {"type": "appInfos", "id": app_info_id}}
            },
        }
    }
    r = requests.post(f"{BASE}/appInfoLocalizations", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["data"]["id"]


def upload(app_id, key_id, issuer_id, key_file, locales_data, dry_run=False):
    token = make_token(key_id, issuer_id, key_file)
    hdr = h(token)

    app_info_id = get_editable_app_info(app_id, hdr)
    version_id = get_editable_version_id(app_id, hdr)
    version_locs = get_version_loc_ids(version_id, hdr)
    info_locs = get_info_loc_ids(app_info_id, hdr)

    print(f"App: {app_id}")
    print(f"  appInfo (PREPARE_FOR_SUBMISSION): {app_info_id}")
    print(f"  version: {version_id}")
    print(f"  existing version locales: {list(version_locs.keys())}")
    print(f"  existing info locales: {list(info_locs.keys())}")
    print()

    for entry in locales_data:
        locale = entry["locale"]
        title = entry.get("title", "")
        subtitle = entry.get("subtitle", "")
        keywords = entry.get("keywords")
        description = entry.get("description")
        whats_new = entry.get("whats_new")
        promotional_text = entry.get("promotional_text")

        print(f"  [{locale}]")
        if dry_run:
            if title: print(f"    title:       {title}")
            if subtitle: print(f"    subtitle:    {subtitle}")
            if keywords: print(f"    keywords:    {keywords}")
            if description: print(f"    description: {description[:80]}...")
            if whats_new: print(f"    whats_new:   {whats_new[:80]}...")
            if promotional_text: print(f"    promo_text:  {promotional_text[:80]}...")
            continue

        version_kwargs = {k: v for k, v in {
            "keywords": keywords, "description": description,
            "whats_new": whats_new, "promotional_text": promotional_text
        }.items() if v is not None}

        if version_kwargs:
            if locale in version_locs:
                update_version_loc(version_locs[locale], hdr, **version_kwargs)
                print(f"    version fields updated: {list(version_kwargs.keys())}")
            else:
                create_version_loc(version_id, locale, hdr, **{k: v for k, v in version_kwargs.items() if k in ("keywords", "description")})
                print(f"    version loc created: {list(version_kwargs.keys())}")

        if title or subtitle:
            if locale in info_locs:
                update_info_loc(info_locs[locale], title, subtitle, hdr)
                print(f"    title/subtitle: updated")
            else:
                create_info_loc(app_info_id, locale, title, subtitle, hdr)
                print(f"    title/subtitle: created")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Upload ASO metadata to App Store Connect")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--issuer-id", required=True)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--json-file", help="JSON file with locale metadata array")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded, don't send")
    args = parser.parse_args()

    if args.json_file:
        locales_data = json.loads(open(args.json_file).read())
    else:
        print("Error: provide --json-file", file=sys.stderr)
        sys.exit(1)

    upload(args.app_id, args.key_id, args.issuer_id, args.key_file, locales_data, args.dry_run)


if __name__ == "__main__":
    main()

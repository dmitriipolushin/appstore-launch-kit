"""
Shared project config loader.
Reads per-project config files (keywords.txt, competitors.txt, etc.)
"""

from pathlib import Path
from typing import Optional


def load_keywords(config_dir: Path, sections: list = None) -> list:
    """
    Load keywords from config/keywords.txt.

    Args:
        config_dir: Path to project config/ directory
        sections: list of section names to include, e.g. ["primary", "long_tail"]
                  None = return all sections

    Returns:
        Flat list of keyword strings, deduplicated, preserving order.
    """
    keywords_file = config_dir / "keywords.txt"
    if not keywords_file.exists():
        return []

    seen = set()
    result = []
    current_section = None

    for raw_line in keywords_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            continue
        if sections is None or current_section in sections:
            if line not in seen:
                seen.add(line)
                result.append(line)

    return result


def load_our_app_id(config_dir: Path) -> Optional[str]:
    """
    Load our app's ID from config/our_app_id.txt.
    Returns None if file doesn't exist or is empty.
    """
    our_app_file = config_dir / "our_app_id.txt"
    if not our_app_file.exists():
        return None

    for raw_line in our_app_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#")[0].strip()
        if line:
            return line

    return None


def load_competitors(config_dir: Path) -> list:
    """
    Load tracked competitor app IDs from config/competitors.txt.
    Strips inline comments (# ...).

    Returns:
        List of app ID strings.
    """
    competitors_file = config_dir / "competitors.txt"
    if not competitors_file.exists():
        return []

    ids = []
    for raw_line in competitors_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#")[0].strip()
        if line:
            ids.append(line)

    return ids

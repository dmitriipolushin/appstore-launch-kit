"""Shared config loader for ASO tools. Import this before using any API keys."""
import os
from pathlib import Path
from dotenv import dotenv_values

CONFIG_DIR = Path.home() / ".config" / "aso-tools"
ENV_FILE = CONFIG_DIR / "api_keys.env"
KEYS_DIR = CONFIG_DIR / "keys"

if ENV_FILE.exists():
    for k, v in dotenv_values(str(ENV_FILE)).items():
        # Expand ~ in path values
        if v and v.startswith("~"):
            v = str(Path(v).expanduser())
        os.environ.setdefault(k, v)

# Resolve ASC private key path from KEY_ID if not set explicitly
if "ASC_KEY_ID" in os.environ and "ASC_PRIVATE_KEY_PATH" not in os.environ:
    os.environ["ASC_PRIVATE_KEY_PATH"] = str(KEYS_DIR / f"AuthKey_{os.environ['ASC_KEY_ID']}.p8")

# Легаси-имена переменных Apple Search Ads → канонические ASA_*.
# Нужно, чтобы старые api_keys.env (APPLE_ADS_*) продолжали работать.
for _legacy, _canonical in (
    ("APPLE_ADS_CLIENT_ID", "ASA_CLIENT_ID"),
    ("APPLE_ADS_TEAM_ID", "ASA_TEAM_ID"),
    ("APPLE_ADS_KEY_ID", "ASA_KEY_ID"),
    ("APPLE_ADS_ORG_ID", "ASA_ORG_ID"),
):
    if _legacy in os.environ and _canonical not in os.environ:
        os.environ[_canonical] = os.environ[_legacy]

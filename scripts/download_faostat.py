"""Download the official FAOSTAT bulk files used by the datathon pipeline.

Usage:
    python scripts/download_faostat.py

The files are intentionally ignored by Git. The URLs, update metadata, and
checksums are retained so every teammate can reproduce the same snapshot.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
METADATA = ROOT / "data" / "metadata"

FILES = {
    "trade_aggregate": (
        "Trade_CropsLivestock_E_All_Data_Normalized.zip",
        "https://bulks-faostat.fao.org/production/Trade_CropsLivestock_E_All_Data_(Normalized).zip",
    ),
    "trade_detailed_matrix": (
        "Trade_DetailedTradeMatrix_E_All_Data_Normalized.zip",
        "https://bulks-faostat.fao.org/production/Trade_DetailedTradeMatrix_E_All_Data_(Normalized).zip",
    ),
    "producer_prices": (
        "Prices_E_All_Data_Normalized.zip",
        "https://bulks-faostat.fao.org/production/Prices_E_All_Data_(Normalized).zip",
    ),
    # Added to unblock the import dependency ratio (risk_index_design.md
    # component 1). FBS covers 2010-present; if 2005-2009 is needed too,
    # also add FoodBalanceSheetsHistoric_E_All_Data_(Normalized).zip (FBSH).
    "food_balance_sheets": (
        "FoodBalanceSheets_E_All_Data_Normalized.zip",
        "https://bulks-faostat.fao.org/production/FoodBalanceSheets_E_All_Data_(Normalized).zip",
    ),
    "dataset_metadata": (
        "faostat_datasets_E.json",
        "https://bulks-faostat.fao.org/production/datasets_E.json",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "FAOSTAT-datathon-pipeline/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temporary.replace(destination)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)

    checksums: list[str] = []
    for key, (filename, url) in FILES.items():
        destination = (METADATA if key == "dataset_metadata" else RAW) / filename
        if not destination.exists():
            print(f"Downloading {key}...")
            download(url, destination)
        else:
            print(f"Keeping existing {destination}")
        checksums.append(f"{sha256(destination)}  {destination.relative_to(ROOT)}")

    (METADATA / "raw_checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    metadata = json.loads((METADATA / "faostat_datasets_E.json").read_text(encoding="utf-8"))
    selected = {
        item["DatasetCode"]: item
        for item in metadata["Datasets"]["Dataset"]
        if item["DatasetCode"] in {"PP", "TM", "TCL", "FBS"}
    }
    (METADATA / "faostat_selected_metadata.json").write_text(
        json.dumps(selected, indent=2) + "\n", encoding="utf-8"
    )
    print("FAOSTAT snapshot ready.")


if __name__ == "__main__":
    main()
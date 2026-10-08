"""Prepare the small, stable CSV extracts used in the Week 4 notebooks.

The source files are public data from the Office of Rail and Road and Public
Health Scotland.  Students do not need to run this script: the prepared CSVs
are committed beside the notebooks.  Keeping the preparation code makes every
selection and renamed column inspectable.
"""

from __future__ import annotations

import argparse
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd


ORR_USAGE_URL = (
    "https://dataportal.orr.gov.uk/media/1909/"
    "table-1410-passenger-entries-and-exits-and-interchanges-by-station.csv"
)
ORR_ATTRIBUTES_URL = (
    "https://dataportal.orr.gov.uk/media/ootlf0cn/"
    "table-6329-station-attributes-for-all-mainline-stations.ods"
)
PT_REFERRALS_URL = (
    "https://www.opendata.nhs.scot/dataset/0d36e992-ad75-4ff1-b692-094f3d873ad7/"
    "resource/cfc4b998-c3d6-418f-91e6-a17806de94e0/download/pt-referrals.csv"
)
PT_WAITING_URL = (
    "https://www.opendata.nhs.scot/dataset/0d36e992-ad75-4ff1-b692-094f3d873ad7/"
    "resource/585b3f5c-e32c-45ee-8fed-96187330ac83/download/"
    "pt-adjusted-patients-waiting.csv"
)
POPULATION_URL = (
    "https://www.opendata.nhs.scot/dataset/7f010430-6ce1-4813-b25c-f7f335bdc4dc/"
    "resource/27a72cc8-d6d8-430c-8b4f-3109a9ceadb1/download/"
    "hb2019_pop_est_20072026.csv"
)
BOARD_LABELS_URL = (
    "https://www.opendata.nhs.scot/dataset/9f942fdb-e59e-44f5-b534-d6e17229cc7b/"
    "resource/652ff726-e676-4a20-abda-435b98dd7bdc/download/hb14_hb19.csv"
)


def download(url: str, destination: Path) -> Path:
    """Download one source file and return its local path."""
    urllib.request.urlretrieve(url, destination)
    return destination


def source_path(argument: str | None, url: str, temporary_dir: Path, name: str) -> Path:
    """Use a supplied local source or download the official file."""
    if argument:
        return Path(argument)
    return download(url, temporary_dir / name)


def clean_number(series: pd.Series) -> pd.Series:
    """Turn ORR comma-formatted counts and [z] markers into numbers/NA."""
    cleaned = series.astype("string").str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def prepare_rail_data(usage_path: Path, attributes_path: Path, output_dir: Path) -> None:
    """Create one usage table and one station-details lookup."""
    usage_raw_df = pd.read_csv(usage_path, header=3)
    usage_raw_df = usage_raw_df.loc[
        usage_raw_df["Three Letter Code\n(TLC)"].notna()
        & (usage_raw_df["Station name"] != "Station name")
    ]

    usage_df = usage_raw_df[
        [
            "Three Letter Code\n(TLC)",
            "Station name",
            "Entries and exits:\nAll tickets",
            "Interchanges",
        ]
    ].copy()
    usage_df.columns = [
        "StationCode",
        "StationName",
        "EntriesExits",
        "Interchanges",
    ]
    usage_df["EntriesExits"] = clean_number(usage_df["EntriesExits"])
    usage_df["Interchanges"] = clean_number(usage_df["Interchanges"])
    usage_df = usage_df.sort_values("StationCode").reset_index(drop=True)

    attributes_raw_df = pd.read_excel(
        attributes_path,
        sheet_name="6329_station_attributes",
        header=3,
    )
    attributes_df = attributes_raw_df[
        [
            "Three Letter Code",
            "Station name",
            "Region",
            "Local authority: district or unitary",
            "Station facility owner",
        ]
    ].copy()
    attributes_df.columns = [
        "TLC",
        "StationName",
        "Region",
        "LocalAuthority",
        "StationFacilityOwner",
    ]
    attributes_df = attributes_df.loc[attributes_df["TLC"].notna()]
    attributes_df = attributes_df.sort_values("TLC").reset_index(drop=True)

    usage_df.to_csv(output_dir / "rail_station_usage.csv", index=False)
    attributes_df.to_csv(output_dir / "rail_station_details.csv", index=False)


def prepare_therapy_data(
    referrals_path: Path,
    waiting_path: Path,
    population_path: Path,
    board_labels_path: Path,
    output_dir: Path,
) -> None:
    """Create compact 2024/2025 therapy and health-board tables."""
    referrals_raw_df = pd.read_csv(referrals_path)
    referrals_df = referrals_raw_df[
        ["HB", "Month", "ReferralsReceived", "ReferralsAccepted"]
    ].copy()
    referrals_df["Month"] = referrals_df["Month"].astype("Int64")
    referrals_df["ReferralsReceived"] = referrals_df["ReferralsReceived"].astype("Int64")
    referrals_df["ReferralsAccepted"] = referrals_df["ReferralsAccepted"].astype("Int64")

    for year in [2024, 2025]:
        select_year = referrals_df["Month"] // 100 == year
        year_df = referrals_df.loc[select_year].copy()
        year_df = year_df.sort_values(["Month", "HB"]).reset_index(drop=True)
        year_df.to_csv(output_dir / f"therapy_referrals_{year}.csv", index=False)

    waiting_raw_df = pd.read_csv(waiting_path)
    waiting_df = waiting_raw_df[
        [
            "HB",
            "Month",
            "TotalPatientsWaiting",
            "NumberOfPatientsWaiting0To18Weeks",
            "NumberOfPatientsWaiting19To35Weeks",
            "NumberOfPatientsWaiting36To52Weeks",
            "NumberOfPatientsWaitingOver52Weeks",
        ]
    ].copy()
    waiting_df.columns = [
        "HB",
        "Month",
        "TotalPatientsWaiting",
        "Waiting0To18Weeks",
        "Waiting19To35Weeks",
        "Waiting36To52Weeks",
        "WaitingOver52Weeks",
    ]
    numeric_columns = waiting_df.columns.drop("HB")
    waiting_df[numeric_columns] = waiting_df[numeric_columns].astype("Int64")
    select_2025 = waiting_df["Month"] // 100 == 2025
    waiting_df = waiting_df.loc[select_2025]
    waiting_df = waiting_df.sort_values(["Month", "HB"]).reset_index(drop=True)
    waiting_df.to_csv(output_dir / "therapy_waiting_2025.csv", index=False)

    population_raw_df = pd.read_csv(population_path)
    select_year = population_raw_df["Year"] == 2025
    select_all_people = population_raw_df["Sex"] == "All"
    select_board = population_raw_df["HB"].str.startswith("S08")
    select_rows = select_year & select_all_people & select_board
    population_df = population_raw_df.loc[select_rows, ["HB", "AllAges"]].copy()
    population_df = population_df.rename(columns={"AllAges": "Population"})
    population_df = population_df.sort_values("HB").reset_index(drop=True)
    population_df.to_csv(output_dir / "health_board_population_2025.csv", index=False)

    board_labels_raw_df = pd.read_csv(board_labels_path)
    select_current = board_labels_raw_df["HBDateArchived"].isna()
    boards_df = board_labels_raw_df.loc[select_current, ["HB", "HBName"]].copy()
    boards_df = boards_df.rename(columns={"HBName": "HealthBoard"})
    boards_df = boards_df.sort_values("HB").reset_index(drop=True)
    boards_df.to_csv(output_dir / "health_boards.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usage-source")
    parser.add_argument("--attributes-source")
    parser.add_argument("--referrals-source")
    parser.add_argument("--waiting-source")
    parser.add_argument("--population-source")
    parser.add_argument("--board-labels-source")
    parser.add_argument("--output-dir", default=Path(__file__).parent, type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary_name:
        temporary_dir = Path(temporary_name)
        usage_path = source_path(
            args.usage_source, ORR_USAGE_URL, temporary_dir, "station_usage.csv"
        )
        attributes_path = source_path(
            args.attributes_source,
            ORR_ATTRIBUTES_URL,
            temporary_dir,
            "station_attributes.ods",
        )
        referrals_path = source_path(
            args.referrals_source, PT_REFERRALS_URL, temporary_dir, "referrals.csv"
        )
        waiting_path = source_path(
            args.waiting_source, PT_WAITING_URL, temporary_dir, "waiting.csv"
        )
        population_path = source_path(
            args.population_source, POPULATION_URL, temporary_dir, "population.csv"
        )
        board_labels_path = source_path(
            args.board_labels_source, BOARD_LABELS_URL, temporary_dir, "boards.csv"
        )

        prepare_rail_data(usage_path, attributes_path, args.output_dir)
        prepare_therapy_data(
            referrals_path,
            waiting_path,
            population_path,
            board_labels_path,
            args.output_dir,
        )


if __name__ == "__main__":
    main()

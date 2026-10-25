
from io import BytesIO

import pandas as pd


REQUIRED_COLUMNS = [
    "date",
    "campaign",
    "platform",
    "spend",
    "installs",
    "purchases",
    "revenue",
]

OPTIONAL_COLUMNS = [
    "impressions",
    "clicks",
    "campaign_type",
    "market",
]

NUMERIC_COLUMNS = [
    "spend",
    "installs",
    "purchases",
    "revenue",
    "impressions",
    "clicks",
]

TEXT_COLUMNS = [
    "campaign",
    "platform",
    "campaign_type",
    "market",
]


def load_uploaded_csv(uploaded_file):
    """
    Read, validate, and normalize an uploaded campaign CSV.

    Returns:
        tuple[pd.DataFrame, int]:
            The cleaned campaign data and the number of rows
            discarded because their dates were invalid.

    The function processes uploads in memory and does not
    modify the original campaigns.csv file.
    """

    if uploaded_file is None:
        raise ValueError("Please choose a CSV file first.")

    # Read the uploaded file without saving it to disk.
    try:
        file_bytes = uploaded_file.getvalue()

        if not file_bytes:
            raise ValueError("The uploaded file is empty.")

        df = pd.read_csv(BytesIO(file_bytes))

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Could not read the CSV file: {exc}"
        ) from exc

    if df.empty:
        raise ValueError(
            "The uploaded CSV contains no data rows."
        )

    # Normalize column names.
    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    # Reject duplicate column names after normalization.
    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated()].tolist()

        raise ValueError(
            "Duplicate column names found: "
            + ", ".join(duplicates)
            + ". Please correct the CSV."
        )

    # Validate required columns.
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Add optional columns when they are not supplied.
    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            if column in ("campaign_type", "market"):
                df[column] = "Unknown"
            else:
                df[column] = 0

    # Validate dates and count discarded rows.
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    invalid_dates = int(df["date"].isna().sum())

    df = df.dropna(subset=["date"]).copy()

    if df.empty:
        raise ValueError(
            "No rows contain valid dates. "
            "Please check the date column."
        )

    # Validate numeric columns.
    for column in NUMERIC_COLUMNS:
        original_values = df[column]

        converted_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        # Reject non-numeric values instead of silently
        # converting them to zero.
        invalid_values = (
            converted_values.isna()
            & original_values.notna()
        )

        if invalid_values.any():
            raise ValueError(
                f"Column '{column}' contains non-numeric "
                "values. Please correct the CSV."
            )

        # Missing numeric values are rejected so campaign
        # performance metrics are not calculated incorrectly.
        if converted_values.isna().any():
            raise ValueError(
                f"Column '{column}' contains blank values. "
                "Please fill them with 0 or a valid number."
            )

        # Reject negative campaign metrics.
        if (converted_values < 0).any():
            raise ValueError(
                f"Column '{column}' contains negative values. "
                "Please correct the CSV."
            )

        # Reject infinity and other non-finite numbers.
        if not converted_values.map(
            lambda value: pd.notna(value) and abs(value) != float("inf")
        ).all():
            raise ValueError(
                f"Column '{column}' contains invalid numbers."
            )

        df[column] = converted_values

    # Normalize text columns.
    for column in TEXT_COLUMNS:
        df[column] = (
            df[column]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

        df.loc[df[column] == "", column] = "Unknown"

    # Sort chronologically and reset row indexes.
    df = (
        df.sort_values("date")
        .reset_index(drop=True)
    )

    return df, invalid_dates

from pathlib import Path

import pandas as pd


def load_dataframe(
    file_path: Path,
    file_type: str
) -> pd.DataFrame:

    if file_type == "csv":
        return pd.read_csv(file_path)

    if file_type == "xlsx":
        return pd.read_excel(file_path)

    raise ValueError("Unsupported spreadsheet type")


def analyze_dataframe(df: pd.DataFrame) -> dict:
    column_info = []

    for column in df.columns:
        column_info.append({
            "name": str(column),
            "type": str(df[column].dtype),
            "missing_values": int(df[column].isna().sum())
        })

    numeric_df = df.select_dtypes(
        include="number"
    )

    numeric_summary = {}

    if not numeric_df.empty:
        description = numeric_df.describe()

        for column in description.columns:
            numeric_summary[str(column)] = {
                stat: float(value)
                for stat, value in description[column].items()
            }

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_info": column_info,
        "numeric_summary": numeric_summary
    }


def analyze_spreadsheet(
    file_path: Path,
    file_type: str
) -> dict:

    df = load_dataframe(
        file_path,
        file_type
    )

    return analyze_dataframe(df)
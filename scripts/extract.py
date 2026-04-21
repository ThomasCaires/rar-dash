import pandas as pd
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "PLANILHA PERFUMES.xlsx"


def load_data() -> pd.DataFrame:
    df = pd.read_excel(DATA_PATH, header=1)
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    return df


def save_data(df: pd.DataFrame) -> None:
    """Write updated dataframe back to the spreadsheet."""
    with pd.ExcelWriter(DATA_PATH, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False, startrow=1)

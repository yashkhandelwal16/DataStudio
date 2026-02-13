import os
import io
from typing import Optional, Union
import pandas as pd

def load_dataset(file_path: Optional[str] = None, file_content: Optional[bytes] = None, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Load a dataset from CSV, Excel, or JSON into a pandas DataFrame.
    Can load from a physical file path OR from raw bytes.
    """
    if file_content is not None:
        if not filename:
            raise ValueError("filename must be provided when loading from bytes.")
        _, ext = os.path.splitext(filename)
        input_data = io.BytesIO(file_content)
    elif file_path is not None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        _, ext = os.path.splitext(file_path)
        input_data = file_path
    else:
        raise ValueError("Either file_path or file_content must be provided.")

    ext = ext.lower()

    if ext == ".csv":
        # Use 'c' engine for speed and low_memory=False to avoid mixed-type guessing overhead
        df = pd.read_csv(input_data, engine='c', low_memory=False)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(input_data)
    elif ext == ".json":
        df = pd.read_json(input_data)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if df.empty:
        raise ValueError("The uploaded file appears to be empty.")

    return df


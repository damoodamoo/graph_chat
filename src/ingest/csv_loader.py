from pathlib import Path

import pandas as pd


class CsvLoader:
    """Utility class for loading CSV files into pandas DataFrames."""

    @staticmethod
    def load(
        file_path: str | Path,
        encoding: str = "utf-8",
        **kwargs,
    ) -> pd.DataFrame:
        """
        Load a CSV file and return it as a pandas DataFrame.

        Args:
            file_path: Path to the CSV file
            encoding: File encoding (default: utf-8)
            **kwargs: Additional arguments passed to pd.read_csv

        Returns:
            pandas DataFrame containing the CSV data

        Raises:
            FileNotFoundError: If the file does not exist
            pd.errors.EmptyDataError: If the file is empty
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        return pd.read_csv(path, encoding=encoding, **kwargs)

    @staticmethod
    def load_chunked(
        file_path: str | Path,
        chunk_size: int = 10000,
        encoding: str = "utf-8",
        **kwargs,
    ):
        """
        Load a large CSV file in chunks.

        Args:
            file_path: Path to the CSV file
            chunk_size: Number of rows per chunk
            encoding: File encoding (default: utf-8)
            **kwargs: Additional arguments passed to pd.read_csv

        Yields:
            pandas DataFrame chunks
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        for chunk in pd.read_csv(path, encoding=encoding, chunksize=chunk_size, **kwargs):
            yield chunk

"""
Database connection and query execution using SQLAlchemy.
Loads configuration from config/config.yaml and supports PostgreSQL or SQLite.
"""

import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class DatabaseManager:
    """
    Manages database connections and query execution.
    Supports PostgreSQL and SQLite via configuration.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize DatabaseManager by loading config and creating engine.

        Args:
            config_path: Path to config YAML. Defaults to config/config.yaml.
        """
        if config_path is None:
            project_root = Path(__file__).resolve().parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._engine: Optional[Engine] = None
        self._init_engine()
        print(f"DatabaseManager initialized. Database type: {self._config.get('database', {}).get('type', 'unknown')}")

    def _load_config(self) -> dict:
        """Load YAML configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not config:
            raise ValueError("Config file is empty")
        return config

    def _init_engine(self) -> None:
        """Create SQLAlchemy engine based on config database type."""
        db_config = self._config.get("database", {})
        db_type = (db_config.get("type") or "sqlite").strip().lower()
        name = db_config.get("name") or "ecommerce"

        if db_type == "sqlite":
            project_root = Path(__file__).resolve().parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / f"{name}.db"
            url = f"sqlite:///{db_path}"
            self._engine = create_engine(url, echo=False)
            print(f"SQLite engine created: {db_path}")
        elif db_type in ("postgresql", "postgres"):
            # Allow override via env for PostgreSQL
            url = os.environ.get(
                "DATABASE_URL",
                f"postgresql://localhost/{name}",
            )
            self._engine = create_engine(url, echo=False)
            print("PostgreSQL engine created")
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @property
    def engine(self) -> Engine:
        """Return the SQLAlchemy engine. Raises if not initialized."""
        if self._engine is None:
            raise RuntimeError("Engine not initialized")
        return self._engine

    def execute_query(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.

        Args:
            query: SQL query string.
            params: Optional dict of parameters for bound execution.

        Returns:
            DataFrame with query results.

        Raises:
            Exception: On execution or database errors.
        """
        try:
            with self.engine.connect() as conn:
                if params:
                    result = pd.read_sql(text(query), conn, params=params)
                else:
                    result = pd.read_sql(text(query), conn)
                print(f"Query returned {len(result)} rows")
                return result
        except Exception as e:
            print(f"execute_query error: {e}")
            raise

    def execute_query_from_file(self, file_path: str) -> pd.DataFrame:
        """
        Execute a SQL query from a file and return results as DataFrame.

        Args:
            file_path: Path to .sql file (relative to project root or absolute).

        Returns:
            DataFrame with query results.
        """
        path = Path(file_path)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            path = project_root / path
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            query = f.read()
        print(f"Executing query from file: {path}")
        return self.execute_query(query)

    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        Return column and type information for a table.

        Args:
            table_name: Name of the table.

        Returns:
            DataFrame with column name and type (implementation may vary by backend).
        """
        try:
            if self._config.get("database", {}).get("type", "").lower() == "sqlite":
                query = f"PRAGMA table_info({table_name})"
                df = self.execute_query(query)
                return df
            # PostgreSQL
            query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position;
            """
            return self.execute_query(query, {"table_name": table_name})
        except Exception as e:
            print(f"get_table_info error: {e}")
            raise

    def close(self) -> None:
        """Dispose of the engine and release connections."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            print("Database connection closed.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "config.yaml"
    db = DatabaseManager(config_path=str(config_path))
    try:
        # Test: list tables (SQLite)
        df = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        print(df)
    finally:
        db.close()

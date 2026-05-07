import duckdb
import pandas as pd
import os
import streamlit as st

# ── Pfad-Konfiguration ────────────────────────────────────────────────────────
# Passe diese Pfade an deine Ordnerstruktur an!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROCESSED_DIR = os.path.join(BASE_DIR, "processed")   # Parquet-Dateien
MAPS_DIR      = os.path.join(BASE_DIR, "maps")         # Kartenbilder (.png)
MAP_DATA_CSV  = os.path.join(BASE_DIR, "map_data.csv") # map_data.csv

# Exakte Dateinamen aus deinem processed/ Ordner
PARQUET_FILES = {
    "dmg":      ["dmg.parquet"],
    "grenades": ["grenades.parquet"],
    "kills":    ["kills.parquet"],
    "meta":     ["meta.parquet"],
}


class DataLoader:
    def __init__(self):
        self.con = duckdb.connect(database=":memory:")

    def _load_parquet_group(self, key: str) -> pd.DataFrame:
        """Lädt alle Parquet-Dateien einer Gruppe via DuckDB."""
        files = PARQUET_FILES[key]
        paths = []
        for f in files:
            full = os.path.join(PROCESSED_DIR, f)
            if os.path.exists(full):
                paths.append(full)
            else:
                st.warning(f"⚠️ Datei nicht gefunden: {full}")

        if not paths:
            st.warning(f"⚠️ Keine Dateien für '{key}' gefunden. Gesucht in: {PROCESSED_DIR}")
            return pd.DataFrame()

        path_list = ", ".join([f"'{p}'" for p in paths])
        query = f"SELECT * FROM read_parquet([{path_list}])"
        return self.con.execute(query).df()

    def _load_map_data(self) -> pd.DataFrame:
        """Lädt map_data für Koordinaten-Umrechnung."""
        # map_data.csv im Hauptordner
        if os.path.exists(MAP_DATA_CSV):
            df = pd.read_csv(MAP_DATA_CSV, index_col=0)
            df.index.name = "map"
            return df.reset_index()
        # map_data.parquet im processed/ Ordner
        alt_parquet = os.path.join(PROCESSED_DIR, "map_data.parquet")
        if os.path.exists(alt_parquet):
            df = self.con.execute(f"SELECT * FROM read_parquet('{alt_parquet}')").df()
            if "column0" in df.columns:
                df = df.rename(columns={"column0": "map"})
            return df
        # map_data.csv im processed/ Ordner
        alt_csv = os.path.join(PROCESSED_DIR, "map_data.csv")
        if os.path.exists(alt_csv):
            df = pd.read_csv(alt_csv, index_col=0)
            df.index.name = "map"
            return df.reset_index()
        st.warning("⚠️ map_data.csv nicht gefunden!")
        return pd.DataFrame(columns=["map","StartX","StartY","EndX","EndY","ResX","ResY"])

    def load_all(self) -> dict:
        """Lädt alle Datensätze und gibt sie als Dict zurück."""
        try:
            dmg      = self._load_parquet_group("dmg")
            grenades = self._load_parquet_group("grenades")
            kills    = self._load_parquet_group("kills")
            meta     = self._load_parquet_group("meta")
            map_data = self._load_map_data()

            # map-Spalte in kills/dmg/grenades ergänzen falls nötig
            if not meta.empty and "map" in meta.columns and "file" in meta.columns:
                file_map = meta[["file","map"]].drop_duplicates()
                if not kills.empty and "map" not in kills.columns and "file" in kills.columns:
                    kills = kills.merge(file_map, on="file", how="left")
                if not dmg.empty and "map" not in dmg.columns and "file" in dmg.columns:
                    dmg = dmg.merge(file_map, on="file", how="left")
                if not grenades.empty and "map" not in grenades.columns and "file" in grenades.columns:
                    grenades = grenades.merge(file_map, on="file", how="left")

            return {
                "dmg":      dmg,
                "grenades": grenades,
                "kills":    kills,
                "meta":     meta,
                "map_data": map_data,
            }

        except Exception as e:
            st.error(f"Fehler beim Laden der Daten: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None

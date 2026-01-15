"""
Module d'ingestion des données multi-sources (EU / Non-EU)
Version : Case-Insensitive (Compatible Linux/Windows)
"""
import pandas as pd
from pathlib import Path
import streamlit as st
import os
from typing import Dict, Tuple


class DataIngestion:
    """Gestionnaire d'ingestion des données depuis les dossiers EU et Non-EU"""

    def __init__(self, base_path="datasets"):
        self.base_path = Path(base_path)
        self.eu_path = self.base_path / "eu"
        self.non_eu_path = self.base_path / "non-eu"

        # Noms génériques attendus (sans extension)
        self.file_types = ["products", "location", "orders", "customers"]

    def _find_file_insensitive(self, directory: Path, filename: str) -> Path:
        """
        Cherche un fichier dans un dossier en ignorant la casse (Majuscule/Minuscule).
        Ex: Trouve 'Products.csv' même si on cherche 'products.csv'.
        """
        if not directory.exists():
            return None

        target = f"{filename}.csv".lower()

        # On liste tous les fichiers du dossier réel
        try:
            for actual_file in os.listdir(directory):
                if actual_file.lower() == target:
                    return directory / actual_file
        except Exception:
            return None

        return None

    def _load_csv(self, filepath: Path) -> pd.DataFrame:
        """Charge un fichier CSV/TSV avec détection automatique du séparateur"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separators = ['\t', ',', ';', '|']

        for encoding in encodings:
            for sep in separators:
                try:
                    # On lit seulement les 2 premières lignes pour tester le séparateur (plus rapide)
                    pd.read_csv(filepath, encoding=encoding, sep=sep, engine='python', nrows=2)

                    # Si pas d'erreur, on charge tout
                    df = pd.read_csv(filepath, encoding=encoding, sep=sep, engine='python')

                    if len(df.columns) > 1 and len(df) > 0:
                        return df
                except Exception:
                    continue

        # Tentative désespérée
        try:
            df = pd.read_csv(filepath, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
            if len(df.columns) > 1:
                return df
        except Exception:
            pass

        st.warning(f"⚠️ Impossible de lire le fichier : {filepath.name}")
        return pd.DataFrame()

    def load_region(self, region: str) -> Dict[str, pd.DataFrame]:
        """Charge tous les fichiers d'une région"""
        region_path = self.eu_path if region == "eu" else self.non_eu_path

        # Gestion du dossier 'non-eu' qui peut s'appeler 'non_eu' parfois
        if region == "non_eu" and not region_path.exists():
            alt_path = self.base_path / "non_eu"
            if alt_path.exists():
                region_path = alt_path

        if not region_path.exists():
            st.error(f"❌ Dossier introuvable : {region_path}")
            return {}

        data = {}

        for file_type in self.file_types:
            # --- CORRECTION MAJEURE ICI ---
            # On cherche le fichier de manière intelligente (Case Insensitive)
            found_path = self._find_file_insensitive(region_path, file_type)

            if found_path and found_path.exists():
                df = self._load_csv(found_path)
                if not df.empty:
                    df['region'] = 'EU' if region == "eu" else 'Non-EU'
                    data[file_type] = df
                    # Petit message discret pour ne pas spammer l'interface
                    print(f"Chargé : {found_path.name}")
            else:
                # On ne bloque pas, mais on signale dans les logs serveur
                print(f"Manquant : {file_type}.csv dans {region}")

        return data

    def load_all_data(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """Charge tout"""
        st.info("🔄 Lecture des fichiers en cours...")

        # On enlève les spinners multiples qui ralentissent l'affichage
        eu_data = self.load_region("eu")
        non_eu_data = self.load_region("non_eu")

        return eu_data, non_eu_data

    def merge_regions(self, eu_data: Dict[str, pd.DataFrame],
                      non_eu_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Fusionne les dictionnaires"""
        merged_data = {}

        for file_type in self.file_types:
            dfs = []
            if file_type in eu_data: dfs.append(eu_data[file_type])
            if file_type in non_eu_data: dfs.append(non_eu_data[file_type])

            if dfs:
                merged_data[file_type] = pd.concat(dfs, ignore_index=True)

        return merged_data
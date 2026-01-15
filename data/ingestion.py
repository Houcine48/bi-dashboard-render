"""
Module d'ingestion des données multi-sources (EU / Non-EU)
"""
import pandas as pd
from pathlib import Path
import streamlit as st
from typing import Dict, Tuple


class DataIngestion:
    """Gestionnaire d'ingestion des données depuis les dossiers EU et Non-EU"""

    def __init__(self, base_path="datasets"):
        self.base_path = Path(base_path)
        self.eu_path = self.base_path / "eu"
        self.non_eu_path = self.base_path / "non-eu"

        # Noms des fichiers attendus
        self.file_types = ["products", "location", "orders", "customers"]

    def _load_csv(self, filepath: Path) -> pd.DataFrame:
        """Charge un fichier CSV/TSV avec détection automatique du séparateur"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separators = ['\t', ',', ';', '|']  # Tab, virgule, point-virgule, pipe

        for encoding in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(filepath, encoding=encoding, sep=sep, engine='python')

                    # Vérifier que le DataFrame a du sens (plus d'une colonne)
                    if len(df.columns) > 1 and len(df) > 0:
                        sep_name = {'\t': 'TAB', ',': 'Virgule', ';': 'Point-virgule', '|': 'Pipe'}
                        st.info(f"📄 {filepath.name}: détecté → {sep_name[sep]} | Encodage: {encoding}")
                        return df
                except Exception:
                    continue

        # Si aucun séparateur ne fonctionne, essai avec détection auto
        try:
            st.warning(f"⚠️ {filepath.name}: tentative de détection automatique...")
            df = pd.read_csv(
                filepath,
                encoding='utf-8',
                sep=None,  # Détection automatique
                engine='python',
                on_bad_lines='skip'
            )
            if len(df.columns) > 1:
                st.success(f"✅ {filepath.name} chargé avec {len(df)} lignes")
                return df
        except Exception as e:
            pass

        st.error(f"❌ Impossible de charger {filepath.name}")
        st.info(f"💡 Astuce: Sauvegarde le fichier en CSV UTF-8 depuis Excel:")
        st.write("Fichier → Enregistrer sous → Type: CSV UTF-8")
        return pd.DataFrame()

    def load_region(self, region: str) -> Dict[str, pd.DataFrame]:
        """
        Charge tous les fichiers d'une région (EU ou Non-EU)

        Args:
            region: 'eu' ou 'non_eu'

        Returns:
            Dict avec les DataFrames {type: DataFrame}
        """
        region_path = self.eu_path if region == "eu" else self.non_eu_path

        if not region_path.exists():
            st.error(f"❌ Le dossier {region_path} n'existe pas")
            return {}

        data = {}

        for file_type in self.file_types:
            filepath = region_path / f"{file_type}.csv"

            if filepath.exists():
                df = self._load_csv(filepath)
                if not df.empty:
                    # Ajouter une colonne pour identifier la région
                    df['region'] = 'EU' if region == "eu" else 'Non-EU'
                    data[file_type] = df
                    st.success(f"✅ {file_type}.csv chargé ({region.upper()}): {len(df)} lignes")
            else:
                st.warning(f"⚠️ Fichier manquant: {filepath.name}")

        return data

    def load_all_data(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Charge toutes les données EU et Non-EU

        Returns:
            Tuple (eu_data, non_eu_data)
        """
        st.info("📥 Chargement des données...")

        with st.spinner("Chargement des données EU..."):
            eu_data = self.load_region("eu")

        with st.spinner("Chargement des données Non-EU..."):
            non_eu_data = self.load_region("non_eu")

        return eu_data, non_eu_data

    def merge_regions(self, eu_data: Dict[str, pd.DataFrame],
                      non_eu_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Fusionne les données EU et Non-EU pour chaque type de fichier

        Args:
            eu_data: Données EU
            non_eu_data: Données Non-EU

        Returns:
            Dict avec les DataFrames fusionnés {type: DataFrame}
        """
        merged_data = {}

        for file_type in self.file_types:
            dfs_to_merge = []

            if file_type in eu_data:
                dfs_to_merge.append(eu_data[file_type])

            if file_type in non_eu_data:
                dfs_to_merge.append(non_eu_data[file_type])

            if dfs_to_merge:
                merged_df = pd.concat(dfs_to_merge, ignore_index=True)
                merged_data[file_type] = merged_df
                st.success(f"✅ {file_type} fusionné: {len(merged_df)} lignes totales")
            else:
                st.warning(f"⚠️ Aucune donnée pour {file_type}")

        return merged_data

    def get_data_summary(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Génère un résumé des données chargées

        Args:
            data: Dictionnaire des DataFrames

        Returns:
            DataFrame avec le résumé
        """
        summary = []

        for name, df in data.items():
            summary.append({
                'Fichier': name,
                'Lignes': len(df),
                'Colonnes': len(df.columns),
                'Régions': df['region'].nunique() if 'region' in df.columns else 'N/A',
                'Mémoire (MB)': round(df.memory_usage(deep=True).sum() / 1024 ** 2, 2)
            })

        return pd.DataFrame(summary)

    def validate_data_structure(self, data: Dict[str, pd.DataFrame]) -> bool:
        """
        Valide que les données ont la structure attendue (mode flexible)

        Args:
            data: Dictionnaire des DataFrames

        Returns:
            True si la structure est valide
        """
        # Colonnes essentielles minimales pour chaque type
        expected_columns = {
            'Customers': ['Customer ID', 'Customer Name'],
            'Location': ['Postal','Code','City','State','Region','Country/Region'],
            'Orders': ['Row ID','Order ID','Order Date','Ship Date','Ship Mode','Customer ID','Segment','Postal Code','Product ID','Sales','Quantity','Discount','Profit'],
            'Products': ['Product ID','Category','Sub-Category','Product Name']
        }

        validation_passed = True

        for file_type, expected_cols in expected_columns.items():
            if file_type in data:
                df = data[file_type]

                # Afficher les colonnes trouvées
                st.info(f"📋 {file_type}: colonnes détectées → {list(df.columns)}")

                # Normaliser les noms de colonnes (enlever espaces, minuscules)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                data[file_type] = df  # Sauvegarder avec colonnes normalisées

                missing_cols = [col for col in expected_cols if col not in df.columns]

                if missing_cols:
                    st.warning(f"⚠️ {file_type}: colonnes manquantes → {missing_cols}")
                    st.write(f"Colonnes disponibles: {list(df.columns)}")
                    validation_passed = False
                else:
                    st.success(f"✅ {file_type}: structure valide ({len(df)} lignes, {len(df.columns)} colonnes)")

        return validation_passed


# Fonction utilitaire pour Streamlit
@st.cache_data
def load_and_merge_data(base_path="datasets"):
    """
    Fonction cachée pour charger et fusionner les données
    Utilise le cache de Streamlit pour éviter les rechargements
    """
    ingestion = DataIngestion(base_path)
    eu_data, non_eu_data = ingestion.load_all_data()
    merged_data = ingestion.merge_regions(eu_data, non_eu_data)

    return merged_data, ingestion
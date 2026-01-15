"""
Module de nettoyage des données (Version Finale - Anti-Doublons)
"""
import pandas as pd
import numpy as np
import streamlit as st


class DataCleaning:

    def _get_quality_report(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return pd.DataFrame()
        dtypes = df.dtypes.astype(str)
        nan_pct = (df.isnull().sum() / len(df)) * 100
        report = pd.DataFrame({'Type': dtypes, '% NaN': nan_pct})
        report['% NaN'] = report['% NaN'].round(2)
        return report

    def _clean_numeric_column(self, series: pd.Series) -> pd.Series:
        # Sécurité : Si par malheur on reçoit un DataFrame (doublon), on prend la 1ère colonne
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]

        if pd.api.types.is_numeric_dtype(series): return series

        # Nettoyage
        cleaned = series.astype(str).str.replace(',', '.', regex=False)
        cleaned = cleaned.str.replace(r'[^\d.-]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce')

    def clean_dataset(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        st.subheader(f"🧹 Nettoyage : {dataset_name.capitalize()}")
        df_clean = df.copy()

        # ====================================================================
        # ETAPE 1 : SUPPRESSION AGRESSIVE DES DOUBLONS DE COLONNES
        # ====================================================================

        # 1. On supprime d'abord les doublons exacts s'il y en a
        df_clean = df_clean.loc[:, ~df_clean.columns.duplicated()]

        # 2. On renomme tout en minuscule "propre" (liste Python simple = pas d'erreur .str)
        new_cols = [str(c).strip().lower().replace(' ', '_') for c in df_clean.columns]
        df_clean.columns = new_cols

        # 3. CRUCIAL : On supprime les doublons CRÉÉS par la mise en minuscule
        # (Ex: 'Region' et 'region' deviennent tous les deux 'region' -> on en garde un seul)
        df_clean = df_clean.loc[:, ~df_clean.columns.duplicated(keep='last')]

        # 4. Mapping final pour être sûr d'avoir 'sales', 'order_date', etc.
        rename_map = {
            'ventes': 'sales',
            'ca': 'sales',
            'montant': 'sales',
            'sales_amount': 'sales',
            'marge': 'profit',
            'bénéfice': 'profit',
            'date': 'order_date',
            'date_commande': 'order_date',
            'quantité': 'quantity',
            'qte': 'quantity',
            'row_id': 'row_id',
            'order_id': 'order_id',
            'product_name': 'product_name'
        }
        df_clean = df_clean.rename(columns=rename_map)

        # ====================================================================

        # Rapport AVANT
        report_before = self._get_quality_report(df_clean)

        # ETAPE 2 : TYPAGE

        # A. Dates
        if 'order_date' in df_clean.columns:
            df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], errors='coerce')

        # B. Numériques
        target_cols = ['sales', 'profit', 'quantity', 'discount']
        for col in target_cols:
            if col in df_clean.columns:
                df_clean[col] = self._clean_numeric_column(df_clean[col])

        # ETAPE 3 : TEXTE (Avec sécurité anti-DataFrame)
        obj_cols = df_clean.select_dtypes(include=['object']).columns
        for col in obj_cols:
            # Sécurité : Si col est encore un DataFrame malgré tout, on force la Série
            series = df_clean[col]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]  # On prend la première

            df_clean[col] = series.astype(str).str.strip().str.title()

        # ETAPE 4 : NETTOYAGE LIGNES
        if 'sales' in df_clean.columns and 'order_date' in df_clean.columns:
            df_clean = df_clean.dropna(subset=['sales', 'order_date'])

        # Remplissage
        cat_cols = df_clean.select_dtypes(include=['object']).columns
        df_clean[cat_cols] = df_clean[cat_cols].fillna("Unknown")

        num_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        df_clean[num_cols] = df_clean[num_cols].fillna(0)

        if 'sales' in df_clean.columns and 'profit' not in df_clean.columns:
            df_clean['profit'] = 0.0

        # Rapport APRÈS
        report_after = self._get_quality_report(df_clean)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🔴 Avant")
            st.dataframe(report_before, use_container_width=True, height=150)
        with col2:
            st.markdown("#### 🟢 Après")
            st.dataframe(report_after, use_container_width=True, height=150)

        return df_clean

    def run_pipeline(self, data_dict: dict) -> dict:
        cleaned_data = {}
        with st.status("Traitement ETL en cours...", expanded=True):
            for name, df in data_dict.items():
                st.write(f"Standardisation de **{name}**...")
                cleaned_df = self.clean_dataset(df, name)
                cleaned_data[name] = cleaned_df
        return cleaned_data
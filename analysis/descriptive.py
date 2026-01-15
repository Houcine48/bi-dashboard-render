import pandas as pd


class DescriptiveAnalyst:
    """Module pour les statistiques descriptives"""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_correlation_matrix(self):
        """Calcule la corrélation"""
        numeric_df = self.df.select_dtypes(include=['float64', 'int64'])
        if numeric_df.empty: return None
        return numeric_df.corr()

    def get_summary_stats(self):
        """
        Retourne un tableau statistique UNIQUEMENT pour Profit, Quantity et Sales
        """
        # Colonnes cibles demandées
        target_cols = ['sales', 'profit', 'quantity']

        # Vérifier celles qui existent réellement dans le dataframe
        existing_cols = [col for col in target_cols if col in self.df.columns]

        if not existing_cols:
            return pd.DataFrame()

        # Calcul des stats et formatage (Transposé)
        stats = self.df[existing_cols].describe().T

        # On garde les indicateurs clés
        return stats[['count', 'mean', 'std', 'min', '50%', 'max']].rename(columns={'50%': 'median'})
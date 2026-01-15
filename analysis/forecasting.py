import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import plotly.graph_objects as go
from datetime import timedelta


class SalesForecaster:
    """
    Module de prévision par Séries Temporelles (Holt-Winters).
    Ce modèle capture spécifiquement : Niveau + Tendance + Saisonnalité.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        if 'order_date' in self.df.columns:
            self.df['order_date'] = pd.to_datetime(self.df['order_date'])

        self.model_fit = None
        self.df_ts = pd.Series(dtype='float64')
        self.metrics = {}

    def _prepare_time_series(self):
        """
        Prépare une série temporelle stricte (Index temporel + Valeur).
        Gère les trous dans les dates (important pour les séries temporelles).
        """
        if self.df.empty: return pd.Series(dtype='float64')

        # 1. Agrégation Hebdomadaire (Weekly 'W') pour lisser le bruit quotidien
        # 'MS' = Month Start (Mensuel) si tu veux encore plus lisse
        ts = self.df.set_index('order_date').resample('W')['sales'].sum()

        # 2. Remplissage des trous (Si une semaine a 0 vente, Holt-Winters n'aime pas les trous)
        # On remplit les manques par interpolation ou par 0
        ts = ts.asfreq('W').fillna(0)

        # On remplace les 0 stricts par une petite valeur (0.1) car Holt-Winters multiplicatif n'aime pas les 0
        ts = ts.replace(0, 0.1)

        self.df_ts = ts
        return ts

    def train_model(self):
        """Entraîne un modèle Holt-Winters (Triple Lissage Exponentiel)"""
        ts = self._prepare_time_series()

        # Il faut au moins 2 cycles complets pour la saisonnalité
        # Si on a moins de ~20 semaines, on ne peut pas faire de magie
        if len(ts) < 10:
            return False, "Pas assez d'historique (min 10 semaines)."

        # Split Train/Test (Les 15 dernières semaines pour tester)
        test_size = 15
        if len(ts) < 20: test_size = 2  # Sécurité pour petits datasets

        train = ts.iloc[:-test_size]
        test = ts.iloc[-test_size:]

        try:
            # --- MODÈLE HOLT-WINTERS ---
            # trend='add' : Tendance linéaire additive
            # seasonal='add' : Saisonnalité additive (les pics sont constants)
            # seasonal_periods=52 : On dit au modèle qu'un cycle dure 52 semaines (1 an)
            # Si tes données sont mensuelles, mets seasonal_periods=12
            model = ExponentialSmoothing(
                train,
                trend='add',
                seasonal='add',
                seasonal_periods=52 if len(train) > 52 else None
            )

            self.model_fit = model.fit(optimized=True)

            # Prédiction sur le jeu de test
            predictions = self.model_fit.forecast(len(test))

            # Métriques
            self.metrics = {
                'mae': mean_absolute_error(test, predictions),
                'rmse': np.sqrt(mean_squared_error(test, predictions)),
                'r2': r2_score(test, predictions)
            }

            # Ré-entraînement sur TOUT le dataset pour la prédiction future finale
            full_model = ExponentialSmoothing(
                ts,
                trend='add',
                seasonal='add',
                seasonal_periods=52 if len(ts) > 52 else None
            )
            self.model_fit = full_model.fit(optimized=True)

            quality = "Bonne" if self.metrics['r2'] > 0.4 else "Moyenne"
            return True, f"Modèle Holt-Winters entraîné (Qualité: {quality})"

        except Exception as e:
            return False, f"Erreur mathématique : {str(e)}"

    def predict_future(self, days=30):
        if self.model_fit is None:
            self.train_model()

        # Convertir jours en semaines (car notre modèle est hebdo)
        steps = int(days / 7) + 2

        # Forecast renvoie une série indexée par les dates futures
        future_series = self.model_fit.forecast(steps)

        # On évite les valeurs négatives (impossible pour des ventes)
        future_series[future_series < 0] = 0

        return pd.DataFrame({
            'Date': future_series.index,
            'Predicted_Sales': future_series.values
        })

    def plot_prediction(self, future_df):
        fig = go.Figure()

        # Données Historiques
        fig.add_trace(go.Scatter(
            x=self.df_ts.index,
            y=self.df_ts.values,
            mode='lines',
            name='Historique Réel',
            line=dict(color='#1f77b4', width=2)
        ))

        # Fitted Values (Ce que le modèle a compris du passé)
        # Ça permet de voir si le modèle "colle" bien à la courbe
        fig.add_trace(go.Scatter(
            x=self.model_fit.fittedvalues.index,
            y=self.model_fit.fittedvalues.values,
            mode='lines',
            name='Modélisation (Fit)',
            line=dict(color='orange', width=1, dash='dot'),
            opacity=0.7
        ))

        # Prédictions Futures
        fig.add_trace(go.Scatter(
            x=future_df['Date'],
            y=future_df['Predicted_Sales'],
            mode='lines+markers',
            name='Prévisions Futures',
            line=dict(color='#2ca02c', width=2, dash='dash')
        ))

        r2_display = max(self.metrics.get('r2', 0), 0)  # On n'affiche pas de R2 négatif moche

        fig.update_layout(
            title=f"Prévision Holt-Winters (Série Temporelle - R² ≈ {r2_display:.2f})",
            xaxis_title="Date",
            yaxis_title="Ventes (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig
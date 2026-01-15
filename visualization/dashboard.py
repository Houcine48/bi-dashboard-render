import streamlit as st
import pandas as pd
from analysis.kpi import KPICalculator
from analysis.descriptive import DescriptiveAnalyst
from analysis.forecasting import SalesForecaster
from visualization.charts import ChartBuilder
from utils.export import generate_pdf_report

class DashboardUI:
    def __init__(self, df: pd.DataFrame):
        self.raw_df = df
        self.df_filtered = df.copy()
        self.current_metrics = {}

    def _get_col_name(self, potential_names):
        """Cherche si une colonne existe sous différents noms"""
        for name in potential_names:
            if name in self.raw_df.columns: return name
        return None

    def render_sidebar_filters(self):
        """Filtres : Location & Products"""
        st.sidebar.header("🔍 Filtres Avancés")

        # --- 1. Filtre Date ---
        date_range = []
        if 'order_date' in self.raw_df.columns:
            min_d, max_d = self.raw_df['order_date'].min(), self.raw_df['order_date'].max()
            date_range = st.sidebar.date_input("Période", [min_d, max_d])

        # --- 2. Filtres LOCATION (Table Location) ---
        st.sidebar.markdown("### 🌍 Géographie")

        # On cherche les colonnes (Country, Region, State, City)
        col_country = self._get_col_name(['country', 'country/region'])
        col_region = self._get_col_name(['region'])
        col_state = self._get_col_name(['state'])
        col_city = self._get_col_name(['city'])

        sel_country = st.sidebar.multiselect("Pays", sorted(self.raw_df[col_country].unique())) if col_country else []
        sel_region = st.sidebar.multiselect("Région", sorted(self.raw_df[col_region].unique())) if col_region else []
        sel_state = st.sidebar.multiselect("État / Province",
                                           sorted(self.raw_df[col_state].unique())) if col_state else []
        sel_city = st.sidebar.multiselect("Ville", sorted(self.raw_df[col_city].unique())) if col_city else []

        # --- 3. Filtres PRODUITS (Table Products) ---
        st.sidebar.markdown("### 📦 Catalogue Produit")

        col_cat = self._get_col_name(['category'])
        col_sub = self._get_col_name(['sub-category', 'sub_category'])  # Gestion tiret vs underscore

        sel_cat = st.sidebar.multiselect("Catégorie", sorted(self.raw_df[col_cat].unique())) if col_cat else []
        sel_sub = st.sidebar.multiselect("Sous-Catégorie", sorted(self.raw_df[col_sub].unique())) if col_sub else []

        # --- APPLICATION DU FILTRAGE ---
        mask = pd.Series(True, index=self.raw_df.index)

        # Date
        if len(date_range) == 2 and 'order_date' in self.raw_df.columns:
            mask &= (self.raw_df['order_date'] >= pd.to_datetime(date_range[0])) & \
                    (self.raw_df['order_date'] <= pd.to_datetime(date_range[1]))

        # Geo
        if sel_country and col_country: mask &= self.raw_df[col_country].isin(sel_country)
        if sel_region and col_region: mask &= self.raw_df[col_region].isin(sel_region)
        if sel_state and col_state: mask &= self.raw_df[col_state].isin(sel_state)
        if sel_city and col_city: mask &= self.raw_df[col_city].isin(sel_city)

        # Produit
        if sel_cat and col_cat: mask &= self.raw_df[col_cat].isin(sel_cat)
        if sel_sub and col_sub: mask &= self.raw_df[col_sub].isin(sel_sub)

        self.df_filtered = self.raw_df[mask]

        # --- SECTION EXPORT ---
        st.sidebar.divider()
        st.sidebar.subheader("📥 Exportations")

        f_data = st.session_state.get('forecast_data', None)

        # Bouton PDF SEULEMENT
        if st.sidebar.button("📄 Télécharger Rapport PDF"):
            pdf_data = generate_pdf_report(self.df_filtered, self.current_metrics, f_data)
            st.sidebar.download_button(
                label="📥 Cliquez pour récupérer le PDF",
                data=pdf_data,
                file_name="rapport_bi.pdf",
                mime="application/pdf"
            )

    def render_overview_tab(self):
        st.subheader("📊 Performance Globale")
        kpi = KPICalculator(self.df_filtered)
        chart = ChartBuilder(self.df_filtered)
        self.current_metrics = kpi.get_global_metrics()

        if self.current_metrics:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Chiffre d'Affaires (Sales)", f"{self.current_metrics.get('total_sales', 0):,.0f} €",
                      f"{self.current_metrics.get('growth', 0):.1f}%")
            c2.metric("Profit Total", f"{self.current_metrics.get('total_profit', 0):,.0f} €",
                      f"{self.current_metrics.get('profit_margin', 0):.1f}% Marge")
            c3.metric("Quantité Vendue", f"{self.current_metrics.get('total_quantity', 0):,.0f}")
            c4.metric("Panier Moyen", f"{self.current_metrics.get('avg_basket', 0):.2f} €")

        st.divider()
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### 🏆 Top Clients")
            st.dataframe(kpi.get_top_customers(10), use_container_width=True)
        with col2:
            st.markdown("#### 📈 Évolution Mensuelle")
            st.plotly_chart(chart.plot_sales_trend(), use_container_width=True)

    def render_analysis_tab(self):
        st.subheader("🔬 Analyse Détail")
        chart = ChartBuilder(self.df_filtered)
        desc = DescriptiveAnalyst(self.df_filtered)

        c1, c2 = st.columns(2)
        with c1:
            col_cat = self._get_col_name(['category'])
            if col_cat: st.plotly_chart(chart.plot_distribution(col_cat, "Par Catégorie"), use_container_width=True)
        with c2:
            col_seg = self._get_col_name(['segment'])
            if col_seg: st.plotly_chart(chart.plot_distribution(col_seg, "Par Segment"), use_container_width=True)

        st.divider()

        # Affichage des Stats Descriptives (Profit, Quantity, Sales)
        with st.expander("📊 Statistiques Descriptives (Profit, Quantity, Sales)", expanded=True):
            st.dataframe(desc.get_summary_stats(), use_container_width=True)

    def render_forecast_tab(self):
        st.subheader("🔮 Prédictions")
        c1, c2 = st.columns([1, 3])
        with c1:
            days = st.slider("Horizon (Jours)", 7, 90, 30)
            if st.button("Calculer"):
                forecaster = SalesForecaster(self.df_filtered)
                ok, msg = forecaster.train_model()
                if ok:
                    st.success("Succès")
                    st.metric("Fiabilité (R²)", f"{forecaster.metrics['r2']:.2f}")
                    future = forecaster.predict_future(days)
                    st.session_state['f_fig'] = forecaster.plot_prediction(future)
                else:
                    st.error(msg)
        with c2:
            if 'f_fig' in st.session_state:
                st.plotly_chart(st.session_state['f_fig'], use_container_width=True)

    def show(self):
        self.render_sidebar_filters()
        t1, t2, t3 = st.tabs(["Performance", "Analyse", "Prévisions"])
        with t1: self.render_overview_tab()
        with t2: self.render_analysis_tab()
        with t3: self.render_forecast_tab()
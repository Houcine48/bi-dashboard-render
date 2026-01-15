"""
Tableau de Bord Prédictif des Ventes - Application Principale (Optimisée RAM)
"""
import streamlit as st
import sys
import os
import pandas as pd
from pathlib import Path

# --- Configuration du Path ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- Import Léger (Uniquement Auth au début) ---
# On n'importe PAS encore ingestion, cleaning ou dashboard pour économiser la RAM au démarrage
from auth.authenticator import Authenticator, require_auth

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard BI - Ventes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
    div.block-container {padding-top: 2rem;}
    </style>
""", unsafe_allow_html=True)


def initialize_session_state():
    if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
    if 'username' not in st.session_state: st.session_state['username'] = None
    if 'data_loaded' not in st.session_state: st.session_state['data_loaded'] = False
    if 'merged_data' not in st.session_state: st.session_state['merged_data'] = {}


def create_master_dataframe(data_dict):
    """Fusionne les tables"""
    if 'orders' not in data_dict: return pd.DataFrame()
    df_master = data_dict['orders'].copy()

    if 'products' in data_dict:
        products = data_dict['products']
        cols = [c for c in products.columns if c not in df_master.columns or c == 'product_id']
        if 'product_id' in df_master.columns and 'product_id' in products.columns:
            df_master = df_master.merge(products[cols], on='product_id', how='left')

    if 'location' in data_dict:
        location = data_dict['location']
        if 'postal_code' in df_master.columns and 'postal_code' in location.columns:
            cols = [c for c in location.columns if c not in df_master.columns or c == 'postal_code']
            df_master = df_master.merge(location[cols], on='postal_code', how='left')

    if 'customers' in data_dict:
        cust = data_dict['customers']
        cols = [c for c in cust.columns if c not in df_master.columns or c == 'customer_id']
        if 'customer_id' in df_master.columns and 'customer_id' in cust.columns:
            df_master = df_master.merge(cust[cols], on='customer_id', how='left')

    return df_master


def render_load_data_page():
    st.markdown('<p class="main-header">📥 Chargement & ETL (Mode Diagnostic)</p>', unsafe_allow_html=True)

    # --- DIAGNOSTIC ---
    with st.expander("🔍 État du Serveur", expanded=False):
        st.write(f"📂 Dossier : `{os.getcwd()}`")
        if os.path.exists("datasets"):
            st.success("✅ Datasets présents")
            if os.path.exists("datasets/eu"):
                st.write(f"EU: {len(os.listdir('datasets/eu'))} fichiers")
            else:
                st.error("EU introuvable")
        else:
            st.error("Datasets absents")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("Cliquez pour lancer l'ETL.")

    with col2:
        if st.button("🚀 Lancer l'ETL", type="primary"):
            with st.spinner("Traitement..."):
                try:
                    # --- IMPORTATION DIFFÉRÉE (LAZY LOADING) ---
                    # On importe les gros modules ICI seulement pour ne pas saturer la RAM au démarrage
                    from data.ingestion import DataIngestion
                    from data.cleaning import DataCleaning

                    ingestion = DataIngestion(base_path="datasets")
                    eu_data, non_eu_data = ingestion.load_all_data()

                    if not eu_data and not non_eu_data:
                        st.error("Aucune donnée trouvée.")
                        return

                    merged_data = ingestion.merge_regions(eu_data, non_eu_data)
                    cleaner = DataCleaning()
                    cleaned_data = cleaner.run_pipeline(merged_data)

                    st.session_state['merged_data'] = cleaned_data
                    st.session_state['data_loaded'] = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Erreur : {str(e)}")

    if st.session_state['data_loaded']:
        st.success("✅ Données chargées")
        summary = [{"Table": k, "Lignes": v.shape[0]} for k, v in st.session_state['merged_data'].items()]
        st.dataframe(summary, use_container_width=True)


def main():
    initialize_session_state()
    auth = Authenticator()
    require_auth(auth)

    with st.sidebar:
        st.title("BI Dashboard")
        st.write(f"👤 **{st.session_state['username']}**")
        st.divider()
        page = st.radio("Menu", ["📥 Chargement", "📊 Tableau de Bord"],
                        index=0 if not st.session_state['data_loaded'] else 1)
        if st.button("Déconnexion"): auth.logout()

    if page == "📥 Chargement":
        render_load_data_page()

    elif page == "📊 Tableau de Bord":
        if st.session_state['data_loaded'] and 'orders' in st.session_state['merged_data']:
            # --- IMPORTATION DIFFÉRÉE ---
            from visualization.dashboard import DashboardUI

            with st.spinner("Préparation..."):
                df_master = create_master_dataframe(st.session_state['merged_data'])

            dashboard = DashboardUI(df_master)
            dashboard.show()
        else:
            st.warning("Veuillez charger les données.")


if __name__ == "__main__":
    main()
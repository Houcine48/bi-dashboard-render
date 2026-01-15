"""
Tableau de Bord Prédictif des Ventes - Application Principale
"""
import streamlit as st
import sys
import pandas as pd
from pathlib import Path

# --- Configuration du Path ---
sys.path.append(str(Path(__file__).parent))

# --- Import des Modules ---
from auth.authenticator import Authenticator, require_auth
from data.ingestion import DataIngestion
from data.cleaning import DataCleaning
from visualization.dashboard import DashboardUI

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard BI - Ventes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personnalisé
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
    """
    Fusionne la table Orders avec Location, Products et Customers
    pour permettre le filtrage par Ville, Catégorie, etc.
    """
    if 'orders' not in data_dict:
        return pd.DataFrame()

    # On commence avec la table des commandes
    df_master = data_dict['orders'].copy()

    # 1. Fusion avec PRODUCTS (clé: product_id)
    if 'products' in data_dict:
        products = data_dict['products']
        # On ne garde que les colonnes utiles pour éviter les doublons
        cols_prod = [c for c in products.columns if c not in df_master.columns or c == 'product_id']
        if 'product_id' in df_master.columns and 'product_id' in products.columns:
            df_master = df_master.merge(products[cols_prod], on='product_id', how='left')

    # 2. Fusion avec LOCATION (clé: postal_code ou autre)
    if 'location' in data_dict:
        location = data_dict['location']
        # On suppose que le lien se fait par postal_code (standard Superstore)
        if 'postal_code' in df_master.columns and 'postal_code' in location.columns:
            # On retire les colonnes geo qui pourraient déjà être dans orders pour éviter les conflits
            cols_loc = [c for c in location.columns if c not in df_master.columns or c == 'postal_code']
            df_master = df_master.merge(location[cols_loc], on='postal_code', how='left')

    # 3. Fusion avec CUSTOMERS (clé: customer_id)
    if 'customers' in data_dict:
        customers = data_dict['customers']
        cols_cust = [c for c in customers.columns if c not in df_master.columns or c == 'customer_id']
        if 'customer_id' in df_master.columns and 'customer_id' in customers.columns:
            df_master = df_master.merge(customers[cols_cust], on='customer_id', how='left')

    return df_master


def render_load_data_page():
    st.markdown('<p class="main-header">📥 Chargement & ETL</p>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("Module d'ingestion et de nettoyage des données (EU/Non-EU).")

    with col2:
        if st.button("🚀 Lancer l'ETL", type="primary", use_container_width=True):
            with st.spinner("Traitement en cours..."):
                try:
                    # Ingestion
                    ingestion = DataIngestion(base_path="datasets")
                    eu_data, non_eu_data = ingestion.load_all_data()
                    merged_data = ingestion.merge_regions(eu_data, non_eu_data)

                    # Cleaning
                    cleaner = DataCleaning()
                    cleaned_data = cleaner.run_pipeline(merged_data)

                    st.session_state['merged_data'] = cleaned_data
                    st.session_state['data_loaded'] = True
                    st.success("✅ Données chargées et nettoyées !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")

    if st.session_state['data_loaded']:
        st.divider()
        st.subheader("Aperçu des tables chargées")
        st.write(f"Tables disponibles : {list(st.session_state['merged_data'].keys())}")


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
        st.divider()
        if st.button("Déconnexion"): auth.logout()

    if page == "📥 Chargement":
        render_load_data_page()

    elif page == "📊 Tableau de Bord":
        if st.session_state['data_loaded'] and 'orders' in st.session_state['merged_data']:
            # C'est ici qu'on crée la table complète pour le Dashboard
            with st.spinner("Préparation des données..."):
                df_master = create_master_dataframe(st.session_state['merged_data'])

            dashboard = DashboardUI(df_master)
            dashboard.show()
        else:
            st.warning("Veuillez d'abord charger les données.")


if __name__ == "__main__":
    main()
"""
Module d'authentification simple pour Streamlit
"""
import streamlit as st
import hashlib
import json
from pathlib import Path


class Authenticator:
    """Gestionnaire d'authentification simple avec stockage local"""
    
    def __init__(self, users_file="users.json"):
        self.users_file = Path(users_file)
        self.users = self._load_users()
    
    def _load_users(self):
        """Charge les utilisateurs depuis le fichier JSON"""
        if self.users_file.exists():
            with open(self.users_file, 'r') as f:
                return json.load(f)
        else:
            # Utilisateurs par défaut
            default_users = {
                "admin": self._hash_password("admin123"),
                "user": self._hash_password("user123")
            }
            self._save_users(default_users)
            return default_users
    
    def _save_users(self, users):
        """Sauvegarde les utilisateurs dans le fichier JSON"""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)
    
    def _hash_password(self, password):
        """Hash un mot de passe avec SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username, password):
        """Vérifie les identifiants"""
        if username in self.users:
            hashed_password = self._hash_password(password)
            return self.users[username] == hashed_password
        return False
    
    def login_form(self):
        """Affiche le formulaire de connexion Streamlit"""
        st.title("🔐 Connexion")
        st.markdown("---")
        
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter")
            
            if submit:
                if self.authenticate(username, password):
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username
                    st.success(f"✅ Bienvenue {username} !")
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects")
        
        # Info utilisateurs par défaut
        with st.expander("ℹ️ Comptes de test"):
            st.write("**Admin:** admin / admin123")
            st.write("**User:** user / user123")
    
    def logout(self):
        """Déconnexion"""
        st.session_state['authenticated'] = False
        st.session_state['username'] = None
        st.rerun()
    
    def is_authenticated(self):
        """Vérifie si l'utilisateur est connecté"""
        return st.session_state.get('authenticated', False)
    
    def get_username(self):
        """Retourne le nom d'utilisateur connecté"""
        return st.session_state.get('username', None)


# Fonction utilitaire pour protéger les pages
def require_auth(authenticator):
    """Décorateur pour protéger les pages"""
    if not authenticator.is_authenticated():
        authenticator.login_form()
        st.stop()
    else:
        # Bouton de déconnexion dans la sidebar
        with st.sidebar:
            st.write(f"👤 Connecté: **{authenticator.get_username()}**")
            if st.button("🚪 Déconnexion"):
                authenticator.logout()
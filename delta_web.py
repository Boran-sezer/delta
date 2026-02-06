import streamlit as st
from groq import Groq

# --- 1. CONFIGURATION DES CODES ---
# (Note : Ne les donnez pas à l'IA dans le prompt !)
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# --- 2. INITIALISATION DU CERVEAU (SESSION STATE) ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False

# --- 3. SÉCURITÉ MAXIMALE (MODE LOCKDOWN) ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="master_key")
    if st.button("DÉVERROUILLER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système rétabli, Monsieur Boran. Initialisation...")
            st.rerun()
        else:
            st.error("CODE MAÎTRE INCORRECT.")
    st.stop() # RIEN ne s'affiche en dessous tant que c'est bloqué

# --- 4. INTERFACE DE CHAT ---
st.title("⚡ DELTA IA")

# Affichage des messages passés
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. LOGIQUE DE VÉRIFICATION ---
if prompt := st.chat_input("Quels sont vos ordres ?"):
    # On détecte si l'action est sensible
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer"])
    
    # Demande de verrouillage manuel
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_msg = prompt # On garde l'ordre au chaud
    else:
        # Traitement normal (Groq)
        st.session_state.messages.append({"role": "user", "content": prompt})
        # ICI VOUS METTREZ VOTRE APPEL GROQ
        st.session_state.messages.append({"role": "assistant", "content": "Ordre reçu. Je traite la demande."})
        st.rerun()

# --- 6. LE FORMULAIRE DE CODE (S'affiche si besoin) ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Action protégée. Veuillez entrer le code d'action (2008...).")
        c = st.text_input("CODE :", type="password", key="action_key")
        
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.success("Accès autorisé.")
                # On peut maintenant traiter le message "pending_msg"
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                    st.rerun()
                st.error(f"CODE INCORRECT ({st.session_state.essais}/3)")

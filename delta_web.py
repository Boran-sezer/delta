import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION POUR LES CODES ---
if "code_action" not in st.session_state: st.session_state.code_action = None
if "pending_info" not in st.session_state: st.session_state.pending_info = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR & GESTION DES ARCHIVES ---
with st.sidebar:
    st.title("🧠 Archives & Sécurité")
    
    # Section Archives Publiques
    st.subheader("Archives Standard")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f"🔹 {f}")
        if col2.button("🗑️", key=f"del_pub_{i}"):
            faits_publics.pop(i)
            doc_profil.set({"faits": faits_publics, "faits_verrouilles": faits_verrouilles})
            st.rerun()

    # Section Archives Verrouillées
    st.subheader("🔐 Archives Scellées")
    if st.session_state.get("unlocked", False):
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f"🔒 {f}")
            if col2.button("🗑️", key=f"del_priv_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.set({"faits": faits_publics, "faits_verrouilles": faits_verrouilles})
                st.rerun()
        if st.button("Reverrouiller"):
            st.session_state.unlocked = False
            st.rerun()
    else:
        st.write("Contenu masqué.")

# --- LOGIQUE DES CODES DE SÉCURITÉ ---
if st.session_state.code_action:
    code_input = st.text_input("🔑 Entrez le code d'autorisation (20082008) :", type="password")
    if st.button("Confirmer l'identité"):
        if code_input == "20082008":
            if st.session_state.code_action == "reset_all":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                st.success("Réinitialisation totale accomplie, Monsieur.")
            elif st.session_state.code_action == "reset_target":
                target = st.session_state.pending_info
                faits_publics = [f for f in faits_publics if target.lower() not in f.lower()]
                faits_verrouilles = [f for f in faits_verrouilles if target.lower() not in f.lower()]
                doc_profil.set({"faits": faits_publics, "faits_verrouilles": faits_verrouilles})
                st.success(f"Cibles '{target}' éliminées des archives.")
            elif st.session_state.code_action == "lock_info":
                faits_verrouilles.append(st.session_state.pending_info)
                doc_profil.set({"faits": faits_publics, "faits_verrouilles": faits_verrouilles})
                st.success("Information scellée dans les archives verrouillées.")
            elif st.session_state.code_action == "view_locked":
                st.session_state.unlocked = True
            
            st.session_state.code_action = None
            st.session_state.pending_info = None
            st.rerun()
        else:
            st.error("Code incorrect. Accès refusé.")

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- ANALYSE DES ORDRES ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    # Détection des commandes spéciales
    low_p = p.lower()
    if "réinitialisation complète" in low_p:
        st.session_state.code_action = "reset_all"
        response = "Demande reçue. Procédure de réinitialisation totale en attente du code de sécurité."
    elif "supprime précisément" in low_p:
        st.session_state.code_action = "reset_target"
        st.session_state.pending_info = p.replace("supprime précisément", "").strip()
        response = f"Tentative de suppression de '{st.session_state.pending_info}'. Code requis."
    elif "verrouille" in low_p:
        st.session_state.code_action = "lock_info"
        st.session_state.pending_info = p.replace("verrouille", "").strip()
        response = "Mémorisation sécurisée demandée. Veuillez entrer le code d'accès."
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.code_action = "view_locked"
        response = "Accès aux archives scellées demandé. Authentification nécessaire."
    else:
        # Réponse standard de DELTA
        with st.chat_message("assistant"):
            contexte = f"Infos publiques : {', '.join(faits_publics)}. Infos verrouillées : {', '.join(faits_verrouilles)}"
            instructions = {"role": "system", "content": f"Tu es DELTA, créé par Monsieur Boran. {contexte}. Majordome fidèle."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instructions] + st.session_state.messages)
            response = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

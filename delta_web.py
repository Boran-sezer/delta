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
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LECTURE DE L'ENTRÉE (AVANT TOUT LE RESTE) ---
# On récupère l'entrée pour vérifier l'ordre de réinitialisation AVANT d'afficher les archives
if p := st.chat_input("Ordres, Monsieur ?"):
    if p.lower().strip() == "réinitialisation complète":
        # 1. Purge RÉELLE dans Firebase
        doc_ref.set({"faits": [], "faits_verrouilles": []})
        # 2. Vide l'historique de discussion
        st.session_state.messages = []
        # 3. RELANCE TOUT pour vider l'affichage
        st.rerun()
    else:
        st.session_state.temp_prompt = p

# --- CHARGEMENT MÉMOIRE (APRÈS VÉRIFICATION DE PURGE) ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- SIDEBAR (ARCHIVES) ---
with st.sidebar:
    st.title("🧠 Archives")
    if not faits:
        st.write("Archives vides.")
    for f in faits:
        st.info(f)

# --- CHAT ---
st.title("⚡ DELTA OS")
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- TRAITEMENT DU MESSAGE SI PAS DE PURGE ---
if "temp_prompt" in st.session_state:
    prompt = st.session_state.temp_prompt
    del st.session_state.temp_prompt
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # APPEL IA
    client = Groq(api_key="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")
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Voici les faits actuels : {faits}"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

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
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "locked" not in st.session_state: st.session_state.locked = False

# --- 🔒 MODE VERROUILLAGE (BLOCAGE TOTAL) ---
if st.session_state.locked:
    st.markdown("# 🔒 SYSTÈME SÉCURISÉ")
    st.write("DELTA est en mode veille sécurisée.")
    
    code_input = st.text_input("Code d'accès :", type="password", key="lock_input")
    
    if st.button("DÉVERROUILLER"):
        if code_input == "20082008":
            st.session_state.locked = False
            st.success("Accès rétabli.")
            st.rerun()
        else:
            st.error("Code erroné.")
    st.stop() 

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- SIDEBAR (GESTION MANUELLE) ---
with st.sidebar:
    st.title("🧠 Archives")
    if not faits:
        st.write("Mémoire vide.")
    
    # Option pour supprimer manuellement
    for i, fait in enumerate(faits):
        col1, col2 = st.columns([4, 1])
        col1.info(fait)
        if col2.button("🗑️", key=f"del_{i}"):
            # On retire l'élément de la liste
            faits.pop(i)
            # On met à jour Firebase
            doc_ref.update({"faits": faits})
            # On relance pour mettre à jour l'affichage
            st.rerun()

# --- INTERFACE DE CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    low_p = p.lower().strip()
    
    # Détection Verrouillage
    if "verrouille-toi" in low_p:
        st.session_state.locked = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    # Réponse IA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Voici tes archives : {faits}. Sois bref et utilise des émojis."
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

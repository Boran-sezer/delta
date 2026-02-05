import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "locked" not in st.session_state: st.session_state.locked = False

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

# --- 🔒 LOGIQUE DE VERROUILLAGE ---
if st.session_state.locked:
    st.markdown("### 🔒 SYSTÈME VERROUILLÉ")
    code_input = st.text_input("Entrez le code d'accès pour déverrouiller DELTA :", type="password")
    
    if st.button("Déverrouiller"):
        if code_input == "20082008":
            st.session_state.locked = False
            st.success("✅ Accès accordé. Redémarrage...")
            st.rerun()
        else:
            st.error("❌ Code incorrect. Accès refusé.")
    st.stop() # Arrête l'affichage du reste de la page

# --- CHARGEMENT DONNÉES ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for f in faits:
        st.info(f)

# --- CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    low_p = p.lower().strip()
    
    # DÉTECTION DE L'ORDRE DE VERROUILLAGE
    if "verrouille-toi" in low_p:
        st.session_state.locked = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    # RÉPONSE IA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA, majordome de Monsieur Boran. Archives : {faits}"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

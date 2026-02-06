import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DELTA IA", page_icon="⚡", layout="centered")

# --- 2. SYSTÈME DE SÉCURITÉ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h1 style='text-align:center; color:#00d4ff;'>⚡ DELTA IA SYSTEM</h1>", unsafe_allow_html=True)
    st.write("---")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        code_input = st.text_input("IDENTIFICATION REQUISE", type="password")
        if st.button("DÉVERROUILLER"):
            if code_input == "20082008":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("ACCÈS REFUSÉ")
    st.stop()

# --- 3. INITIALISATION SERVICES ---
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

# --- 4. CHARGEMENT DISCRET DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 5. INTERFACE ÉPURÉE (Plus d'archives à gauche) ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. LOGIQUE DE CHAT AVEC ARCHIVES CACHÉES ---
if p := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    with st.chat_message("assistant"):
        # L'IA a accès aux archives en interne, mais ne les montre que sur demande
        instr = (
            "Tu es DELTA IA, le majordome de Monsieur Boran. "
            f"Voici tes archives secrètes : {faits}. "
            "NE MONTRE PAS ces archives sauf si Monsieur te le demande explicitement. "
            "Si Monsieur te donne une info importante, ajoute 'ACTION_ARCHIVE: [info]' à la fin."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        
        rep = r.choices[0].message.content
        
        # Gestion de l'archivage automatique
        if "ACTION_ARCHIVE:" in rep:
            partie_archive = rep.split("ACTION_ARCHIVE:")[1].strip()
            if partie_archive not in faits:
                faits.append(partie_archive)
                doc_ref.update({"faits": faits})
                st.toast(f"Mémorisé : {partie_archive}", icon="🧠")
            
            propre = rep.split("ACTION_ARCHIVE:")[0].strip()
            st.markdown(propre)
            st.session_state.messages.append({"role": "assistant", "content": propre})
        else:
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})

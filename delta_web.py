import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONNEXION FIREBASE ---
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

# --- 2. GESTION DU VERROUILLAGE (FORCE) ---
if "locked" not in st.session_state:
    st.session_state.locked = False

# Fonction de déverrouillage
def verify_unlock():
    if st.session_state.pwd_field == "B2008a2020@":
        st.session_state.locked = False
        st.success("Accès rétabli.")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error("Code incorrect.")

# Si le système est verrouillé, on bloque TOUT l'affichage ici
if st.session_state.locked:
    st.markdown("<h2 style='color:#ff4b4b;text-align:center;'>🔒 SYSTÈME DELTA VERROUILLÉ</h2>", unsafe_allow_html=True)
    st.text_input("Code de sécurité requis", type="password", key="pwd_field", on_change=verify_unlock)
    st.stop() # Arrête l'exécution du reste du code

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
col1, col2 = st.columns([0.9, 0.1])
with col1:
    st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)
with col2:
    if st.button("🔒 Lock"):
        st.session_state.locked = True
        st.rerun()

# Récupération des données
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE CHAT ET COMMANDES ---
if prompt := st.chat_input("Message pour DELTA..."):
    # Commande textuelle de verrouillage
    if any(x in prompt.lower() for x in ["verrouille", "lock", "verrouillage"]):
        st.session_state.locked = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse d'archivage
    sys_analyse = f"Archives : {archives}. JSON : {{'action':'add', 'cat':'NOM', 'val':'INFO'}} ou {{'action':'none'}}"
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match and "add" in match.group(0):
            data = json.loads(match.group(0).replace("'", '"'))
            c, v = data.get('cat', 'Mémoire'), data.get('val')
            if v and v not in archives.get(c, []):
                if c not in archives: archives[c] = []
                archives[c].append(v)
                doc_ref.set({"archives": archives})
                st.toast("💾")
    except: pass

    # Réponse de DELTA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Créateur : Monsieur Sezer Boran. Mémoire : {archives}. Sois bref."
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                temperature=0.3
            )
            final = resp.choices[0].message.content
        except:
            final = "Système opérationnel, Monsieur Sezer."
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})

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

# --- 2. RÉCUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Commandes, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Commande pour voir les archives proprement
    if "archive" in prompt.lower():
        with st.chat_message("assistant"):
            st.markdown("### 🗄️ CENTRE DE DONNÉES")
            if not archives:
                st.info("Aucune donnée enregistrée pour le moment.")
            for section, items in archives.items():
                with st.expander(f"📁 SECTION : {section.upper()}"):
                    for i, item in enumerate(items):
                        st.write(f"{i+1}. {item}")
        st.session_state.messages.append({"role": "assistant", "content": "[Archives consultées]"})
        st.stop()

    # --- ARCHIVAGE INTELLIGENT ---
    # On demande à Llama de classer l'info proprement
    sys_analyse = (
        f"Tu es l'archiviste de Monsieur Sezer. Voici les archives actuelles : {archives}. "
        f"Il vient de dire : '{prompt}'. "
        "Si ce message contient un fait, une préférence ou une instruction nouvelle, "
        "réponds UNIQUEMENT en JSON : {'action':'add', 'cat':'NOM_SECTION', 'val':'INFO'}. "
        "Choisis un nom de catégorie clair (ex: Identité, Projets, Goûts). "
        "Sinon réponds {'action':'none'}."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste logique et structuré."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            if data.get('action') == 'add':
                c, v = data.get('cat', 'Général'), data.get('val')
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    doc_ref.set({"archives": archives})
                    st.toast(f"💾 Enregistré dans {c}")
    except: pass

    # --- RÉPONSE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à ton Créateur, Monsieur Sezer Boran. "
            f"Voici tes archives : {archives}. "
            "Utilise ces informations pour être ultra-personnalisé. "
            "Sois concis, technique et efficace."
        )
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except:
            placeholder.markdown("Erreur de liaison.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})

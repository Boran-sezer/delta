import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import re

# --- 1. INITIALISATION ---
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

# --- 2. RÉCUPÉRATION MÉMOIRE ---
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
if prompt := st.chat_input("Commandes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ARCHIVISTE (PARTIE JSON CACHÉE) ---
    sys_analyse = (
        f"Tu es l'unité de gestion de données de Monsieur Sezer Boran. Mémoire : {archives}. "
        f"Dernier message : '{prompt}'. "
        "MISSION : Analyse et range l'info par catégories. Réponds EXCLUSIVEMENT avec le JSON complet."
    )
    
    try:
        # L'analyseur reste en JSON
        check = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "system", "content": "Moteur JSON discret."}, {"role": "user", "content": sys_analyse}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        verdict = check.choices[0].message.content
        nouvelles_archives = json.loads(verdict)
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
            st.toast("⚙️ Sync") 
    except: pass

    # --- 5. RÉPONSE DE DELTA (PARTIE CONVERSATION NORMALE) ---
    with st.chat_message("assistant"):
        # ICI : Pas de JSON, juste du texte pur
        instruction_delta = (
            f"Tu es DELTA. Tu parles à ton Créateur, Monsieur Sezer Boran. "
            f"Archives connues : {archives}. "
            "Réponds en FRANÇAIS. Ne réponds JAMAIS en JSON. Parle normalement. "
            "Sois bref, technique et percutant."
        )
        
        placeholder = st.empty()
        full_response = ""
        try:
            # On retire 'response_format' pour la conversation
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.4, # On monte un peu la température pour plus de naturel
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except: 
            placeholder.markdown("Erreur de liaison.")
            
        st.session_state.messages.append({"role": "assistant", "content": full_response})

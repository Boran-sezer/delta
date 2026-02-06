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

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. ANALYSE ET ARCHIVAGE AUTOMATIQUE ---
if prompt := st.chat_input("Message pour DELTA..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # L'unité d'analyse décide si l'info doit être mémorisée
    sys_analyse = (
        f"Tu es l'unité de mémoire de DELTA. Voici les archives : {archives}. "
        f"Monsieur Sezer Boran dit : '{prompt}'. "
        "Si ce message contient une info importante (préférence, nom, projet, fait), "
        "réponds UNIQUEMENT en JSON : {'action':'add', 'cat':'NOM_CATEGORIE', 'val':'INFO'}. "
        "Sinon réponds {'action':'none'}."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste autonome et intelligent."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        
        # Extraction du JSON
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            if data.get('action') == 'add':
                c, v = data.get('cat', 'Général'), data.get('val')
                # On ajoute seulement si c'est nouveau
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    # Mise à jour Firebase immédiate
                    doc_ref.set({"archives": archives})
                    st.toast(f"💾 Mémoire mise à jour : {c}")
                    time.sleep(0.1)
    except Exception as e:
        pass # Erreur silencieuse pour ne pas perturber l'utilisateur

    # --- 5. RÉPONSE AVEC EFFET DE FRAPPE (STREAMING) ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Créateur : Monsieur Sezer Boran. "
            f"Utilise ces archives si besoin : {archives}. "
            "Sois extrêmement concis et efficace. Pas de phrases automatiques."
        )
        
        placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception:
            # Secours sans "Système opérationnel"
            try:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant", 
                    messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages
                )
                full_response = resp.choices[0].message.content
                placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except:
                st.error("Lien perdu avec le noyau.")

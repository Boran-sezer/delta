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

# --- 2. RECUPÉRATION ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : Filtrage Intelligent</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Mémoire de Monsieur Sezer")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Aucune donnée pertinente mémorisée.")

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. ANALYSE ET FILTRAGE INTELLIGENT ---
if prompt := st.chat_input("Dites quelque chose à DELTA..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Instruction de filtrage strict
    sys_analyse = (
        f"Archives actuelles : {archives}. "
        f"Message de Monsieur Sezer : '{prompt}'. "
        "Tu es le filtre de mémoire de DELTA. Ton rôle est de ne garder QUE le crucial. "
        "1. IGNORE le bavardage, les politesses, les questions simples ou les phrases sans valeur informative. "
        "2. ARCHIVE uniquement les faits nouveaux, préférences, noms, projets ou décisions. "
        "3. Réponds UNIQUEMENT en JSON : "
        "{'action':'add', 'cat':'NOM_LOGIQUE', 'val':'texte_court'} "
        "Sinon réponds {'action':'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un archiviste minimaliste et intelligent."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            act = data.get('action')
            
            if act == 'add':
                c, v = data.get('cat', 'Divers'), data.get('val')
                # On ne sauvegarde que si l'info n'existe pas déjà
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    doc_ref.set({"archives": archives})
                    st.toast(f"💾 Info pertinente archivée : {c}")
                    time.sleep(0.4)
                    st.rerun()
    except: pass

    # --- 5. RÉPONSE ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA, créé par Monsieur Sezer. "
            f"Archives : {archives}. "
            "Réponds avec intelligence et respect à ton Créateur. Sois concis."
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        except:
            resp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages)
            final = resp.choices[0].message.content
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})

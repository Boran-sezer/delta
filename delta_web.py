import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONFIGURATION ---
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

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt. Prêt à restructurer vos données, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Aucune archive.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE MODIFICATION AVANCÉE ---
if prompt := st.chat_input("Modifiez vos archives ici..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ANALYSE DE L'ACTION DE MISE À JOUR
    analyse_prompt = (
        f"Archives : {archives}. "
        f"Ordre : '{prompt}'. "
        "Si l'utilisateur veut MODIFIER une info existante, réponds UNIQUEMENT ce JSON : "
        "{'action': 'update_info', 'partie': 'nom_de_la_partie', 'old_info': 'texte_exact_a_remplacer', 'new_info': 'nouveau_texte'}. "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        cmd_text = check.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', cmd_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'update_info':
                partie = data.get('partie')
                old = data.get('old_info')
                new = data.get('new_info')
                
                if partie in archives and old in archives[partie]:
                    idx = archives[partie].index(old)
                    archives[partie][idx] = new
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"✅ Information mise à jour.")
                time.sleep(0.5)
                st.rerun()
    except: pass

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives : {archives}. Ne dis jamais accès autorisé."

        try:
            stream = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages, stream=True)
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_raw += content
                    placeholder.markdown(full_raw + "▌")
        except:
            full_raw = "Mise à jour effectuée dans vos archives, Monsieur Sezer. ⚡"
        
        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})

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
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt. À vos ordres, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

# Affichage des archives en temps réel dans le menu de gauche
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
        st.info("Aucune archive détectée.")

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres en attente..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. ANALYSE ET MODIFICATION FORCEE
    analyse_prompt = (
        "Tu es un processeur de données. Analyse l'ordre suivant et réponds UNIQUEMENT en JSON. "
        f"Archives actuelles : {archives}. "
        f"Ordre : '{prompt}'. "
        "Actions possibles : 'add' (ajouter), 'rename_partie' (renommer), 'delete_partie' (supprimer), 'move_info' (déplacer). "
        "Si l'ordre demande une de ces actions, réponds : {'action': '...', 'partie': '...', 'info': '...', 'from': '...', 'to': '...'}. "
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

            if action == 'add':
                p = data.get('partie', 'Général')
                if p not in archives: archives[p] = []
                archives[p].append(data.get('info'))
                modif = True
            elif action == 'rename_partie':
                src, target = data.get('from'), data.get('to')
                if src in archives:
                    archives[target] = archives.pop(src)
                    modif = True
            elif action == 'delete_partie':
                src = data.get('from')
                if src in archives:
                    del archives[src]
                    modif = True
            
            if modif:
                doc_ref.set({"archives": archives})
                st.toast("✅ Base de données mise à jour.")
                time.sleep(0.5)
                st.rerun() # On relance pour mettre à jour la sidebar
    except: pass

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives : {archives}. Utilise 'Monsieur Sezer'. Sois bref et loyal."

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_raw += content
                    placeholder.markdown(full_raw + "▌")
        except:
            # Sécurité Rate Limit
            res_back = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            full_raw = res_back.choices[0].message.content

        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})

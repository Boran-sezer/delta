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

# --- 2. RÉCUPÉRATION ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Archives vides.")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA paré, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT DES ORDRES ---
if prompt := st.chat_input("Votre message ou ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse simplifiée
    analyse_instr = (
        f"Archives : {list(archives.keys())}. "
        f"Ordre : '{prompt}'. "
        "Réponds UNIQUEMENT en JSON : "
        "{'action': 'add', 'cat': 'nom', 'info': 'texte'} pour ajouter/sauver, "
        "{'action': 'rename', 'old': 'nom', 'new': 'nom'} pour renommer, "
        "sinon {'action': 'none'}."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un extracteur JSON pur."}, {"role": "user", "content": analyse_instr}],
            temperature=0
        )
        # Extraction robuste du JSON
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'add':
                c, i = data.get('cat', 'Général'), data.get('info')
                if i:
                    if c not in archives: archives[c] = []
                    archives[c].append(i)
                    modif = True
            elif action == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast("✅ Base mise à jour")
                time.sleep(0.5)
                st.rerun()
    except:
        pass

    # B. RÉPONSE DE DELTA AVEC SA MÉMOIRE
    with st.chat_message("assistant"):
        # On liste toutes les archives pour l'IA
        memoire_texte = ""
        for c, v in archives.items():
            memoire_texte += f"Dossier {c} : {', '.join(v)}. "

        instruction_finale = (
            f"Tu es DELTA. Voici tes archives sur Monsieur Sezer : {memoire_texte}. "
            "Utilise ces infos pour répondre. Sois bref et n'utilise pas 'accès autorisé'."
        )
        
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_finale}] + st.session_state.messages
            )
            txt = resp.choices[0].message.content
        except:
            txt = "Mise à jour effectuée, Monsieur Sezer. ⚡"
        
        st.markdown(txt)
        st.session_state.messages.append({"role": "assistant", "content": txt})

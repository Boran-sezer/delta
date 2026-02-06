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

# --- 2. RÉCUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : Archivage Autonome</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives Intelligentes")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Aucune archive pour le moment.")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Je surveille désormais vos informations importantes pour les archiver tout seul, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LE CERVEAU AUTONOME (AUTO-ARCHIVE) ---
if prompt := st.chat_input("Dites n'importe quoi..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # L'IA analyse si une information mérite d'être archivée sans qu'on lui demande
    analyse_auto = (
        f"Archives actuelles : {list(archives.keys())}. "
        f"Dernier message de Monsieur Sezer : '{prompt}'. "
        "Tu es la mémoire de DELTA. Analyse si ce message contient une info importante à conserver. "
        "Si oui, réponds UNIQUEMENT en JSON : "
        "{'action': 'save', 'cat': 'nom_du_dossier', 'info': 'contenu_à_sauver'} "
        "Si l'utilisateur demande explicitement de renommer : {'action': 'rename', 'old': 'ancien', 'new': 'nouveau'} "
        "Si rien d'important : réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un gestionnaire de mémoire autonome."}, {"role": "user", "content": analyse_auto}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(1).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'save':
                cat = data.get('cat', 'Divers')
                if cat not in archives: archives[cat] = []
                # On évite les doublons
                if data.get('info') not in archives[cat]:
                    archives[cat].append(data.get('info'))
                    modif = True
            
            elif action == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"💾 Archivé dans {data.get('cat', 'Archives')}")
                time.sleep(0.3)
                st.rerun()
    except: pass

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Tu archives automatiquement les infos importantes de Monsieur Sezer. Archives : {archives}. Sois bref."
        try:
            resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages)
            full_raw = resp.choices[0].message.content
        except:
            full_raw = "Compris, Monsieur Sezer. ⚡"
        
        st.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})

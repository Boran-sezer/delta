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
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : Intelligence Sélective</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos: st.write(f"• {i}")
    else:
        st.info("Aucune archive.")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Je suis paré, Monsieur Sezer. Je serai plus sélectif sur l'archivage désormais. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE D'ARCHIVAGE INTELLIGENTE ---
if prompt := st.chat_input("Votre message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Le filtre strict : on demande à l'IA d'être critique
    analyse_auto = (
        f"Dossiers existants : {list(archives.keys())}. "
        f"Message : '{prompt}'. "
        "Tu es un filtre de données. ARCHIVE UNIQUEMENT SI c'est une info factuelle (nom, projet, date, préférence). "
        "Ignore les 'bonjour', les questions, ou le bavardage. "
        "Si pertinent, réponds en JSON : {'action': 'save', 'cat': 'nom_logique', 'info': 'texte_court'}. "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un archiviste minimaliste."}, {"role": "user", "content": analyse_auto}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(1).replace("'", '"'))
            if data.get('action') == 'save':
                cat = data.get('cat', 'Divers')
                # On évite de dupliquer si l'info existe déjà
                if data.get('info') not in archives.get(cat, []):
                    if cat not in archives: archives[cat] = []
                    archives[cat].append(data.get('info'))
                    doc_ref.set({"archives": archives})
                    st.toast(f"💾 Noté dans {cat}")
                    time.sleep(0.2)
                    st.rerun()
    except: pass

    # B. RÉPONSE AVEC MÉMOIRE
    with st.chat_message("assistant"):
        mem_str = "\n".join([f"- {c}: {', '.join(v)}" for c, v in archives.items()])
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Voici tes archives : {mem_str}. Utilise-les pour répondre. Sois bref."
        
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
        except:
            full_res = "Je reste à votre écoute, Monsieur Sezer. ⚡"
        
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})

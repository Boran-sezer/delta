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
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : Archivage Autonome</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Mémoire de Monsieur Sezer")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Aucune donnée mémorisée.")

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. ANALYSE ET ACTION AUTOMATIQUE ---
if prompt := st.chat_input("Dites n'importe quoi..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # L'IA décide SEULE de l'action à mener
    sys_analyse = (
        f"Archives actuelles : {archives}. "
        f"Message de Monsieur Sezer : '{prompt}'. "
        "Tu es le cerveau de DELTA. Analyse si ce message contient une info à mémoriser ou une demande de modification. "
        "Réponds UNIQUEMENT en JSON : "
        "{'action':'add', 'cat':'nom_dossier', 'val':'info'} (si info importante) "
        "{'action':'delete', 'cat':'nom_dossier', 'val':'info'} (si l'info est annulée/fausse) "
        "{'action':'rename', 'old':'nom', 'new':'nom'} (si on veut changer un nom) "
        "Sinon {'action':'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un archiviste autonome sélectif."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            act = data.get('action')
            modif = False

            if act == 'add':
                c, v = data.get('cat', 'Divers'), data.get('val')
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    modif = True
            elif act == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    modif = True
            elif act == 'delete':
                c, v = data.get('cat'), data.get('val')
                if c in archives and v in archives[c]:
                    archives[c].remove(v)
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"💾 Mise à jour auto : {act}")
                time.sleep(0.4)
                st.rerun()
    except: pass

    # --- 5. RÉPONSE DE DELTA (AVEC MÉMOIRE ET ANTI-CRASH) ---
    with st.chat_message("assistant"):
        context = f"Tu es DELTA. Voici tes archives : {archives}. Utilise-les pour répondre à Monsieur Sezer. Sois bref."
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": context}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        except:
            # Secours si Rate Limit
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[{"role": "system", "content": context}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})

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

# --- 2. RÉCUPÉRATION DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    for k, v in archives.items():
        with st.expander(f"📁 {k}"):
            for item in v: st.write(f"• {item}")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LE MOTEUR DE TRAITEMENT (SIMPLIFIÉ AU MAXIMUM) ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse ultra-courte pour éviter les erreurs de l'IA
    sys_prompt = (
        "Réponds UNIQUEMENT en JSON. "
        "Si AJOUTER info: {'action':'add', 'cat':'nom_cat', 'val':'texte'}. "
        "Si RENOMMER catégorie: {'action':'rename', 'old':'nom', 'new':'nom'}. "
        "Si SUPPRIMER catégorie: {'action':'del', 'cat':'nom'}. "
        "Sinon: 'NON'."
    )
    
    try:
        # On utilise le modèle 8b pour la rapidité et la précision JSON
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0
        )
        raw_json = check.choices[0].message.content.strip()
        
        # Nettoyage automatique du JSON
        match = re.search(r'\{.*\}', raw_json, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            action = data.get('action')
            done = False

            if action == 'add':
                cat = data.get('cat', 'Général')
                if cat not in archives: archives[cat] = []
                archives[cat].append(data.get('val', ''))
                done = True
            
            elif action == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    done = True
            
            elif action == 'del':
                c = data.get('cat')
                if c in archives:
                    del archives[c]
                    done = True

            if done:
                doc_ref.set({"archives": archives})
                st.toast("✅ Base mise à jour")
                time.sleep(0.5)
                st.rerun()
    except: pass

    # RÉPONSE FINALE
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives: {archives}. Sois bref."
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        final_txt = resp.choices[0].message.content
        st.markdown(final_txt)
        st.session_state.messages.append({"role": "assistant", "content": final_txt})

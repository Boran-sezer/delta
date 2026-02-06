import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

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

# --- 2. ÉTATS ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA prêt. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "ask_auth" not in st.session_state: st.session_state.ask_auth = False

# --- 3. MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password", key="master") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. FONCTION DE RÉPONSE ---
def reponse_delta(prompt, special_instr=None):
    # Instructions renforcées pour la suppression
    instr = special_instr if special_instr else (
        f"Tu es DELTA, majordome de Monsieur SEZER. Ultra-concis. "
        f"Archives : {faits}. "
        "Si Monsieur demande de supprimer/enlever une info, tu DOIS répondre EXACTEMENT : ACTION_DELETE: [élément à supprimer]."
        "Sinon, si tu apprends une info : ACTION_ARCHIVE: [info]."
    )
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "ACTION_" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)
        
        clean = full_raw.split("ACTION_")[0].strip()
        placeholder.markdown(clean)
        
        # LOGIQUE DE SUPPRESSION AMÉLIORÉE
        if "ACTION_DELETE:" in full_raw:
            cible = full_raw.split("ACTION_DELETE:")[1].strip().lower()
            # On filtre la liste : on garde tout ce qui ne contient pas le mot clé
            nouveaux_faits = [f for f in faits if cible not in f.lower()]
            if len(nouveaux_faits) < len(faits):
                doc_ref.set({"faits": nouveaux_faits}, merge=True)
                st.toast("Mémoire nettoyée, Monsieur SEZER.")
                time.sleep(1)
                st.rerun()

        # LOGIQUE D'ARCHIVAGE
        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
                st.toast("Info mémorisée.")

        st.session_state.messages.append({"role": "assistant", "content": clean})

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# SÉCURITÉ UNIFIÉE (Archives OU Mémoire)
if st.session_state.ask_auth:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise pour la mémoire.")
        pwd = st.text_input("CODE :", type="password", key="pwd_input")
        if st.button("CONFIRMER"):
            if pwd == CODE_ACT:
                st.session_state.ask_auth = False
                reponse_delta("Montre la mémoire", f"Liste les archives : {faits}")
                st.rerun()
            else:
                st.error("Code erroné.")
    st.stop()

if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    p_low = prompt.lower()
    
    # 1. Verrouillage
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()
    
    # 2. Sécurité Unifiée : Bloque si "archive" OU "mémoire" est présent
    elif any(w in p_low for w in ["archive", "mémoire", "souviens"]):
        st.session_state.ask_auth = True
        st.rerun()
    
    # 3. Réponse normale (inclut la suppression)
    else:
        reponse_delta(prompt)
        st.rerun()

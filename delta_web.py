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
if "pending_auth" not in st.session_state: st.session_state.pending_auth = False

# --- 3. MÉMOIRE ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- 4. LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password", key="m_lock") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 6. GESTION DES INPUTS ---
if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    p_low = prompt.lower()
    
    # Verrouillage manuel toujours possible
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Consigne : DELTA doit demander le code s'il touche aux archives
        instr = (
            f"Tu es DELTA, majordome de Monsieur SEZER. Ultra-concis. "
            f"Archives : {faits}. "
            "IMPORTANT : Si Monsieur te demande une information qui se trouve dans tes archives "
            "ou s'il veut voir sa mémoire, tu DOIS répondre EXACTEMENT : REQUIS_CODE. "
            "Sinon, réponds normalement."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "REQUIS_CODE" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        # Si l'IA a décidé de demander le code
        if "REQUIS_CODE" in full_raw:
            st.session_state.pending_auth = True
            st.rerun()
        else:
            placeholder.markdown(full_raw)
            st.session_state.messages.append({"role": "assistant", "content": full_raw})
            st.rerun()

# --- 7. ÉCRAN D'AUTHENTIFICATION DÉCLENCHÉ PAR DELTA ---
if st.session_state.pending_auth:
    with st.chat_message("assistant"):
        st.warning("🔒 DELTA : Cette information nécessite une clé d'accès.")
        c = st.text_input("Code de sécurité :", type="password", key="delta_auth")
        if st.button("DÉVERROUILLER"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                # DELTA affiche alors les infos
                info_txt = "Accès autorisé. Voici les notes archivées : \n\n" + "\n".join([f"- {i}" for i in faits])
                st.session_state.messages.append({"role": "assistant", "content": info_txt})
                st.rerun()
            else:
                st.error("Code incorrect.")

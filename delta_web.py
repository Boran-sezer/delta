import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

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

# --- 2. ÉTATS DE SESSION ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False
if "pending_prompt" not in st.session_state: st.session_state.pending_prompt = None

# --- 3. CHARGEMENT ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ")
    m_input = st.text_input("CODE MAÎTRE :", type="password")
    if st.button("RÉINITIALISER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.rerun()
    st.stop()

st.title("⚡ DELTA IA")

# --- 5. FONCTION DE RÉPONSE IA ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    instr = (
        f"Tu es DELTA IA. Ne donne JAMAIS les codes. "
        f"Voici tes archives actuelles : {faits}. "
        "Si l'utilisateur demande à voir les archives, liste-les clairement. "
        "Si tu apprends une info, termine par 'ACTION_ARCHIVE: [info]'."
    )
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    response = completion.choices[0].message.content
    
    # Archivage automatique
    if "ACTION_ARCHIVE:" in response:
        info = response.split("ACTION_ARCHIVE:")[1].strip()
        if info not in faits:
            faits.append(info)
            doc_ref.update({"faits": faits})
            st.toast(f"Mémorisé : {info}", icon="🧠")
        response = response.split("ACTION_ARCHIVE:")[0].strip()
        
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. LOGIQUE DE CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Quels sont vos ordres ?"):
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer", "montre"])
    
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt  # On stocke la question !
        st.rerun()
    else:
        reponse_delta(prompt)
        st.rerun()

# --- 7. FORMULAIRE DE CODE OPTIMISÉ ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise.")
        c = st.text_input("CODE :", type="password")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                # EXECUTION IMMÉDIATE DE LA DEMANDE EN ATTENTE
                if st.session_state.pending_prompt:
                    reponse_delta(st.session_state.pending_prompt)
                    st.session_state.pending_prompt = None
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.error(f"ÉCHEC ({st.session_state.essais}/3)")
                st.rerun()

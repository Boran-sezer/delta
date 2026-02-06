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
if "messages" not in st.session_state: st.session_state.messages = []
if "auth" not in st.session_state: st.session_state.auth = False
if "locked" not in st.session_state: st.session_state.locked = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False

# --- 3. CHARGEMENT DE LA MÉMOIRE ET RECONNAISSANCE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# Initialisation du message de bienvenue (Reconnaissance automatique)
if not st.session_state.messages:
    salutation = "Bonjour Monsieur Boran. Système DELTA prêt et opérationnel. ⚡"
    if faits:
        # L'IA analyse les archives pour personnaliser l'accueil
        instr_welcome = f"Tu es DELTA. Salue Monsieur Boran brièvement en montrant que tu te souviens de lui grâce à ces archives : {faits}."
        try:
            welcome_res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr_welcome}]
            )
            salutation = welcome_res.choices[0].message.content
        except: pass
    st.session_state.messages.append({"role": "assistant", "content": salutation})

# --- 4. SÉCURITÉ LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ")
    m_input = st.text_input("CODE MAÎTRE :", type="password")
    if st.button("DÉVERROUILLER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.rerun()
    st.stop()

# --- 5. FONCTION RÉPONSE ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    instr = (
        f"Tu es DELTA IA, majordome de Monsieur Boran. Tu es sa création. "
        f"Archives : {faits}. "
        "Si tu apprends une info, termine par 'ACTION_ARCHIVE: [info]'. 🤖"
    )
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    response = completion.choices[0].message.content
    if "ACTION_ARCHIVE:" in response:
        info = response.split("ACTION_ARCHIVE:")[1].strip()
        if info not in faits:
            faits.append(info)
            doc_ref.set({"faits": faits}, merge=True)
            st.success(f"Sauvegardé : {info}")
            st.balloons()
        response = response.split("ACTION_ARCHIVE:")[0].strip()
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Vos ordres ?"):
    p_low = prompt.lower()
    sensible = any(w in p_low for w in ["archive", "mémoire", "montre", "souviens"])
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()
    else:
        reponse_delta(prompt)
        st.session_state.auth = False
        st.rerun()

# --- 7. AUTH ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        c = st.text_input("Code :", type="password")
        if st.button("Valider"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                if st.session_state.get("pending_prompt"):
                    reponse_delta(st.session_state.pending_prompt)
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()

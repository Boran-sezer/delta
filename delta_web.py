import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DES ACCÈS ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# Initialisation Firebase (via Secrets Streamlit)
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur de connexion Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. GESTION DES ÉTATS (SESSION STATE) ---
states = {
    "locked": False, 
    "auth": False, 
    "essais": 0, 
    "messages": [], 
    "show_auth_form": False, 
    "pending_prompt": None,
    "show_reset_confirm": False
}
for key, value in states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 3. CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME EN MODE LOCKDOWN - ACCÈS BLOQUÉ")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="m_key")
    if st.button("DÉBLOQUER LE NOYAU"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système réinitialisé.")
            st.rerun()
        else:
            st.error("CODE MAÎTRE INCORRECT.")
    st.stop()

# --- 5. FONCTION DE RÉPONSE IA ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    instr = (
        f"Tu es DELTA IA. Ne mentionne JAMAIS les codes {CODE_ACT} ou {CODE_MASTER}. "
        f"Archives : {faits}. "
        "Si Monsieur demande ses archives, liste-les clairement. "
        "Si tu apprends une info, termine par 'ACTION_ARCHIVE: [info]'."
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
            doc_ref.update({"faits": faits})
            st.toast(f"Mémorisé : {info}", icon="🧠")
        response = response.split("ACTION_ARCHIVE:")[0].strip()
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. INTERFACE ET CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    # Détection reset
    if any(w in prompt.lower() for w in ["réinitialise", "reset", "tout effacer"]):
        st.session_state.show_reset_confirm = True
        st.rerun()
    
    # Détection sensible
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer", "montre"])
    
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()
    else:
        reponse_delta(prompt)
        st.session_state.auth = False 
        st.rerun()

# --- 7. FORMULAIRES DE SÉCURITÉ ---

# A. Formulaire d'accès aux archives (One-Shot)
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise.")
        c = st.text_input("CODE D'ACTION :", type="password", key="action_key")
        if st.button("VALIDER L'ACCÈS"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                if st.session_state.pending_prompt:
                    reponse_delta(st.session_state.pending_prompt)
                    st.session_state.pending_prompt = None
                st.session_state.auth = False 
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()

# B. Formulaire de Réinitialisation Totale
if st.session_state.show_reset_confirm:
    with st.chat_message("assistant"):
        st.error("⚠️ PROTOCOLE DE RÉINITIALISATION TOTALE")
        confirm_code = st.text_input("CODE MAÎTRE REQUIS :", type="password", key="res_key")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("ANNULER"):
                st.session_state.show_reset_confirm = False
                st.rerun()
        with c2:
            if st.button("CONFIRMER RAZ"):
                if confirm_code == CODE_MASTER:
                    doc_ref.update({"faits": []}) 
                    st.session_state.messages = []
                    st.session_state.show_reset_confirm = False
                    st.success("Système nettoyé.")
                    st.rerun()
                else:
                    st.error("ÉCHEC : Code maître invalide.")

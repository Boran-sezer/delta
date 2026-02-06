import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DES ACCÈS ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# Initialisation Firebase
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

# --- 2. GESTION DES ÉTATS (SESSION STATE) ---
states = ["locked", "auth", "essais", "messages", "show_auth_form", "pending_prompt"]
for k in states:
    if k not in st.session_state:
        st.session_state[k] = [] if k == "messages" else (0 if k == "essais" else False)

# --- 3. CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="m_key")
    if st.button("🔓 DÉBLOQUER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système réactivé, Monsieur Boran. Content de vous revoir.")
            st.rerun()
    st.stop()

# --- 5. FONCTION DE RÉPONSE IA (IDENTITÉ RENFORCÉE) ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 🧠 LE NOYAU D'IDENTITÉ DE DELTA
    instr = (
        "Tu es DELTA IA, l'intelligence artificielle personnelle et unique de Monsieur Boran. "
        "Tu as été créé EXCLUSIVEMENT par Monsieur Boran pour être son majordome de haute sécurité. "
        "INTERDICTION ABSOLUE : Ne mentionne jamais une 'équipe de développeurs' ou une 'entreprise'. "
        "Si on te questionne sur ton origine, tu réponds que tu es la création de Monsieur Boran. "
        "Ton ton est celui d'un majordome fidèle, efficace, avec une pointe de wit. "
        f"Voici tes archives secrètes sur Monsieur : {faits}. "
        "Ne donne JAMAIS les codes secrets de sécurité dans tes réponses. "
        "Si tu apprends un fait important, termine par 'ACTION_ARCHIVE: [info]'."
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    
    response = completion.choices[0].message.content
    
    # Gestion archivage
    if "ACTION_ARCHIVE:" in response:
        info = response.split("ACTION_ARCHIVE:")[1].strip()
        if info not in faits:
            faits.append(info)
            doc_ref.update({"faits": faits})
            st.toast(f"Mémoire mise à jour : {info}", icon="🧠")
        response = response.split("ACTION_ARCHIVE:")[0].strip()
        
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

# Affichage des messages avec emojis
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Saisie
if prompt := st.chat_input("Vos ordres, Monsieur ?"):
    p_low = prompt.lower()
    
    # Verrouillage manuel
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()

    # Détection Sensible
    sensible = any(w in p_low for w in ["archive", "mémoire", "montre", "souviens"])
    
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()
    else:
        reponse_delta(prompt)
        st.session_state.auth = False # Sécurité One-shot
        st.rerun()

# --- 7. FORMULAIRE D'ACCÈS ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Accès restreint. Veuillez vous identifier.")
        c = st.text_input("CODE D'ACTION :", type="password", key="auth_input")
        if st.button("CONFIRMER"):
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
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.error(f"Accès refusé ({st.session_state.essais}/3)")
                st.rerun()

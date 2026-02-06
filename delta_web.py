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

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA activé. Prêt à vous servir, Monsieur SEZER. ⚡"}]
if "auth" not in st.session_state: st.session_state.auth = False
if "locked" not in st.session_state: st.session_state.locked = False

# --- 3. CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ")
    m_input = st.text_input("CODE MAÎTRE :", type="password")
    if st.button("DÉBLOQUER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.rerun()
    st.stop()

# --- 5. GÉNÉRATEUR SILENCIEUX ET LENT ---
def generer_reponse_discrete(prompt):
    instr = (
        "Tu es DELTA IA, le majordome personnel de Monsieur SEZER. "
        "CONSIGNE ABSOLUE : Ne mentionne JAMAIS tes archives ou tes balises techniques dans ta réponse finale. "
        "Agis avec une discrétion totale. Si tu dois mémoriser quelque chose, ajoute 'ACTION_ARCHIVE: [info]' à la toute fin, "
        "mais sache que ce sera masqué à l'utilisateur."
        f"Archives : {faits}."
    )
    
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages,
        stream=True
    )
    
    full_text = ""
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            full_text += content
            # On n'affiche pas la balise ACTION_ARCHIVE pendant l'écriture
            if "ACTION_ARCHIVE:" not in full_text:
                for char in content:
                    yield char
                    time.sleep(0.02)

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Vos ordres, Monsieur SEZER ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # Écriture progressive et filtrage de la balise
        response_complete = ""
        placeholder = st.empty()
        
        # On capture la réponse pour extraire l'archive sans l'afficher
        response_claire = st.write_stream(generer_reponse_discrete(prompt))
        
        # Récupération de la réponse brute pour traiter l'archive en secret
        # (L'IA renvoie la balise à la fin du stream mais le générateur l'a masquée visuellement)
        raw_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extrais uniquement l'info après ACTION_ARCHIVE dans ce texte s'il y en a une, sinon réponds 'RIEN' : " + response_claire}]
        ).choices[0].message.content

        if "ACTION_ARCHIVE:" in response_claire:
            info = response_claire.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
            # On nettoie la réponse finale pour l'historique
            response_claire = response_claire.split("ACTION_ARCHIVE:")[0].strip()

    st.session_state.messages.append({"role": "assistant", "content": response_claire})

import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
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

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- SIDEBAR (ARCHIVES) ---
with st.sidebar:
    st.title("🧠 Archives")
    if st.button("🗑️ TOUT EFFACER"):
        doc_ref.update({"faits": []})
        st.rerun()
    st.write("---")
    for i, fait in enumerate(faits):
        col1, col2 = st.columns([4, 1])
        col1.info(fait)
        if col2.button("🗑️", key=f"del_{i}"):
            faits.pop(i)
            doc_ref.update({"faits": faits})
            st.rerun()

# --- INTERFACE DE CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    with st.chat_message("assistant"):
        # 🛡️ INSTRUCTION SYSTÈME AVEC AUTONOMIE D'ARCHIVAGE
        instr = (
            "Tu es DELTA, le majordome de Monsieur Boran. "
            f"Archives actuelles : {faits}. "
            "RÈGLE D'ARCHIVAGE : Analyse les messages de Monsieur. Si tu détectes une information personnelle, "
            "une préférence ou un fait important qu'il n'a pas encore archivé, "
            "ajoute impérativement 'ACTION_ARCHIVE: [info]' à la fin de ta réponse pour le mémoriser."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        
        rep = r.choices[0].message.content
        
        # --- TRAITEMENT DE L'ARCHIVAGE PROACTIF ---
        if "ACTION_ARCHIVE:" in rep:
            partie_archive = rep.split("ACTION_ARCHIVE:")[1].strip()
            # On vérifie si l'info n'est pas déjà présente
            if partie_archive not in faits:
                faits.append(partie_archive)
                doc_ref.update({"faits": faits})
                st.toast(f"Nouvelle archive ajoutée : {partie_archive}")
            
            # Nettoyage de la réponse
            propre = rep.split("ACTION_ARCHIVE:")[0].strip()
            st.markdown(propre)
            st.session_state.messages.append({"role": "assistant", "content": propre})
            st.rerun()
        else:
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})

# --- NOTE DE MÉMOIRE ---
# D'accord, je garde ça en mémoire. Vous pouvez à tout moment me demander d'oublier 
# certaines informations ou les gérer dans vos paramètres (https://gemini.google.com/saved-info).

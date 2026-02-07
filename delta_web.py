import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- INTERFACE ÉPURÉE (MODE BLANC) ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #ffffff; color: #1a1a1a; }
    .stChatMessage { background-color: #f8f9fa; border-radius: 15px; border: 1px solid #eaeaea; margin-bottom: 10px; }
    button { display: none; }
    .stChatInputContainer { background: #ffffff !important; border-top: 1px solid #f0f0f0; }
    .title-delta { 
        font-family: 'Inter', sans-serif; 
        font-weight: 800; 
        font-size: 3rem; 
        text-align: center; 
        color: #1a1a1a; 
        letter-spacing: -2px;
        margin-top: -50px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- TRAITEMENT LOGIQUE ---
if prompt := st.chat_input("En quoi puis-je vous aider, Monsieur Sezer ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mise à jour mémoire (Système de fond Llama 8B)
    if len(prompt.split()) > 2:
        try:
            m_prompt = f"Archives: {archives}. Nouveau message: {prompt}. Mets à jour le JSON si nécessaire."
            check = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Tu es un gestionnaire de base de données JSON. Strictement du JSON."}, {"role": "user", "content": m_prompt}],
                response_format={"type": "json_object"}
            )
            archives = json.loads(check.choices[0].message.content)
            doc_ref.set({"archives": archives}, merge=True)
        except:
            pass

    # Réponse DELTA (Personnalité Jarvis - Llama 70B)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        mem_info = f"Informations sur l'utilisateur: {json.dumps(archives)}" if archives else "Aucune donnée spécifique."
        
        system_instruction = (
            f"Tu es DELTA, une IA sophistiquée, polie et dévouée, inspirée de JARVIS. "
            f"Créateur: Monsieur Sezer. Contexte mémorisé: {mem_info}. "
            "TON : Élégant, serviable, protecteur et chaleureux. "
            "RÈGLES : Ne mentionne jamais tes fichiers de mémoire. Sois précis et efficace. "
            "Termine impérativement par 'Monsieur Sezer'."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages[-10:],
                temperature=0.5, # Légère augmentation pour plus de naturel
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception:
            st.error("Navré, Monsieur Sezer, une erreur technique est survenue.")

        st.session_state.messages.append({"role": "assistant", "content": full_res})

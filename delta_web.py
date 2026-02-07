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
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #ffffff; color: #1a1a1a; }
    .stChatMessage { background-color: #f7f7f8; border-radius: 10px; border: 1px solid #e5e5e5; }
    button { display: none; }
    .title-delta { font-weight: 800; font-size: 2.8rem; text-align: center; color: #000; letter-spacing: -2px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)
st.divider()

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- TRAITEMENT ---
if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Mise à jour mémoire (Inspiration Lux, filtrage DELTA)
    if len(prompt.split()) > 2:
        try:
            m_prompt = f"Archives: {archives}. Message: {prompt}. Update JSON memory if info is relevant."
            check = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "You are a JSON database manager. No prose."}, {"role": "user", "content": m_prompt}],
                response_format={"type": "json_object"}
            )
            archives = json.loads(check.choices[0].message.content)
            doc_ref.set({"archives": archives}, merge=True)
        except: pass

    # Réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        mem_info = f"Mémoire: {json.dumps(archives)}" if archives else "Néant."
        
        system_instruction = (
            f"Tu es DELTA. Créateur: Monsieur Sezer. {mem_info}. "
            "RÈGLE: Réponse courte, sans politesse, sans mentionner ta mémoire. "
            "Termine par 'Monsieur Sezer'."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages[-6:],
            temperature=0.4,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})

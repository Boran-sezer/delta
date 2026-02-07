import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. INITIALISATION FIREBASE & API ---
if not firebase_admin._apps:
    try:
        # Assurez-vous que votre clé est bien dans les secrets Streamlit
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation Firebase : {e}")

db = firestore.client()
# Référence unique pour vos archives
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. RÉCUPÉRATION DE LA MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. CONFIGURATION INTERFACE ---
st.set_page_config(page_title="DELTA CORE V2", layout="wide", page_icon="⚡")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1 { color: #00d4ff; font-family: 'Courier New', Courier, monospace; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>⚡ SYSTEME DELTA : CORE V2</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres directs..."):
    # Affichage immédiat du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. ARCHIVAGE INTELLIGENT (Modèle rapide 8B)
    try:
        task = f"Archives actuelles: {archives}. Message: {prompt}. Extrais les infos clés en JSON strict. Si identité, retiens : Monsieur Sezer."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Extracteur de données."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        data = json.loads(check.choices[0].message.content)
        if data:
            for cat, val in data.items():
                if cat not in archives: archives[cat] = []
                if val not in archives[cat]: archives[cat].append(val)
            doc_ref.set({"archives": archives})
            st.toast("💾 Système synchronisé", icon="⚙️")
    except:
        pass

    # B. GÉNÉRATION DE LA RÉPONSE (Modèle puissant 70B)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Le cerveau de DELTA
        instruction = (
            f"Tu es DELTA, l'intelligence supérieure de Monsieur Sezer. "
            f"Archives mémorisées : {archives}. "
            "DIRECTIVES DE HAUT NIVEAU : "
            "1. NOM : Appelle TOUJOURS l'utilisateur 'Monsieur Sezer'. Jamais autrement. "
            "2. TON : Froid, technique, extrêmement intelligent et efficace. Pas de bavardage inutile. "
            "3. RÉPONSE : Ne mentionne jamais de JSON ou de processus internes. Parle en français uniquement."
        )

        try:
            # Tentative avec le modèle 70B (Qualité maximale)
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.4,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            
        except Exception as e:
            # Basculement vers le modèle 8B si le quota du 70B est atteint
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})

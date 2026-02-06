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
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False
if "pending_prompt" not in st.session_state: st.session_state.pending_prompt = None

# --- 3. CHARGEMENT DE LA MÉMOIRE DEPUIS FIREBASE ---
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
            st.success("Système réactivé, Monsieur Boran.")
            st.rerun()
    st.stop()

# --- 5. FONCTION DE RÉPONSE IA ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Instructions strictes pour l'archivage
    instr = (
        "Tu es DELTA IA, l'intelligence artificielle personnelle de Monsieur Boran. "
        "Tu as été créé par lui seul. "
        f"Voici tes archives actuelles sur lui : {faits}. "
        "IMPORTANT : Si Monsieur te donne une information personnelle (couleur, goût, info), "
        "tu DOIS finir ta réponse par la balise exacte : ACTION_ARCHIVE: [l'info à retenir]. "
        "Ne donne jamais tes codes secrets."
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    
    response = completion.choices[0].message.content
    
    # --- LOGIQUE D'ÉCRITURE DANS FIREBASE ---
    if "ACTION_ARCHIVE:" in response:
        parts = response.split("ACTION_ARCHIVE:")
        info_a_sauver = parts[1].strip()
        texte_final = parts[0].strip()
        
        if info_a_sauver not in faits:
            faits.append(info_a_sauver)
            # Envoi vers Firestore
            doc_ref.set({"faits": faits}, merge=True) 
            st.success(f"✅ Mémoire Firestore mise à jour : {info_a_sauver}")
            st.balloons() # Confirmation visuelle
        
        response = texte_final
        
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Vos ordres, Monsieur ?"):
    p_low = prompt.lower()
    
    # Verrouillage manuel
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()

    # Détection demande d'archives
    sensible = any(w in p_low for w in ["archive", "mémoire", "montre", "souviens"])
    
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()
    else:
        reponse_delta(prompt)
        st.session_state.auth = False 
        st.rerun()

# --- 7. FORMULAIRE D'ACCÈS ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise pour la mémoire.")
        c = st.text_input("CODE :", type="password", key="auth_input")
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
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()

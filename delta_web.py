import streamlit as st

# --- INITIALISATION DES ÉTATS ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "security_mode" not in st.session_state:
    st.session_state.security_mode = False
if "attempts" not in st.session_state:
    st.session_state.attempts = 0

st.title("⚡ DELTA SYSTEM")

# --- AFFICHAGE DU CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- ZONE DE SAISIE ---
if p := st.chat_input("Vos ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    rep = ""

    # 1. SI ON ATTEND LE CODE
    if st.session_state.security_mode:
        if p == "20082008":
            rep = "✅ **Code correct.** Réinitialisation effectuée."
            st.session_state.security_mode = False
            st.session_state.attempts = 0
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ **Code incorrect.** Recommencez (Essai {st.session_state.attempts}/3)."
            else:
                rep = "🔴 **ROUGE**"
                st.session_state.security_mode = False
                st.session_state.attempts = 0

    # 2. DÉTECTION DE LA DEMANDE DE RÉINITIALISATION
    elif "réinitialisation" in p.lower():
        st.session_state.security_mode = True
        st.session_state.attempts = 0
        rep = "🔒 **Sécurité activée.** Veuillez entrer le code d'accès."

    # 3. RÉPONSE PAR DÉFAUT
    else:
        rep = "Je suis à votre écoute. Dites 'réinitialisation' pour tester le protocole."

    # AFFICHAGE DE LA RÉPONSE
    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

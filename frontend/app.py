"""Interface Streamlit PlantWorld AI."""

import uuid

import streamlit as st

import evaluation_page
from config import ACCEPTED_TYPES
from services.api_client import ApiError, analyze, chat

st.set_page_config(page_title="PlantWorld AI", page_icon="🌿", layout="centered")

# --- Navigation : page d'analyse ou page d'évaluation du workflow ----------
if st.sidebar.button("🧪 Évaluation du workflow", width="stretch"):
    st.session_state.page = "evaluation"
    st.rerun()

if st.session_state.get("page") == "evaluation":
    evaluation_page.render()
    st.stop()

# --- En-tête ---------------------------------------------------------------
st.title("🌿 PlantWorld AI")
st.caption("Importez une photo de plante, lancez l'analyse, puis discutez du résultat.")


uploaded_file = st.file_uploader("Choisissez une image", type=ACCEPTED_TYPES)

if uploaded_file is None:
    st.info("Formats acceptés : JPG, JPEG, PNG.")
    st.stop()

# Streamlit ré-exécute ce script à chaque interaction : l'analyse et la conversation
# sont gardées dans st.session_state, et remises à zéro quand l'image change.
if st.session_state.get("file_id") != uploaded_file.file_id:
    st.session_state.file_id = uploaded_file.file_id
    st.session_state.analysis = None
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())  # identifiant de la conversation (mémoire n8n)

st.image(uploaded_file, caption=uploaded_file.name, width="stretch")

# --- Analyse ---------------------------------------------------------------
if st.button("Analyser", type="primary", width="stretch"):
    with st.spinner("Analyse en cours..."):
        try:
            st.session_state.analysis = analyze(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())  # nouvelle analyse = nouvelle conversation
        except ApiError as error:
            st.error(str(error))

analysis = st.session_state.analysis
if analysis is None:
    st.stop()

st.subheader("Résultat de l'analyse")
result = analysis["result"]
confidence = f"Confiance : {result['confidence']:.0%}"

if not result["recognized"]:
    st.warning(
        "**Plante non reconnue avec certitude.**  \n"
        "Essayez une photo nette d'une seule feuille, bien éclairée, sur un fond uni."
    )
elif result["is_healthy"]:
    st.success(f"**{result['plant']}** : la plante semble saine.  \n{confidence}")
else:
    st.error(f"**{result['plant']}** : {result['disease']} détecté(e).  \n{confidence}")

# --- Chatbot ---------------------------------------------------------------
st.divider()
st.subheader("💬 Discuter de cette analyse")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Posez une question sur cette plante..."):
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            try:
                reply = chat(st.session_state.session_id, question, analysis["result"], st.session_state.messages)
            except ApiError as error:
                st.error(str(error))
            else:
                st.markdown(reply)
                st.session_state.messages += [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": reply},
                ]

#front end side - run with streamlit run app.py


import streamlit as st
import requests

st.set_page_config(page_title="Israeli Medical Chatbot", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "phase" not in st.session_state:
    st.session_state.phase = "collection"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

st.title("🏥 Medical Service Assistant")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("How can I help you?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Microservice
    payload = {
        "message": prompt,
        "history": st.session_state.messages,
        "user_profile": st.session_state.user_data,
        "phase": st.session_state.phase
    }

    response_json = requests.post("http://localhost:8000/chat", json=payload).json()
    ai_response = response_json["response"]

    # If the backend extracted a profile, save it and switch phases
    if response_json.get("extracted_profile"):
        st.session_state.user_data = response_json["extracted_profile"]
        st.session_state.phase = "qa"
        st.success(f"Verified: {st.session_state.user_data['Full Name']}")
    ai_response = response_json["response"]

    # Check if Phase 1 is complete (Basic Logic)
    if "[COMPLETE]" in ai_response and st.session_state.phase == "collection":
        st.session_state.phase = "qa"
        st.success("Registration complete! You can now ask about medical services.")

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
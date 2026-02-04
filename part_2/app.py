# Medical Chatbot Frontend with Advanced RTL/LTR Support
# Light Blue & Dark Blue Medical Theme
# Run with: streamlit run app.py

import streamlit as st
import requests
import re

# Page configuration
st.set_page_config(
    page_title="Israeli Medical Chatbot",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS with Light Blue & Dark Blue Medical Theme
st.markdown("""
<style>
    /* Hebrew RTL chat bubbles */
    .chat-rtl {
        direction: rtl;
        text-align: right;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        line-height: 1.6;
        font-size: 1rem;
    }

    /* English LTR chat bubbles */
    .chat-ltr {
        direction: ltr;
        text-align: left;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        line-height: 1.6;
        font-size: 1rem;
    }

    /* USER MESSAGE - LIGHT BLUE */
    .user-message-rtl {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        direction: rtl;
        text-align: right;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(79, 172, 254, 0.3);
        line-height: 1.6;
        font-size: 1rem;
    }

    .user-message-ltr {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        direction: ltr;
        text-align: left;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(79, 172, 254, 0.3);
        line-height: 1.6;
        font-size: 1rem;
    }

    /* ASSISTANT MESSAGE - DARK BLUE */
    .assistant-message-rtl {
        background: linear-gradient(135deg, #005eb8 0%, #003d82 100%);
        color: white;
        direction: rtl;
        text-align: right;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0, 94, 184, 0.3);
        line-height: 1.6;
        font-size: 1rem;
    }

    .assistant-message-ltr {
        background: linear-gradient(135deg, #005eb8 0%, #003d82 100%);
        color: white;
        direction: ltr;
        text-align: left;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0, 94, 184, 0.3);
        line-height: 1.6;
        font-size: 1rem;
    }

    /* Code blocks in messages */
    .user-message-rtl code, .user-message-ltr code,
    .assistant-message-rtl code, .assistant-message-ltr code {
        background-color: rgba(255,255,255,0.2);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }

    /* Lists in RTL */
    .user-message-rtl ol, .user-message-rtl ul,
    .assistant-message-rtl ol, .assistant-message-rtl ul {
        padding-right: 1.5rem;
        padding-left: 0;
    }

    /* Lists in LTR */
    .user-message-ltr ol, .user-message-ltr ul,
    .assistant-message-ltr ol, .assistant-message-ltr ul {
        padding-left: 1.5rem;
        padding-right: 0;
    }

    /* Hide Streamlit default chat styling */
    .stChatMessage {
        background-color: transparent !important;
    }

    /* Profile info box - Medical Blue with Green Accent */
    .profile-box-rtl {
        background: linear-gradient(135deg, #005eb8 0%, #003d82 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        direction: rtl;
        text-align: right;
        margin: 1rem 0;
        border-left: 5px solid #00a650;
        box-shadow: 0 3px 10px rgba(0, 94, 184, 0.3);
    }

    .profile-box-ltr {
        background: linear-gradient(135deg, #005eb8 0%, #003d82 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        direction: ltr;
        text-align: left;
        margin: 1rem 0;
        border-right: 5px solid #00a650;
        box-shadow: 0 3px 10px rgba(0, 94, 184, 0.3);
    }
</style>
""", unsafe_allow_html=True)


def detect_language(text: str) -> str:
    """
    Detects if text is primarily Hebrew or English.
    Returns 'rtl' for Hebrew, 'ltr' for English.
    """
    if not text:
        return 'ltr'

    # Count Hebrew characters (Unicode range: 0590-05FF)
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    # Count Latin characters
    latin_chars = len(re.findall(r'[a-zA-Z]', text))

    # If more Hebrew characters, use RTL
    return 'rtl' if hebrew_chars > latin_chars else 'ltr'


def detect_language_code(text: str) -> str:
    """
    Detects language and returns backend language code.
    Returns 'he' for Hebrew, 'en' for English.
    """
    direction = detect_language(text)
    return 'he' if direction == 'rtl' else 'en'


def clean_message(content: str) -> str:
    """Removes technical tags and empty code blocks from message content."""
    # 1. Remove [COMPLETE] tag
    content = content.replace("[COMPLETE]", "").strip()

    # 2. Remove JSON blocks with content
    content = re.sub(r'```\s*\{.*?\}\s*```', '', content, flags=re.DOTALL)
    content = re.sub(r'\{[^}]*"Full Name"[^}]*\}', '', content, flags=re.DOTALL)

    # 3. ADDED: Remove empty json code blocks or standalone backticks
    content = re.sub(r'```json\s*```', '', content, flags=re.I)
    content = content.replace('```', '')

    return content.strip()


def render_message_html(content: str, role: str):
    """
    Renders a message with proper HTML styling and text direction.
    """
    direction = detect_language(content)
    cleaned_content = clean_message(content)

    if not cleaned_content:
        return

    # Escape HTML but preserve newlines
    cleaned_content = cleaned_content.replace('<', '&lt;').replace('>', '&gt;')
    cleaned_content = cleaned_content.replace('\n', '<br>')

    # Choose CSS class based on role and direction
    css_class = f"{role}-message-{direction}"

    # Render
    st.markdown(f'<div class="{css_class}">{cleaned_content}</div>', unsafe_allow_html=True)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "phase" not in st.session_state:
    st.session_state.phase = "collection"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "preferred_language" not in st.session_state:
    st.session_state.preferred_language = None  # Will be set from first message

# Header with medical blue color
st.markdown("""
    <h1 style='text-align: center; color: #005eb8;'> Medical Service Assistant</h1>
    <p style='text-align: center; color: #666;'>עוזר שירותי בריאות | Medical Services Helper</p>
""", unsafe_allow_html=True)

# Show current user profile if in Q&A phase
if st.session_state.phase == "qa" and st.session_state.user_data:
    user_name = st.session_state.user_data.get('Full Name', '')
    hmo = st.session_state.user_data.get('HMO', '')
    tier = st.session_state.user_data.get('Insurance Tier', '')

    direction = detect_language(user_name)
    css_class = f"profile-box-{direction}"

    profile_html = f"""
    <div class="{css_class}">
        <strong>👤 {user_name}</strong><br>
        🏥 {hmo} - {tier}
    </div>
    """
    st.markdown(profile_html, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📖 הוראות | Instructions")

    st.markdown("""
    <div style='direction: rtl; text-align: right; background: #e3f2fd; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
        <h4 style='color: #005eb8;'>עברית:</h4>
        <ol>
            <li>ספקו את הפרטים האישיים שלכם</li>
            <li>אשרו את הפרטים</li>
            <li>שאלו על שירותי בריאות</li>
        </ol>
    </div>

    <div style='direction: ltr; text-align: left; background: #e3f2fd; padding: 1rem; border-radius: 8px;'>
        <h4 style='color: #005eb8;'>English:</h4>
        <ol>
            <li>Provide your personal information</li>
            <li>Confirm the details</li>
            <li>Ask about medical services</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Reset button
    if st.button("🔄 התחל מחדש | Start Over", use_container_width=True):
        st.session_state.messages = []
        st.session_state.phase = "collection"
        st.session_state.user_data = {}
        st.session_state.preferred_language = None  # Reset language preference
        st.rerun()

    # Status indicator
    st.markdown("---")
    if st.session_state.phase == "collection":
        st.info("📝 Phase: Information Collection\nשלב: איסוף מידע")
    else:
        st.success("💬 Phase: Q&A\nשלב: שאלות ותשובות")

# Display chat history
for message in st.session_state.messages:
    render_message_html(message["content"], message["role"])

# Chat input
placeholder_text = "Type your message... | הקלד הודעה..."
if prompt := st.chat_input(placeholder_text):
    # Detect and store language from first message
    if st.session_state.preferred_language is None:
        st.session_state.preferred_language = detect_language_code(prompt)
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_message_html(prompt, "user")

    # Prepare API request with preferred language
    payload = {
        "message": prompt,
        "history": st.session_state.messages[:-1],
        "user_profile": st.session_state.user_data,
        "phase": st.session_state.phase,
        "preferred_language": st.session_state.preferred_language
    }

    # Call backend
    try:
        with st.spinner("⏳ Processing... | מעבד..."):
            response = requests.post(
                "http://localhost:8000/chat",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            response_json = response.json()

        ai_response = response_json["response"]

        # Handle profile extraction
        if response_json.get("extracted_profile"):
            st.session_state.user_data = response_json["extracted_profile"]
            st.session_state.phase = "qa"

            # Success message
            user_name = st.session_state.user_data.get('Full Name', '')
            direction = detect_language(user_name)

            if direction == 'rtl':
                st.success(f"✅ רישום הושלם בהצלחה! שלום {user_name}")
            else:
                st.success(f"✅ Registration successful!")

            # Small delay for visual effect
            import time
            time.sleep(0.5)

        # Legacy completion check
        if "[COMPLETE]" in ai_response and st.session_state.phase == "collection":
            st.session_state.phase = "qa"

        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        render_message_html(ai_response, "assistant")

    except requests.exceptions.ConnectionError:
        st.error("""
        ❌ **Connection Error**

        Cannot connect to backend server.

        **Please ensure:**
        - Backend is running: `python main.py`
        - Server is on: http://localhost:8000

        ---

        ❌ **שגיאת חיבור**

        לא ניתן להתחבר לשרת.

        **אנא ודא:**
        - השרת פועל: `python main.py`
        - הכתובת: http://localhost:8000
        """)

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timeout. Please try again. | תם הזמן. אנא נסה שוב.")

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Server error: {e}")

    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")


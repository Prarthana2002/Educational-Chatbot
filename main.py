import os
import json
import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import base64
import tempfile
from datetime import datetime

# File to persist chat history
CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as file:
            return json.load(file)
    return {}

def save_chat_history(history):
    with open(CHAT_HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

def generate_voiceover(text):
    """Generate voiceover audio, store the file path, and return the path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        tts = gTTS(text, lang="en", slow=False)
        tts.save(temp_audio.name)
        return temp_audio.name

def get_audio_player(file_path):
    """Generate an audio player for replay without autoplay."""
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode()
        return f"""
        <audio controls>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
    return ""

def recognize_speech():
    """Recognize speech input and convert it to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Speak now.")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            st.session_state.user_message = text
        except sr.WaitTimeoutError:
            st.warning("Listening timed out. Please try again.")
        except sr.UnknownValueError:
            st.warning("Could not understand the audio. Try speaking again.")
        except sr.RequestError:
            st.error("Could not request results. Check your internet connection.")

st.set_page_config(page_title="AI-Powered Educational Chat Bot", layout="wide")
st.title("🎓 AI-Powered Educational Chat Bot")
st.markdown("Your virtual assistant for all education-related queries.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

today_date = datetime.today().strftime("%Y-%m-%d")
if today_date not in st.session_state.chat_history:
    st.session_state.chat_history[today_date] = []

# Gemini AI Configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Sidebar Chat History
st.sidebar.markdown("<h1 style='text-align: center; margin-top: -50px;'>🤖Educational Bot</h1>", unsafe_allow_html=True)  # Moves title to extreme top
st.sidebar.markdown("---")
st.sidebar.header("Chat History")

selected_date = None
if st.session_state.chat_history:
    with st.sidebar.container():
        for date in sorted(st.session_state.chat_history.keys(), reverse=True):
            if st.sidebar.button(date, key=date, help="View chat history", use_container_width=True):
                st.session_state.selected_date = date
                selected_date = date

# Delete Chat Option
st.sidebar.markdown("---")
st.sidebar.subheader("Manage Chat History")
dates = list(st.session_state.chat_history.keys())
selected_delete_date = st.sidebar.selectbox("Select a date to delete", ["Select"] + dates, key="delete_select")
if st.sidebar.button("Delete Chat", use_container_width=True):
    if selected_delete_date and selected_delete_date != "Select":
        del st.session_state.chat_history[selected_delete_date]
        save_chat_history(st.session_state.chat_history)
        st.sidebar.success(f"Deleted chat history for {selected_delete_date}")
        st.rerun()

# Chat Section
st.subheader("Chat with the AI-Powered Educational Chat Bot")

col1, col2 = st.columns([3, 1])

with col1:
    with st.form("chat_form"):
        user_message = st.text_input("Your Query:", value=st.session_state.get("user_message", ""), placeholder="Type your question here...")
        submitted = st.form_submit_button("Send")

with col2:
    if st.button("🎤 Speak", use_container_width=True):
        recognize_speech()
        st.rerun()

if submitted or user_message:
    if user_message:
        try:
            if "chat_session" not in st.session_state or st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat(history=[{
                    "role": "user",
                    "parts": ["You are an AI designed to simplify complex academic and technical content for enhanced learning accessibility."]
                }])
            response = st.session_state.chat_session.send_message(user_message)
            
            # Generate voiceover and save file path
            voiceover_path = generate_voiceover(response.text)
            
            # Store chat history with voiceover path
            st.session_state.chat_history[today_date].append({
                "inputs": user_message,
                "bot_response": response.text,
                "voiceover": voiceover_path
            })
            save_chat_history(st.session_state.chat_history)
            
            st.session_state.latest_response = response.text
            st.session_state.latest_voiceover = voiceover_path
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display response
if "latest_response" in st.session_state and st.session_state.latest_response:
    col1, col2 = st.columns([8, 2])
    with col1:
        st.markdown(f"**Bot:** {st.session_state.latest_response}")
    with col2:
        if st.button("🔊 Voiceover", use_container_width=True):
            st.markdown(get_audio_player(st.session_state.latest_voiceover), unsafe_allow_html=True)

# Show Chat History
if selected_date:
    st.subheader(f"Chat History ({selected_date})")
    if selected_date in st.session_state.chat_history and st.session_state.chat_history[selected_date]:
        for chat in st.session_state.chat_history[selected_date]:
            st.markdown(f"**You:** {chat['inputs']}")
            st.markdown(f"**Bot:** {chat['bot_response']}")
            if "voiceover" in chat:
                st.markdown(get_audio_player(chat["voiceover"]), unsafe_allow_html=True)
    else:
        st.info("No chat history available for this date.")

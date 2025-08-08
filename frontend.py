"""
Streamlit Frontend with Runtime API Key Input
"""

import streamlit as st
import uuid
import os
from chat import ChatbotBackend

# Page configuration
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Modern AI Chatbot")
st.markdown("Powered by LangGraph, LangChain, and Google Gemini")

# Initialize session state for API key
if 'api_key_entered' not in st.session_state:
    st.session_state.api_key_entered = False
if 'user_api_key' not in st.session_state:
    st.session_state.user_api_key = ""

# Check if API key is available from environment or user input
def get_api_key():
    """Get API key from environment or user input"""
    # First try environment variable
    env_api_key = os.getenv("GEMINI_API_KEY")
    if env_api_key:
        return env_api_key
    # Then try user input
    return st.session_state.user_api_key

# API Key Input Section
if not st.session_state.api_key_entered:
    st.markdown("### 🔑 API Key Required")
    
    # Check if environment API key exists
    env_api_key = os.getenv("GEMINI_API_KEY")
    if env_api_key:
        st.success("✅ API Key found in environment variables!")
        if st.button("Use Environment API Key"):
            st.session_state.api_key_entered = True
            st.session_state.user_api_key = env_api_key
            st.rerun()
    else:
        st.info("No environment API key found. Please enter your Google Gemini API key to continue.")
    
    st.markdown("---")
    
    with st.container():
        st.markdown("#### Enter Your Google Gemini API Key")
        
        # Information about getting API key
        with st.expander("ℹ️ How to get your API Key", expanded=False):
            st.markdown("""
            1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
            2. Sign in with your Google account
            3. Click **"Create API Key"**
            4. Copy the generated API key
            5. Paste it in the field below
            
            **Note:** Your API key is only stored in your browser session and is not saved permanently.
            """)
        
        # API key input
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_input_key = st.text_input(
                "API Key",
                type="password",
                placeholder="Enter your Google Gemini API key here...",
                help="Your API key will only be stored for this session"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
            if st.button("✅ Connect", type="primary"):
                if user_input_key.strip():
                    st.session_state.user_api_key = user_input_key.strip()
                    st.session_state.api_key_entered = True
                    st.rerun()
                else:
                    st.error("Please enter a valid API key")
        
        # Warning about API key security
        st.warning("⚠️ **Security Notice:** We are not sharing your API key. You are advised to Never share your API key publicly. It will only be used for this session.")
    
    # Stop here if no API key is provided
    st.stop()

# Initialize chatbot with API key
if 'chatbot' not in st.session_state:
    try:
        # Create ChatbotBackend with user's API key
        st.session_state.chatbot = ChatbotBackend(api_key=get_api_key())
        st.success("🎉 Chatbot initialized successfully!")
    except Exception as e:
        st.error(f"❌ Failed to initialize chatbot: {str(e)}")
        st.error("Please check your API key and try again.")
        
        # Reset API key state to allow re-entry
        if st.button("🔄 Try Different API Key"):
            st.session_state.api_key_entered = False
            st.session_state.user_api_key = ""
            if 'chatbot' in st.session_state:
                del st.session_state.chatbot
            st.rerun()
        
        st.stop()

# Initialize other session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'message_history' not in st.session_state:
    st.session_state.message_history = []

# Sidebar for controls
with st.sidebar:
    st.header("🎛️ Controls")
    
    # API Key Status
    st.markdown("#### 🔑 API Key Status")
    api_key = get_api_key()
    if api_key:
        masked_key = f"{api_key[:8]}{'*' * 20}{api_key[-4:]}" if len(api_key) > 12 else f"{api_key[:4]}{'*' * 10}"
        st.success(f"✅ Connected: `{masked_key}`")
    else:
        st.error("❌ No API key")
    
    # Disconnect button
    if st.button("🔌 Disconnect & Change API Key"):
        st.session_state.api_key_entered = False
        st.session_state.user_api_key = ""
        st.session_state.message_history = []
        if 'chatbot' in st.session_state:
            del st.session_state.chatbot
        st.rerun()
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.message_history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    
    st.markdown("---")
    
    st.header("ℹ️ Features")
    st.markdown("""
    This chatbot can:
    - 💬 Have natural conversations
    - 🌤️ Get weather information
    - 🧮 Perform calculations
    - 🧠 Remember conversation context
    - 🛠️ Use tools when needed
    """)
    
    st.markdown("---")
    
    st.header("📊 Session Info")
    st.write(f"**Session ID:** `{st.session_state.get('session_id', 'N/A')[:8]}...`")
    st.write(f"**Messages:** {len(st.session_state.message_history)}")
    
    st.markdown("---")
    
    st.header("🔒 Privacy")
    st.markdown("""
    - Your API key is only stored in your browser session
    - No data is saved permanently
    - Conversation history is cleared when you close the browser
    """)

# Display chat messages
chat_container = st.container()

with chat_container:
    # Welcome message if no conversation history
    if not st.session_state.message_history:
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome to the AI Chatbot!**
            
            I'm ready to help you with:
            - **General questions** and conversations
            - **Weather information** for different cities
            - **Mathematical calculations**
            - And much more!
            
            Try asking me something like:
            - "What's the weather in New York?"
            - "Calculate 25 * 4 + 10"
            - "Tell me about Pakistan"
            """)
    
    # Display conversation history
    for message in st.session_state.message_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.message_history.append({"role": "user", "content": prompt})
    
    # Display user message
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Get response from chatbot backend
                    response = st.session_state.chatbot.process_message_sync(
                        prompt, 
                        st.session_state.get('session_id', 'default')
                    )
                    
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.message_history.append({
                        "role": "assistant", 
                        "content": response
                    })
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.message_history.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <small>Reach out to me for your advance Chatbot Solutions | <a href="https://adeelhamid.github.io" target="_blank">Adeel Hamid</a> | 
        <a href="https://makersuite.google.com/app/apikey" target="_blank">Get API Key</a>
        </small>
    </div>
    """, 
    unsafe_allow_html=True
)
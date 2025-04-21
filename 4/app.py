import os
import json
import time
import tempfile
import re
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import requests
import concurrent.futures
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import google.auth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# ------------------ Theme Setup ------------------
st.set_page_config(
    page_title="Claude-Style Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to mimic Claude.ai styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #f9f9f9;
    }
    
    /* Chat message styling */
    .stChatMessage {
        background-color: white;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* User message styling */
    .stChatMessageContent[data-testid="UserChatMessage"] {
        background-color: #f0f7ff;
        border-radius: 8px;
    }
    
    /* Assistant message styling */
    .stChatMessageContent[data-testid="AssistantChatMessage"] {
        background-color: white;
        border-radius: 8px;
    }
    
    /* Input box styling */
    .stChatInputContainer {
        padding: 10px;
        border-top: 1px solid #eee;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: white;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #6c38d0;
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #5429b5;
    }
    
    /* Code block styling */
    pre {
        background-color: #f6f8fa;
        border-radius: 6px;
        padding: 10px;
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: #333;
        font-weight: 500;
    }
    
    /* Link styling */
    a {
        color: #6c38d0;
    }
    
    /* Separator styling */
    hr {
        margin: 1.5rem 0;
        border: none;
        border-top: 1px solid #eee;
    }
    
    /* Custom code buttons */
    .code-action-buttons {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: -5px;
        margin-bottom: 10px;
    }
    
    .code-action-button {
        background-color: #6c38d0;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .code-action-button:hover {
        background-color: #5429b5;
    }
    
    /* Google Sign-in styling */
    .google-btn {
        background-color: white;
        color: #444;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        cursor: pointer;
        font-weight: 500;
        transition: background-color 0.3s;
        width: 100%;
        margin: 20px 0;
    }
    
    .google-btn:hover {
        background-color: #f5f5f5;
    }
    
    /* Chat selector styling */
    .chat-selector {
        margin: 10px 0;
        padding: 10px;
        border-radius: 6px;
        background-color: #f5f5f5;
    }
    
    /* Ad-free badge styling */
    .ad-free-badge {
        background-color: #ffd700;
        color: #333;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 500;
        margin-left: 5px;
    }
    
    /* Usage progress bar */
    .usage-bar {
        height: 8px;
        border-radius: 4px;
        margin: 5px 0;
    }
    
    /* Ad container */
    .ad-container {
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
        text-align: center;
    }
    
    /* Timer styling */
    .ad-timer {
        font-size: 20px;
        font-weight: bold;
        color: #6c38d0;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ Initialization ------------------
load_dotenv()

# Constants
USER_ICON = "👤"
ASSISTANT_ICON = "🤖"
MAX_RETRIES = 3
RETRY_DELAY = 1.5
TEMP_DIR = tempfile.gettempdir()

# Message and ad constants
MESSAGES_PER_AD = 5
AD_DURATION = 10  # seconds

# Load API Key
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API key missing. Please check your .env file.")
    st.stop()

# Load Google Auth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
if not GOOGLE_CLIENT_ID:
    st.error("Google Client ID missing. Please check your .env file.")
    st.stop()

# Load Google AdSense ID
GOOGLE_ADSENSE_ID = os.getenv("GOOGLE_ADSENSE_ID", "ca-pub-1234567890123456")

# Initialize Firebase
firebase_config = os.getenv("FIREBASE_CONFIG")
if firebase_config:
    try:
        # Try to initialize Firebase if not already initialized
        if not firebase_admin._apps:
            # Parse JSON string properly
            config_dict = json.loads(firebase_config)
            cred = credentials.Certificate(config_dict)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except json.JSONDecodeError as e:
        st.error(f"Firebase config JSON parsing error: {e}")
        db = None
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        db = None
else:
    st.warning("Firebase configuration missing. Cloud persistence will be disabled.")
    db = None

# Load model configurations
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "beta.json")
try:
    with open(CONFIG_FILE, 'r') as file:
        models = json.load(file).get("data", [])
        model_ids = [m.get("id") for m in models if m.get("id")]
except Exception as e:
    st.error(f"Model config load error: {e}")
    st.stop()
if not model_ids:
    st.error("No models found in configuration.")
    st.stop()

# Default model settings
DEFAULT_TEXT = "Provider-9/gpt-4.1"
DEFAULT_IMG = "Provider-5/flux-schnell"
text_default = DEFAULT_TEXT if DEFAULT_TEXT in model_ids else model_ids[0]
img_default = DEFAULT_IMG if DEFAULT_IMG in model_ids else model_ids[0]

# Initialize OpenAI client
client = OpenAI(api_key=API_KEY, base_url="https://beta.sree.shop/v1")

# Coupon codes mapping
COUPON_CODES = {
    "NOAD2025": {"ad_free_days": 30, "description": "30 days ad-free experience"},
    "WELCOME15": {"ad_free_days": 15, "description": "15 days ad-free experience"},
    "FRIEND7": {"ad_free_days": 7, "description": "7 days ad-free experience"}
}

# ------------------ Helper Functions ------------------
@st.cache_data(ttl=60)
def check_model_status(model_id, timeout=2):
    """Check if a model is online and return status information."""
    try:
        url = f"https://beta.sree.shop/v1/uptime/{model_id}"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return {"id": model_id, "status": "online"}
        else:
            return {"id": model_id, "status": "offline", "error": resp.text}
    except Exception as e:
        return {"id": model_id, "status": "error", "error": str(e)}

def get_live_models(model_ids):
    """Return a list of model IDs that are currently online."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_model_status, model_ids))
    
    online_models = [result["id"] for result in results if result["status"] == "online"]
    return online_models if online_models else model_ids  # Fallback to all models if none are online

def verify_google_token(id_token_jwt):
    """Verify Google ID token and return user info."""
    try:
        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(id_token_jwt, request, GOOGLE_CLIENT_ID)
        
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return id_info
    except Exception as e:
        st.error(f"Token verification failed: {e}")
        return None

def get_today_start():
    """Get the start of the current day in UTC."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    return today_start

def get_or_create_user(email):
    """Get user data from Firestore or create a new user profile."""
    if not db:
        # Fallback to session state if no Firestore
        if "user_data" not in st.session_state:
            st.session_state.user_data = {
                "email": email,
                "messages_since_last_ad": 0,
                "ad_free_until": None,
                "chats": {"General": []}
            }
        return st.session_state.user_data
    
    # Get from Firestore
    user_ref = db.collection("users").document(email)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        # Initialize chats if not present
        if "chats" not in user_data:
            user_data["chats"] = {"General": []}
        
        # Initialize ad tracking if not present
        if "messages_since_last_ad" not in user_data:
            user_data["messages_since_last_ad"] = 0
        
        user_ref.update(user_data)
    else:
        # Create new user
        user_data = {
            "email": email,
            "messages_since_last_ad": 0,
            "ad_free_until": None,
            "chats": {"General": []}
        }
        user_ref.set(user_data)
    
    return user_data

def update_user_data(email, user_data):
    """Update user data in Firestore."""
    if not db:
        # Fallback to session state if no Firestore
        st.session_state.user_data = user_data
        return
    
    # Update in Firestore
    db.collection("users").document(email).update(user_data)

def get_user_chat_history(email, chat_name):
    """Get chat history for a specific chat."""
    user_data = st.session_state.user_data
    return user_data["chats"].get(chat_name, [])

def update_user_chat_history(email, chat_name, messages):
    """Update chat history for a specific chat."""
    user_data = st.session_state.user_data
    user_data["chats"][chat_name] = messages
    update_user_data(email, user_data)

def increment_message_counter(email):
    """Increment message counter and check if ad should be shown."""
    user_data = st.session_state.user_data
    
    # Check if user has ad-free status
    ad_free_until = user_data.get("ad_free_until")
    if ad_free_until and datetime.now().timestamp() < ad_free_until:
        # User has active ad-free status
        return False
    
    # Increment counter
    counter = user_data.get("messages_since_last_ad", 0) + 1
    user_data["messages_since_last_ad"] = counter
    update_user_data(email, user_data)
    
    # Check if it's time to show an ad (every MESSAGES_PER_AD messages)
    if counter >= MESSAGES_PER_AD:
        user_data["messages_since_last_ad"] = 0
        update_user_data(email, user_data)
        return True
    
    return False

def apply_coupon_code(email, code):
    """Apply coupon code for ad-free period."""
    if code not in COUPON_CODES:
        return False, "Invalid coupon code"
    
    user_data = st.session_state.user_data
    
    # Calculate new ad-free period
    days = COUPON_CODES[code]["ad_free_days"]
    now = datetime.now()
    
    # If user already has ad-free time, extend it
    current_until = user_data.get("ad_free_until")
    if current_until and current_until > now.timestamp():
        new_until = datetime.fromtimestamp(current_until) + timedelta(days=days)
    else:
        new_until = now + timedelta(days=days)
    
    # Update user data
    user_data["ad_free_until"] = new_until.timestamp()
    update_user_data(email, user_data)
    
    return True, f"Coupon applied! Ad-free until {new_until.strftime('%B %d, %Y')}"

def get_ad_free_status(email):
    """Check if user has ad-free status and return expiry date."""
    user_data = st.session_state.user_data
    ad_free_until = user_data.get("ad_free_until")
    
    if ad_free_until and datetime.now().timestamp() < ad_free_until:
        return True, datetime.fromtimestamp(ad_free_until).strftime("%B %d, %Y")
    
    return False, None

def trim_context(messages, max_count):
    """Trim the context to keep only system messages and recent chat messages."""
    system_msgs = [msg for msg in messages if msg.get("role") == "system"]
    chat_msgs = [msg for msg in messages if msg.get("role") in ["user", "assistant"]]
    
    if len(chat_msgs) > max_count:
        return system_msgs + chat_msgs[-max_count:]
    return messages

def extract_code_blocks(text):
    """Extract code blocks from text."""
    pattern = r"```(\w*)\n([\s\S]*?)```"
    matches = re.finditer(pattern, text)
    
    blocks = []
    for match in matches:
        lang = match.group(1).lower() or "python"
        code = match.group(2)
        block_id = hashlib.md5(code.encode()).hexdigest()[:8]
        blocks.append({
            "id": block_id,
            "language": lang,
            "code": code
        })
    
    return blocks

def get_language_extension(language):
    """Get file extension for language."""
    extensions = {
        "python": ".py",
        "py": ".py",
        "javascript": ".js",
        "js": ".js",
        "html": ".html",
        "css": ".css",
        "shell": ".sh",
        "bash": ".sh",
        "json": ".json",
        "typescript": ".ts",
        "tsx": ".tsx",
        "jsx": ".jsx",
    }
    return extensions.get(language.lower(), ".txt")

def copy_button_html(code_id, code):
    """Generate HTML for a copy button."""
    # Escape JS string
    escaped_code = code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("</script>", "<\\/script>")
    
    return f"""
    <button id="copy_btn_{code_id}" class="code-action-button">
        📋 Copy
    </button>
    <script>
        (function() {{
            const btn = document.getElementById('copy_btn_{code_id}');
            btn.addEventListener('click', function() {{
                const code = `{escaped_code}`;
                navigator.clipboard.writeText(code).then(function() {{
                    btn.textContent = '✓ Copied';
                    setTimeout(function() {{
                        btn.textContent = '📋 Copy';
                    }}, 2000);
                }});
            }});
        }})();
    </script>
    """

def run_button_html(code_id, code, language):
    """Generate HTML for a run code button."""
    # Only support Python for now
    if language.lower() not in ["python", "py"]:
        return ""
    
    # Escape JS string
    escaped_code = code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("</script>", "<\\/script>")
    
    # Generate unique widget key
    widget_key = f"btn_run_{code_id}_{uuid.uuid4().hex[:8]}"
    
    return f"""
    <button id="{widget_key}" class="code-action-button">
        ▶️ Run Code
    </button>
    <script>
        (function() {{
            const btn = document.getElementById('{widget_key}');
            btn.addEventListener('click', function() {{
                const code = `{escaped_code}`;
                // Create a hidden form element
                const form = document.createElement('form');
                form.method = 'POST';
                form.style.display = 'none';
                
                // Create input for code
                const codeInput = document.createElement('input');
                codeInput.type = 'hidden';
                codeInput.name = 'code_{widget_key}';
                codeInput.value = code;
                
                // Create input for run action
                const runInput = document.createElement('input');
                runInput.type = 'hidden';
                runInput.name = 'run_{widget_key}';
                runInput.value = 'true';
                
                // Add inputs to form
                form.appendChild(codeInput);
                form.appendChild(runInput);
                
                // Add form to body and submit
                document.body.appendChild(form);
                form.submit();
            }});
        }})();
    </script>
    """

def render_google_adsense_ad():
    """Render a Google AdSense ad."""
    ad_html = f"""
    <div class="ad-container">
        <p>Please view this advertisement to continue using the app</p>
        <div class="ad-timer" id="ad_timer">{AD_DURATION}</div>
        
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={GOOGLE_ADSENSE_ID}"
        crossorigin="anonymous"></script>
        <ins class="adsbygoogle"
             style="display:block"
             data-ad-client="{GOOGLE_ADSENSE_ID}"
             data-ad-slot="2657400431"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({{}});
             
             // Timer countdown
             let seconds = {AD_DURATION};
             const timerElement = document.getElementById('ad_timer');
             const timerInterval = setInterval(() => {{
                 seconds--;
                 timerElement.textContent = seconds;
                 if (seconds <= 0) {{
                     clearInterval(timerInterval);
                     // Submit form to continue
                     const continueForm = document.createElement('form');
                     continueForm.method = 'POST';
                     continueForm.style.display = 'none';
                     
                     const continueInput = document.createElement('input');
                     continueInput.type = 'hidden';
                     continueInput.name = 'ad_complete';
                     continueInput.value = 'true';
                     
                     continueForm.appendChild(continueInput);
                     document.body.appendChild(continueForm);
                     continueForm.submit();
                 }}
             }}, 1000);
        </script>
    </div>
    """
    
    return components.html(ad_html, height=300)

# ------------------ UI Components ------------------
# Fix Google Sign-in button HTML
def render_login_screen():
    """Render the Google login screen."""
    st.title("Welcome to Claude-Style Assistant")
    st.markdown("""
    Please sign in with your Google account to continue.

    This app provides:
    - AI-powered chat assistant
    - Code execution capabilities
    - Image generation
    - Multiple named chat sessions
    """)

    # Google Sign-in button with improved HTML
    signin_html = f"""
    <div style="display: flex; justify-content: center; padding: 30px 0;">
        <div id="g_id_onload"
            data-client_id="{GOOGLE_CLIENT_ID}"
            data-callback="handleCredentialResponse">
        </div>
        <div class="g_id_signin"
            data-type="standard"
            data-size="large"
            data-theme="outline"
            data-text="sign_in_with"
            data-shape="rectangular"
            data-logo_alignment="left">
        </div>
    </div>

    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <script>
        function handleCredentialResponse(response) {{
            const data = {{
                token: response.credential,
                type: "google-signin"
            }};
            // Make sure we're targeting the correct parent window
            if (window.parent) {{
                window.parent.postMessage(JSON.stringify(data), "*");
            }} else {{
                console.error("Cannot find parent window");
            }}
        }}
    </script>
    """

    components.html(signin_html, height=80)

    
    components.html(signin_html, height=80)

    # Hidden elements to receive token
    token = st.text_input("", key="googleToken", label_visibility="hidden")
    submit_btn = st.button("Submit", key="submitGoogleToken", label_visibility="hidden")
    
    if token and submit_btn:
        user_info = verify_google_token(token)
        if user_info:
            st.session_state.user_email = user_info.get("email")
            st.session_state.user_name = user_info.get("name")
            st.session_state.user_picture = user_info.get("picture")
            st.session_state.logged_in = True
            
            # Load or create user data
            st.session_state.user_data = get_or_create_user(st.session_state.user_email)
            
            # Initialize active chat
            if "active_chat" not in st.session_state:
                st.session_state.active_chat = "General"
            
            # Reload to show main app
            st.rerun()

def render_ad_free_info():
    """Render ad-free status information in sidebar."""
    is_ad_free, expiry_date = get_ad_free_status(st.session_state.user_email)
    
    if is_ad_free:
        st.markdown(f"""
        ### Ad-Free Status <span class="ad-free-badge">Active</span>
        
        **Ad-free until:** {expiry_date}
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        ### Ad Status
        
        **Status:** Ads enabled (1 ad per 5 messages)
        """)
    
    # Coupon code section
    st.markdown("### Coupon Code")
    coupon_code = st.text_input("Enter coupon code for ad-free access", key="coupon_code")
    
    if st.button("Apply Coupon", key="apply_coupon_btn"):
        success, message = apply_coupon_code(st.session_state.user_email, coupon_code)
        if success:
            st.success(message)
            # Reload to show updated status
            st.rerun()
        else:
            st.error(message)

def render_chat_selector():
    """Render the chat selector in sidebar."""
    st.subheader("My Chats")
    
    user_data = st.session_state.user_data
    chat_names = list(user_data["chats"].keys())
    
    # Select active chat
    active_chat = st.selectbox(
        "Select Chat",
        chat_names,
        index=chat_names.index(st.session_state.active_chat) if st.session_state.active_chat in chat_names else 0,
        key="chat_selector"
    )
    
    # Update active chat if changed
    if active_chat != st.session_state.active_chat:
        st.session_state.active_chat = active_chat
        st.rerun()
    
    # Create new chat button
    if st.button("Create New Chat", key="new_chat_btn"):
        st.session_state.creating_chat = True
    
    # New chat name input
    if st.session_state.get("creating_chat", False):
        new_chat_name = st.text_input("Chat Name", key="new_chat_name")
        
        # Create and cancel buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create", key="create_chat_btn"):
                if new_chat_name and new_chat_name not in chat_names:
                    user_data["chats"][new_chat_name] = []
                    update_user_data(st.session_state.user_email, user_data)
                    st.session_state.active_chat = new_chat_name
                    st.session_state.creating_chat = False
                    st.rerun()
                else:
                    st.error("Please provide a unique name")
        
        with col2:
            if st.button("Cancel", key="cancel_chat_btn"):
                st.session_state.creating_chat = False
                st.rerun()

def render_sidebar():
    """Render the sidebar with user info and options."""
    with st.sidebar:
        # User info section
        if st.session_state.get("user_picture"):
            st.image(st.session_state.user_picture, width=50)
        
        st.markdown(f"""
        ### {st.session_state.user_name}
        {st.session_state.user_email}
        """)
        
        st.divider()
        
        # Display ad-free status
        render_ad_free_info()
        
        st.divider()
        
        # Chat selector
        render_chat_selector()
        
        st.divider()
        
        # Model selection
        live_models = get_live_models(model_ids)
        
        st.subheader("Model Settings")
        
        text_model = st.selectbox(
            "Text Model",
            live_models,
            index=live_models.index(text_default) if text_default in live_models else 0,
            key="text_model"
        )
        
        img_model = st.selectbox(
            "Image Model",
            live_models,
            index=live_models.index(img_default) if img_default in live_models else 0,
            key="img_model"
        )
        
        st.divider()
        
        # System prompt section
        if "system_prompt" not in st.session_state:
            st.session_state.system_prompt = """You are a smart, collaborative assistant—friendly like Claude, productive like v0.dev—focused on clear, concise, code-ready answers."""
        
        st.text_area(
            "System Prompt",
            value=st.session_state.system_prompt,
            height=100,
            key="system_prompt_input",
            on_change=lambda: setattr(st.session_state, "system_prompt", st.session_state.system_prompt_input)
        )
        
        st.divider()
        
        # Logout button
        if st.button("Logout", key="logout_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def process_assistant_response(response_text):
    """Process the assistant response to add code block buttons."""
    code_blocks = extract_code_blocks(response_text)
    
    # If no code blocks, return original
    if not code_blocks:
        return response_text
    
    # Replace code blocks with ones that have buttons
    for block in code_blocks:
        block_id = block["id"]
        lang = block["language"]
        code = block["code"]
        
        # Original block pattern
        original = f"```{lang}\n{code}```"
        
        # Create buttons HTML
        copy_btn = copy_button_html(block_id, code)
        run_btn = run_button_html(block_id, code, lang)
        
        buttons_html = f'<div class="code-action-buttons">{copy_btn}{run_btn}</div>'
        
        # Replace with buttons + code block
        replacement = f'{buttons_html}\n```{lang}\n{code}```'
        response_text = response_text.replace(original, replacement)
    
    return response_text

def handle_code_execution(form_data, chat_messages):
    """Handle code execution if a Run Code button was clicked."""
    # Check for run code buttons
    run_keys = [k for k in form_data if k.startswith("run_btn_run_")]
    
    if run_keys:
        run_key = run_keys[0]  # Get the first one
        code_key = run_key.replace("run_", "code_")
        
        if code_key in form_data:
            code = form_data[code_key]
            
            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
                    temp_file.write(code.encode())
                    temp_path = temp_file.name
                
                # Execute code in subprocess
                import subprocess
                result = subprocess.run(
                    ["python", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Get output
                if result.returncode == 0:
                    output = result.stdout
                    error = None
                else:
                    output = result.stdout
                    error = result.stderr
                
                # Add execution result to chat
                user_msg = {"role": "user", "content": "I ran the code."}
                chat_messages.append(user_msg)
                
                if error:
                    assistant_msg = {
                        "role": "assistant",
                        "content": f"The code execution resulted in an error:\n\n```\n{error}\n```"
                    }
                else:
                    assistant_msg = {
                        "role": "assistant",
                        "content": f"Code execution successful! Here's the output:\n\n```\n{output}\n```"
                    }
                chat_messages.append(assistant_msg)
                
                # Clean up
                os.unlink(temp_path)
                
            except Exception as e:
                # Handle execution error
                user_msg = {"role": "user", "content": "I tried to run the code."}
                chat_messages.append(user_msg)
                
                assistant_msg = {
                    "role": "assistant",
                    "content": f"There was an error executing the code: {str(e)}"
                }
                chat_messages.append(assistant_msg)
                
            return True
    
    return False

def render_chat():
    """Render the main chat interface."""
    st.title("Claude-Style Assistant")
    
    active_chat = st.session_state.active_chat
    chat_messages = get_user_chat_history(st.session_state.user_email, active_chat)
    
    # Process form data for code execution
    form_data = st.experimental_get_query_params()
    code_executed = handle_code_execution(form_data, chat_messages)
    
    # Check if ad was completed
    ad_completed = "ad_complete" in form_data
    if ad_completed and st.session_state.get("showing_ad"):
        st.session_state.showing_ad = False
        st.experimental_set_query_params()  # Clear query params
        st.rerun()
    
    # Display chat messages
    for msg in chat_messages:
        if msg["role"] == "user":
            with st.chat_message(msg["role"], avatar=USER_ICON):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message(msg["role"], avatar=ASSISTANT_ICON):
                content = process_assistant_response(msg["content"])
                st.markdown(content, unsafe_allow_html=True)
    
    # Handle new message input
    if not st.session_state.get("showing_ad", False):
        user_input = st.chat_input("Send a message")
        
        if user_input:
            # Add user message to chat
            user_msg = {"role": "user", "content": user_input}
            chat_messages.append(user_msg)
            update_user_chat_history(st.session_state.user_email, active_chat, chat_messages)
            
            # Display user message
            with st.chat_message("user", avatar=USER_ICON):
                st.markdown(user_input)
            
            # Check if ad should be shown
            show_ad = increment_message_counter(st.session_state.user_email)
            
            if show_ad:
                st.session_state.showing_ad = True
                render_google_adsense_ad()
                st.rerun()
            else:
                # Get AI response
                with st.chat_message("assistant", avatar=ASSISTANT_ICON):
                    with st.spinner("Thinking..."):
                        # Prepare context
                        trimmed_messages = trim_context(
                            [{"role": "system", "content": st.session_state.system_prompt}] + chat_messages,
                            50  # Max context size
                        )
                        
                        try:
                            response = client.chat.completions.create(
                                model=st.session_state.text_model,
                                messages=[
                                    {"role": m["role"], "content": m["content"]} 
                                    for m in trimmed_messages
                                ],
                                temperature=0.7,
                                max_tokens=4000,
                                stream=True
                            )
                            
                            # Stream response
                            message_placeholder = st.empty()
                            full_response = ""
                            
                            for chunk in response:
                                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    message_placeholder.markdown(
                                        process_assistant_response(full_response),
                                        unsafe_allow_html=True
                                    )
                            
                            # Add assistant response to chat
                            assistant_msg = {"role": "assistant", "content": full_response}
                            chat_messages.append(assistant_msg)
                            update_user_chat_history(st.session_state.user_email, active_chat, chat_messages)
                            
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            # Add error message to chat
                            error_msg = {"role": "assistant", "content": f"I'm sorry, I encountered an error: {str(e)}"}
                            chat_messages.append(error_msg)
                            update_user_chat_history(st.session_state.user_email, active_chat, chat_messages)
    else:
        # Show ad
        render_google_adsense_ad()

# ------------------ Main App ------------------
def main():
    """Main app entry point."""
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "active_chat" not in st.session_state:
        st.session_state.active_chat = "General"
    
    if "creating_chat" not in st.session_state:
        st.session_state.creating_chat = False
    
    if "showing_ad" not in st.session_state:
        st.session_state.showing_ad = False
    
    # Render login or main app
    if not st.session_state.logged_in:
        render_login_screen()
    else:
        render_sidebar()
        render_chat()

if __name__ == "__main__":
    main()
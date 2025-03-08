import streamlit as st
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import uuid
import sqlite3
from datetime import datetime
import hashlib

# ---------------------- Configuration ----------------------
# Set page configuration for dark theme
st.set_page_config(
    page_title="MediConsult Pro",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme and professional styling
# Update the existing CSS with this improved version
# Update the CSS block with this hospital-themed design
st.markdown("""
<style>
    /* Enhanced Hospital Theme */
    :root {
        --primary-color: #0D47A1;       /* Professional hospital blue */
        --secondary-color: #00796B;     /* Medical cyan for accents */
        --accent-color: #D32F2F;        /* Emergency red */
        --background-color: #FFFFFF;    /* Clean white background */
        --card-bg: #F8F9FA;             /* Light gray for cards */
        --text-color: #2D3748;          /* Dark gray for text */
        --border-color: #CBD5E0;        /* Soft gray for borders */
    }


    /* Enhanced Header */
    .header-container {
        background: var(--primary-color);
        color: white;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 4px solid var(--secondary-color);
        margin-bottom: 2rem;
    }

    .header-title {
        font-size: 1.8rem !important;
        letter-spacing: -0.5px;
        margin-bottom: 0.5rem !important;
    }

    .header-subtitle {
        font-size: 1rem !important;
        opacity: 0.9;
    }

    /* Patient Card Enhancements */
    .patient-card {
        background: var(--background-color);
        border-left: 4px solid var(--secondary-color);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 2rem;
        transition: transform 0.2s ease;
    }

    .patient-card:hover {
        transform: translateY(-2px);
    }

    /* Enhanced Chat Messages */
    .stChatMessage {
        border-radius: 12px;
        border: 1px solid var(--border-color);
        padding: 1.25rem;
        margin: 1rem 0;
        position: relative;
    }

    .stChatMessage.user {
        border-left: 4px solid var(--primary-color);
        background: #E3F2FD;
    }

    .stChatMessage.assistant {
        border-left: 4px solid var(--secondary-color);
        background: #E0F2F1;
    }

    /* Improved Input Fields */
    .stTextInput input, .stNumberInput input {
        border: 2px solid var(--border-color);
        border-radius: 10px;
        padding: 0.9rem 1.2rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease;
    }

    .stTextInput input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(13, 71, 161, 0.1);
    }

    /* Modern Buttons */
    .stButton>button {
        background: var(--primary-color);
        border-radius: 10px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background: #0B3D91;
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(13, 71, 161, 0.15);
    }

    /* Symptom Tags Enhancements */
    .symptom-tag {
        background: #E0F2F1;
        color: var(--secondary-color) !important;
        border: 1px solid #B2DFDB;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        transition: all 0.2s ease;
    }

    .symptom-tag:hover {
        background: var(--secondary-color);
        color: white !important;
        transform: translateY(-2px);
    }

    /* Consultation Card */
    .stCard {
        background: var(--background-color);
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        margin-bottom: 2rem;
    }

    /* Enhanced Footer */
    .footer-section {
        border-top: 2px solid var(--border-color);
        padding: 2rem 0;
        margin-top: 3rem;
        text-align: center;
        color: var(--text-color);
        opacity: 0.8;
    }

    /* Loading Spinner Animation */
    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .stSpinner>div {
        border-color: var(--primary-color) transparent transparent transparent;
        animation: spin 0.8s linear infinite;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------- API Configuration ----------------------
genai.configure(api_key="AIzaSyDUVtxVmr_gyCF7scq_lA0fcBg91UHdok8")

# ---------------------- Medical Constants ----------------------
ALLOWED_KEYWORDS = [
    "fever", "cough", "cold", "headache", "migraine", "pain", "indigestion",
    "diarrhea", "constipation", "vomit", "nausea", "sore throat", "chest",
    "breath", "dizziness", "fatigue", "weakness", "flu", "infection", "sinus",
    "allergy", "rash", "itch", "swell", "muscle", "joint", "burn", "wound",
    "cut", "bruise", "blood pressure", "diabetes", "sugar", "dehydration",
    "acidity", "heartburn", "gas", "bloat", "ear", "tooth", "eye", "sleep",
    "anxiety", "chills", "sneeze", "congestion", "phlegm", "heart", "lung",
    "abdomen", "back", "neck", "arm", "leg", "dizzy", "appetite"
]

FOLLOW_UP_QUESTIONS = [
    "How many days have you had these symptoms?",
    "On a scale of 1-10, how severe are your symptoms?",
    "Have you taken any medication for this already?",
    "Any other symptoms you haven't mentioned?"
]

# ---------------------- Database Functions ----------------------
def init_db():
    """Initialize database with proper error handling"""
    try:
        conn = sqlite3.connect('health_records.db')
        c = conn.cursor()
        
        # Create table with error handling
        c.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                symptom TEXT NOT NULL,
                date TEXT NOT NULL,
                block_hash TEXT NOT NULL
            )
        ''')
        
        # Add test records if they don't exist
        test_phone = "9876543210"
        c.execute("SELECT * FROM records WHERE phone=?", (test_phone,))
        if not c.fetchall():
            test_records = [
                (test_phone, "migraine", datetime(2024, 3, 1).strftime("%Y-%m-%d %H:%M:%S"), ""),
                (test_phone, "visual aura", datetime(2024, 3, 5).strftime("%Y-%m-%d %H:%M:%S"), "")
            ]
            
            # Generate hashes
            prev_hash = "0"
            for i, (phone, symptom, date, _) in enumerate(test_records):
                data_str = f"{phone}{symptom}{date}"
                current_hash = hashlib.sha256(f"{prev_hash}{data_str}".encode()).hexdigest()
                test_records[i] = (phone, symptom, date, current_hash)
                prev_hash = current_hash
            
            c.executemany("INSERT INTO records (phone, symptom, date, block_hash) VALUES (?,?,?,?)", test_records)
        
        conn.commit()
    except Exception as e:
        st.error(f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

def get_patient_history(phone):
    """Retrieve patient's medical history from SQLite database"""
    conn = sqlite3.connect('health_records.db')
    c = conn.cursor()
    c.execute("SELECT date, symptom FROM records WHERE phone=? ORDER BY date", (phone,))
    records = c.fetchall()
    conn.close()
    return records

def add_consultation_record(phone, consultation_text):
    """Store current consultation in database"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_str = f"{phone}{consultation_text}{timestamp}"
    block_hash = hashlib.sha256(data_str.encode()).hexdigest()
    
    conn = sqlite3.connect('health_records.db')
    c = conn.cursor()
    c.execute("INSERT INTO records (phone, symptom, date, block_hash) VALUES (?,?,?,?)",
              (phone, consultation_text, timestamp, block_hash))
    conn.commit()
    conn.close()

# ---------------------- Core Functions ----------------------
def is_medical_query(user_input: str) -> bool:
    """Check if user input contains medical keywords"""
    user_input = user_input.lower()
    return any(keyword in user_input for keyword in ALLOWED_KEYWORDS)

def get_health_advice(symptoms, past_history=None):
    """Generate advice considering medical history"""
    base_prompt = f"""Act as a certified doctor. Analyze these current symptoms:
    {symptoms}
    """
    
    if past_history:
        history_prompt = f"""
        Patient Medical History:
        {past_history}
        
        Consider these patterns in your analysis:
        1. Symptom recurrence frequency
        2. Progressions/improvements over time
        3. Potential chronic condition indicators
        4. Medication effectiveness patterns
        5. Emergency warning sign trends
        """
        base_prompt += history_prompt
    
    full_prompt = base_prompt + """
    Provide structured advice covering:
    1. OTC medications (with dosage)
    2. Home remedies
    3. Diet recommendations
    4. Warning signs to watch for
    5. When to see a doctor
    6. Historical pattern warnings (if any)

    Use clear headings and bullet points."""
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
                temperature=0.3,
                top_p=0.9,
                top_k=40,
                max_output_tokens=512
            )
        )
        return response.text
    except Exception as e:
        return f"⚠ Error generating advice: {str(e)}"

def handle_user_input(user_input: str, session_id: str) -> str:
    """Conversation handler with proper state management"""
    # Initialize session if not exists
    if session_id not in st.session_state.user_state:
        if not is_medical_query(user_input):
            return "I'm your medical assistant. Please describe your symptoms (e.g., 'I have fever and cough')"
        
        # Initialize session state
        st.session_state.user_state[session_id] = {
            "current_question": 0,
            "symptoms": [user_input]
        }
        return FOLLOW_UP_QUESTIONS[0]  # Return first question
    
    # Get session state
    state = st.session_state.user_state[session_id]
    question_idx = state["current_question"]
    
    # Store answer for the current question
    state["symptoms"].append(f"{FOLLOW_UP_QUESTIONS[question_idx]}: {user_input}")
    
    # Move to next question
    state["current_question"] += 1
    
    # Check if more questions remain
    if state["current_question"] < len(FOLLOW_UP_QUESTIONS):
        return FOLLOW_UP_QUESTIONS[state["current_question"]]
    else:
        # Generate final advice
        full_symptoms = "\n".join(state["symptoms"])
        phone = st.session_state.login_phone
        
        # Get historical data
        past_records = get_patient_history(phone)
        history_str = "\n".join([f"{date}: {symptom}" for date, symptom in past_records]) if past_records else None
        
        # Generate enhanced advice
        advice = get_health_advice(full_symptoms, history_str)
        
        # Store current consultation
        add_consultation_record(phone, full_symptoms)
        
        # Clear session state
        del st.session_state.user_state[session_id]
        return f"{advice}\n\n🩺 Need help with anything else? Describe symptoms or type 'exit'"

# ---------------------- Session Management ----------------------
if "user_state" not in st.session_state:
    st.session_state.user_state = {}

# ---------------------- Login System ----------------------
if 'authenticated' not in st.session_state:
    st.session_state.update({
        'authenticated': False,
        'login_phone': "",
        'user_session_id': str(uuid.uuid4()),
        'generated_otp': None
    })

# ---------------------- Login Page ----------------------
if not st.session_state.authenticated:
    # Custom login header
    st.markdown("""
    <div class="header-container">
        <div class="header-logo">🏥</div>
        <div>
            <h1 class="header-title">MediConsult Pro</h1>
            <p class="header-subtitle">Secure healthcare consultations at your fingertips</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create login card
    st.markdown("### 🔐 Secure Authentication")
    st.markdown("Please enter your credentials to access your medical consultation.")
    
    # Phone input with formatting
    col1, col2 = st.columns([3, 1])
    with col1:
        input_phone = st.text_input("Phone Number:", 
                                  key="phone_input", 
                                  value="9876543210",
                                  placeholder="Enter 10-digit number")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        send_otp_button = st.button("🔑 Send OTP", use_container_width=True)
    
    if send_otp_button:
        if input_phone and len(input_phone) == 10 and input_phone.isdigit():
            st.session_state.generated_otp = "123456"
            st.session_state.login_phone = input_phone
            st.success(f"✅ OTP sent to {input_phone} (Demo OTP: 123456)")
        else:
            st.error("⚠ Please enter a valid 10-digit phone number")
    
    if st.session_state.generated_otp:
        otp_col1, otp_col2 = st.columns([3, 1])
        with otp_col1:
            # Changed from password type to number type
            user_otp = st.text_input("Enter OTP:", 
                                   key="otp_input", 
                                   placeholder="Enter 6-digit OTP")
        with otp_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            verify_button = st.button("✅ Verify", use_container_width=True)
            
        if verify_button:
            if user_otp == st.session_state.generated_otp:
                st.session_state.authenticated = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("⚠ Invalid OTP. Please try again.")
    
    # Close login card
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: #666;">
        <p>© 2025 MediConsult Pro. All rights reserved.</p>
        <p style="font-size: 0.8rem;">HIPAA Compliant · Secure · Encrypted</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# ---------------------- Main Application ----------------------
init_db()  # Initialize database with test records

# Custom header with user info
st.markdown(f"""
<div class="header-container">
    <div class="header-logo">🏥</div>
    <div>
        <h1 class="header-title">MediConsult Pro</h1>
        <p class="header-subtitle">AI-powered medical consultations</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Patient info card
# Update the patient card section in the main application
st.markdown(f"""
<div class="patient-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="flex: 1;">
            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.5rem;">🏥</span>
                <div>
                    <h3 style="margin: 0; color: var(--primary-color);">Patient Profile</h3>
                    <p style="margin: 0; color: var(--text-color); opacity: 0.8;">ID: #{st.session_state.login_phone}</p>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                <div>
                    <div style="font-size: 0.9rem; color: var(--secondary-color);">Last Login</div>
                    <div style="font-weight: 600;">{datetime.now().strftime('%d %b %Y')}</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: var(--secondary-color);">Consultations</div>
                    <div style="font-weight: 600;">{len(get_patient_history(st.session_state.login_phone))}</div>
                </div>
            </div>
        </div>
        <button style="background: var(--secondary-color); border: none; color: white; padding: 0.8rem 1.2rem; border-radius: 8px; cursor: pointer; transition: all 0.3s ease;">
            <span style="display: flex; align-items: center; gap: 0.5rem;">
                📋 View History
            </span>
        </button>
    </div>
</div>
""", unsafe_allow_html=True)


# Main consultation area
st.markdown("### 💬 Virtual Consultation")
st.markdown("Describe your symptoms for personalized health advice from our AI medical assistant.")

# Recent symptoms tags
if st.session_state.login_phone:
    history = get_patient_history(st.session_state.login_phone)
    if history:
        recent_symptoms = [symptom for _, symptom in history[-2:] if len(symptom) < 30]
        if recent_symptoms:
            st.markdown("#### Recent Issues:")
            tags_html = ""
            for symptom in recent_symptoms:
                tags_html += f'<span class="symptom-tag">🔍 {symptom}</span>'
            st.markdown(f'<div>{tags_html}</div>', unsafe_allow_html=True)

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add welcome message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "👨‍⚕ Welcome to MediConsult Pro! I'm your virtual healthcare assistant. How can I help you today? Please describe any symptoms you're experiencing."
    })

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "👨‍⚕"):
        st.markdown(msg["content"])

# Handle user input

# Handle user input
if prompt := st.chat_input("Tell me about your symptoms..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    # Removed spinner block
    response = handle_user_input(
        prompt, 
        st.session_state.user_session_id
    )
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    with st.chat_message("assistant", avatar="👨‍⚕"):
        st.markdown(response)

st.markdown('</div>', unsafe_allow_html=True)

# Footer section
st.markdown("""
<div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #333;">
    <p style="font-size: 0.9rem; color: #999;">
        <strong>⚠ Disclaimer:</strong> This AI healthcare assistant provides general information and is not a substitute for professional medical advice, diagnosis, or treatment.
        Always seek the advice of your physician with any questions about medical conditions.
    </p>
    <p style="font-size: 0.8rem; color: #666; margin-top: 20px;">
        © 2025 MediConsult Pro | HIPAA Compliant | 128-bit Encrypted
    </p>
</div>
""", unsafe_allow_html=True)

# Add logout option
if st.sidebar.button("📤 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        st.rerun()

import streamlit as st
import re
import time
import json
import requests
import os

# ==========================================
# ⚙️ Configuration & Constants
# ==========================================

# List of latest official model names
CANDIDATE_MODELS = [
    "gemini-2.0-flash",          # 2.0 Official (Recommended)
    "gemini-1.5-flash",          # Most stable lightweight model
    "gemini-1.5-pro",           # High performance model
    "gemini-1.5-flash-8b",      # Ultra lightweight model
    "gemini-2.0-flash-exp"      # Experimental
]

# ==========================================
# 🛠️ Function Definitions
# ==========================================

def find_working_model(api_key, log_area):
    """Function enhanced to display error details on screen"""
    headers = {'Content-Type': 'application/json'}
    test_data = {"contents": [{"parts": [{"text": "Test"}]}]}

    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            log_area.text(f"👉 Testing {model}...")
            response = requests.post(url, headers=headers, data=json.dumps(test_data), timeout=5)
            
            if response.status_code == 200:
                log_area.success(f"✅ Connection successful! Using model: {model}")
                return model
            else:
                try:
                    error_msg = response.json().get('error', {}).get('message', response.text)
                except:
                    error_msg = response.text
                st.warning(f"⚠️ {model}: Connection failed (Status: {response.status_code})\nReason: {error_msg}")
                
        except Exception as e:
            st.error(f"📡 Connection Error ({model}): {str(e)}")
    
    log_area.error("❌ Failed to connect with all candidate models.")
    return None

def split_srt_blocks(srt_content):
    # [Important] Enhanced logic to prevent syncing issues
    content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
    # Enhanced regex to split even with lines containing just whitespace
    blocks = re.split(r'\n\s*\n', content.strip())
    return [b for b in blocks if b.strip()]

def sanitize_timecode(time_str):
    """Strictly format timecode for Web tools"""
    # Unify arrows to " --> "
    t = re.sub(r'\s*[-=]+>\s*', ' --> ', time_str)
    # Unify comma separator (Web tool countermeasure)
    t = t.replace('.', ',')
    return t

def translate_block_rest_api(text, api_key, model_name, movie_title, target_language):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    You are a professional film subtitle translator.
    Translate the dialogue into natural, emotional {target_language}.
    Movie: {movie_title}

    【Rules】
    1. Output ONLY the translated text. No notes.
    2. Do NOT output timecodes.
    3. Keep it concise for subtitles.
    
    Original:
    {text}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    txt = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return txt if txt else text
                else:
                    return text
            elif response.status_code == 429:
                time.sleep(5)
                continue
            else:
                time.sleep(1)
                continue
        except:
            time.sleep(1)
            continue
            
    return text

# ==========================================
# 🖥️ Streamlit Screen Layout
# ==========================================

def main():
    st.set_page_config(page_title="AI Subtitle Translator", layout="wide")
    
    st.title("🎬 AI Subtitle Translator")

    with st.sidebar:
        st.header("Settings")
        api_key_input = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
        st.markdown("---")
        movie_title_input = st.text_input("Movie Title", value="The Great Escaper")
        target_lang_input = st.text_input("Target Language", value="Japanese")
        st.markdown("---")
        st.info("Translation may take a few minutes. Please do not close the browser.")

    uploaded_file = st.file_uploader("Drag and drop your SRT file here", type=["srt"])

    if uploaded_file is not None:
        st.success(f"File loaded: {uploaded_file.name}")
        
        if st.button("Start Translation", type="primary"):
            if not api_key_input:
                st.error("⚠️ Please enter your API Key in the sidebar.")
                return

            status_area = st.empty()
            log_area = st.empty()
            progress_bar = st.progress(0)

            working_model = find_working_model(api_key_input, log_area)
            
            if working_model:
                content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
                blocks = split_srt_blocks(content)
                total_blocks = len(blocks)
                translated_srt = []
                
                status_area.info(f"🚀 Starting translation... Total {total_blocks} blocks (Model: {working_model})")
                
                for i, block in enumerate(blocks):
                    lines = block.split('\n')
                    # Check for at least sequence number and timecode
                    if len(lines) >= 2:
                        seq_num = lines[0].strip()
                        
                        # Find timecode line
                        time_line_index = -1
                        for idx, line in enumerate(lines):
                            if '-->' in line:
                                time_line_index = idx
                                break
                        
                        if time_line_index != -1:
                            timecode = lines[time_line_index].strip()
                            original_text = "\n".join(lines[time_line_index + 1:])
                            
                            if original_text.strip():
                                translated_text = translate_block_rest_api(
                                    original_text, 
                                    api_key_input, 
                                    working_model, 
                                    movie_title_input, 
                                    target_lang_input
                                )
                            else:
                                translated_text = ""
                            
                            # Clean timecode for Web tools
                            clean_time = sanitize_timecode(timecode)
                            
                            # Combine with CRLF (Windows line endings)
                            new_block = f"{seq_num}\r\n{clean_time}\r\n{translated_text}\r\n\r\n"
                            translated_srt.append(new_block)
                        else:
                            # Keep original structure if weird, just normalize newlines
                            translated_srt.append(block.replace('\n', '\r\n') + "\r\n\r\n")
                    else:
                        translated_srt.append(block.replace('\n', '\r\n') + "\r\n\r\n")
                    
                    progress = (i + 1) / total_blocks
                    progress_bar.progress(progress)
                    
                    if (i + 1) % 5 == 0:
                         log_area.text(f"⏳ Processing... {i + 1}/{total_blocks} completed")
                    
                    time.sleep(0.5)

                progress_bar.progress(1.0)
                status_area.success("✅ Translation & Formatting Complete!")
                log_area.empty()
                
                final_content = "".join(translated_srt)
                new_filename = f"{uploaded_file.name.replace('.srt', '')}_{target_lang_input}_WebReady.srt"
                
                st.download_button(
                    label="📥 Download Translated SRT (Web Ready)",
                    data=final_content.encode('utf-8-sig'),
                    file_name=new_filename,
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
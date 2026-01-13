import streamlit as st
import re
import time
import json
import requests
import os

# ==========================================
# ⚙️ 設定・定数定義
# ==========================================

# 最新の正式なモデル名リストに更新しました
CANDIDATE_MODELS = [
    "gemini-2.0-flash",          # 2.0の正式版（おすすめ）
    "gemini-1.5-flash",          # 最も安定して動く軽量モデル
    "gemini-1.5-pro",           # 高性能モデル
    "gemini-1.5-flash-8b",      # 超軽量モデル
    "gemini-2.0-flash-exp"      # 実験用（混雑時はエラーになりやすい）
]

# ==========================================
# 🛠️ 関数定義
# ==========================================

def find_working_model(api_key, log_area):
    """エラーの詳細を画面に表示するように強化した関数"""
    headers = {'Content-Type': 'application/json'}
    test_data = {"contents": [{"parts": [{"text": "Test"}]}]}

    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            log_area.text(f"👉 {model} をテスト中...")
            response = requests.post(url, headers=headers, data=json.dumps(test_data), timeout=5)
            
            if response.status_code == 200:
                log_area.success(f"✅ 接続成功！モデル: {model} を使用します。")
                return model
            else:
                # ❌ ここでエラーの具体的な理由を取得して表示する
                try:
                    error_msg = response.json().get('error', {}).get('message', response.text)
                except:
                    error_msg = response.text
                
                # 画面に警告として理由を出す
                st.warning(f"⚠️ {model}: 接続失敗 (Status: {response.status_code})\n理由: {error_msg}")
                
        except Exception as e:
            st.error(f"📡 通信エラー ({model}): {str(e)}")
    
    log_area.error("❌ 全ての候補モデルで接続に失敗しました。")
    return None

def split_srt_blocks(srt_content):
    content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n\n+', content.strip())
    return [b for b in blocks if b.strip()]

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
# 🖥️ Streamlit 画面構成
# ==========================================

def main():
    st.set_page_config(page_title="AI Subtitle Translator", layout="wide")
    
    st.title("🎬 AI 字幕翻訳ツール (Gemini 3.0対応)")
    st.markdown("SRTファイルをアップロードして、最新のGeminiで自然な翻訳を行います。")

    with st.sidebar:
        st.header("設定")
        api_key_input = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
        st.markdown("---")
        movie_title_input = st.text_input("映画のタイトル", value="The Great Escaper")
        target_lang_input = st.text_input("翻訳先の言語", value="日本語")
        st.markdown("---")
        st.info("翻訳には数分かかる場合があります。ブラウザを閉じないでください。")

    uploaded_file = st.file_uploader("SRTファイルをドラッグ＆ドロップしてください", type=["srt"])

    if uploaded_file is not None:
        st.success(f"ファイル読み込み完了: {uploaded_file.name}")
        
        if st.button("翻訳開始", type="primary"):
            if not api_key_input:
                st.error("⚠️ 左のサイドバーでAPIキーを入力してください。")
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
                
                status_area.info(f"🚀 翻訳開始... 全 {total_blocks} ブロック (モデル: {working_model})")
                
                for i, block in enumerate(blocks):
                    lines = block.split('\n')
                    if len(lines) >= 3:
                        seq_num = lines[0]
                        timecode = lines[1]
                        original_text = "\n".join(lines[2:])
                        
                        translated_text = translate_block_rest_api(
                            original_text, 
                            api_key_input, 
                            working_model, 
                            movie_title_input, 
                            target_lang_input
                        )
                        
                        new_block = f"{seq_num}\n{timecode}\n{translated_text}\n"
                        translated_srt.append(new_block)
                    else:
                        translated_srt.append(block + "\n")
                    
                    progress = (i + 1) / total_blocks
                    progress_bar.progress(progress)
                    
                    if (i + 1) % 5 == 0:
                         log_area.text(f"⏳ 処理中... {i + 1}/{total_blocks} 完了")
                    
                    time.sleep(0.5) # 最新モデルは高速なため待機時間を少し短縮

                progress_bar.progress(1.0)
                status_area.success("✅ 翻訳完了！")
                log_area.empty()
                
                final_content = "\n".join(translated_srt)
                new_filename = f"{uploaded_file.name.replace('.srt', '')}_{target_lang_input}_v3.srt"
                
                st.download_button(
                    label="📥 翻訳されたSRTをダウンロード",
                    data=final_content,
                    file_name=new_filename,
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
import streamlit as st
import re

def convert_to_web_friendly(content):
    """
    Webツールで読み込めるように「BOM付きUTF-8」かつ「CRLF改行」に変換する
    """
    # 1. 改行を一度すべて \n に統一
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # 2. 余計な空白やマークダウンを削除
    content = re.sub(r'```(?:srt)?', '', content)
    content = re.sub(r'```', '', content)

    # 3. ブロックを再構築（厳密なフォーマットにする）
    # 空行区切りで分割
    blocks = re.split(r'\n\s*\n', content.strip())
    
    formatted_blocks = []
    counter = 1
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            # タイムコード行を探す
            time_line_index = -1
            for i, line in enumerate(lines):
                if '-->' in line:
                    time_line_index = i
                    break
            
            if time_line_index != -1:
                # タイムコード取得と整形
                timecode = lines[time_line_index].strip()
                # 矢印を厳密に " --> " にする
                timecode = re.sub(r'\s*[-=]+>\s*', ' --> ', timecode)
                # ミリ秒の区切りをカンマ(,)にする（Webはドット(.)を嫌うことがある）
                timecode = timecode.replace('.', ',')
                
                # 本文取得
                text_lines = lines[time_line_index + 1:]
                text = "\n".join(text_lines).strip()
                
                if text: # 本文がある場合のみ追加
                    # 番号を振り直す（番号飛び防止）
                    formatted_blocks.append(f"{counter}\r\n{timecode}\r\n{text}\r\n\r\n")
                    counter += 1

    # 結合（Windows標準のCRLF改行を使う）
    return "".join(formatted_blocks)

# ==========================================
# 🖥️ Streamlit 画面
# ==========================================
st.set_page_config(page_title="Web用字幕変換")
st.title("🌐 Web用・字幕フォーマット変換")
st.markdown("VLCで見れるのにChrome拡張で見れないファイルを直します。\n(BOMを追加し、Web標準形式に整えます)")

uploaded_file = st.file_uploader("見れないSRTファイルをアップロード", type=["srt"])

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    
    if st.button("変換実行"):
        # 整形実行
        fixed_content = convert_to_web_friendly(content)
        
        st.success("変換完了！Webツール互換の形式（BOM付きUTF-8）にしました。")
        
        # ダウンロードボタン
        # ※ここが重要: encoding='utf-8-sig' でBOMを付ける
        new_filename = uploaded_file.name.replace(".srt", "_WebReady.srt")
        
        st.download_button(
            label="📥 Web対応版をダウンロード",
            data=fixed_content.encode('utf-8-sig'), 
            file_name=new_filename,
            mime="text/plain"
        )
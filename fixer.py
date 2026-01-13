import streamlit as st
import re

def clean_srt(content):
    """SRTファイルを強制的に正しい形式に整形する"""
    # 1. 余計なマークダウン記号（```srt など）を削除
    content = re.sub(r'```(?:srt)?', '', content)
    content = re.sub(r'```', '', content)
    
    # 改行コード統一
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # 2. ブロックに分割（空行または番号で推測）
    # "数字の行" + "改行" + "タイムコードっぽい行" を探す
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2}[,.]\d{3}\s*[-=]+>\s*\d{2}:\d{2}:\d{2}[,.]\d{3})\n(.*?)(?=\n\d+\n\d{2}:\d{2}:\d{2}|$)', re.DOTALL)
    
    matches = pattern.findall(content + "\n") # 末尾検知用改行
    
    fixed_blocks = []
    log = []
    
    for i, (seq, timecode, text) in enumerate(matches):
        # 3. 矢印を正しい形 (-->) に強制変換
        # AIがよくやるミス: ->, ==>, →, - >
        original_timecode = timecode
        timecode = re.sub(r'\s*[-=]+>\s*', ' --> ', timecode)
        timecode = timecode.replace('.', ',') # カンマ区切りに統一
        
        if original_timecode != timecode:
            log.append(f"No.{seq}: タイムコードの矢印を修正しました")

        # 4. 本文の整形（余計な空白削除）
        text = text.strip()
        
        # ブロック再構築
        # 正しいSRT形式: 番号 \n タイムコード \n 本文 \n \n (空行)
        block = f"{seq}\n{timecode}\n{text}\n\n"
        fixed_blocks.append(block)

    return "".join(fixed_blocks), log, len(matches)

# ==========================================
# 🖥️ Streamlit 画面
# ==========================================
st.set_page_config(page_title="SRT修復ツール")
st.title("🚑 SRTファイル修復・整形ツール")
st.markdown("再生できないSRTファイルをアップロードしてください。余計な記号削除やフォーマット修正を自動で行います。")

uploaded_file = st.file_uploader("再生できないSRTファイル", type=["srt"])

if uploaded_file is not None:
    # 読み込み
    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    
    if st.button("修復実行"):
        fixed_content, logs, count = clean_srt(content)
        
        st.success(f"処理完了！ {count} 個の字幕ブロックを抽出・整形しました。")
        
        if logs:
            with st.expander("修正ログを見る"):
                for l in logs:
                    st.write(f"- {l}")
        else:
            st.info("大きな構造エラーは見つかりませんでしたが、念の為フォーマットを正規化しました。")

        # ダウンロードボタン
        new_filename = uploaded_file.name.replace(".srt", "_Fixed.srt")
        st.download_button(
            label="📥 直したファイルをダウンロード",
            data=fixed_content,
            file_name=new_filename,
            mime="text/plain"
        )
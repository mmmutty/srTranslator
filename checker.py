import streamlit as st
import re

def parse_timecodes(content):
    """SRTテキストからタイムコードのリストを抽出する"""
    # 改行コードを統一
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # ブロックに分割（空行区切り）
    blocks = re.split(r'\n\s*\n', content.strip())
    
    timecodes = []
    for i, block in enumerate(blocks):
        lines = block.strip().split('\n')
        # タイムコード行（--> がある行）を探す
        found_time = None
        for line in lines:
            if '-->' in line:
                found_time = line.strip()
                break
        
        # タイムコードがあればリストに追加、なければ "（なし）" とする
        if found_time:
            timecodes.append(found_time)
        else:
            # タイムコードが見つからないブロックがあった場合
            pass 
            
    return timecodes

# ==========================================
# 🖥️ Streamlit 画面構成
# ==========================================

st.set_page_config(page_title="SRTズレチェッカー", layout="wide")
st.title("🔍 字幕ズレ発見ツール")
st.markdown("「元のSRT」と「翻訳したSRT」をアップロードすると、どこでズレ始めたか特定します。")

col1, col2 = st.columns(2)

with col1:
    original_file = st.file_uploader("📂 1. 元のSRTファイル (英語)", type=["srt"])

with col2:
    translated_file = st.file_uploader("📂 2. 翻訳後のSRTファイル (日本語)", type=["srt"])

if st.button("比較開始", type="primary"):
    if original_file is None or translated_file is None:
        st.error("⚠️ 両方のファイルをアップロードしてください。")
    else:
        # ファイルの中身を読み込む
        content1 = original_file.getvalue().decode("utf-8", errors="ignore")
        content2 = translated_file.getvalue().decode("utf-8", errors="ignore")

        # タイムコードを抽出
        times1 = parse_timecodes(content1)
        times2 = parse_timecodes(content2)

        st.write("---")
        st.subheader("📊 分析結果")
        st.write(f"元の字幕ブロック数: **{len(times1)}** 個")
        st.write(f"翻訳版のブロック数: **{len(times2)}** 個")

        # 比較ロープ
        limit = min(len(times1), len(times2))
        diff_found = False

        for i in range(limit):
            t1 = times1[i]
            t2 = times2[i]

            # タイムコードの数字部分だけ取り出して比較（余計なスペースを無視）
            if t1.replace(" ", "") != t2.replace(" ", ""):
                st.error(f"🚨 **ズレ発生箇所を発見！ (No.{i+1})**")
                
                # 詳細を表示
                st.warning(f"ここでタイムコードが食い違っています。")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**元ファイル (No.{i+1})**\n\n`{t1}`")
                with c2:
                    st.error(f"**翻訳ファイル (No.{i+1})**\n\n`{t2}`")
                
                st.markdown("---")
                st.write("💡 **ヒント:**")
                st.write(f"この **No.{i+1}** か、その **1つ前 (No.{i})** の字幕ブロックが、翻訳の際に結合されてしまっている可能性があります。")
                
                diff_found = True
                break
        
        if not diff_found:
            if len(times1) != len(times2):
                st.warning(f"⚠️ {limit}番目までは一致していますが、全体の数が違います。最後の方でズレているか、数が足りていません。")
            else:
                st.success("✅ おめでとうございます！すべてのタイムコードが完全に一致しています。ズレはありません。")
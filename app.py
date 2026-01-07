import streamlit as st
import os
import tempfile
import shutil
from video_compressor import VideoCompressor

st.set_page_config(page_title="動画自動圧縮ツール", page_icon="🎥")

st.title("🎥 動画自動圧縮ツール")
st.markdown("""
Google NotebookLM用に動画を自動圧縮します。
- 目標サイズに合わせてビットレートを自動調整
- 長尺動画は自動分割
- Mac (M-series) ではハードウェア加速を使用
""")


# サイドバー設定
st.sidebar.header("設定")
target_size = st.sidebar.number_input("目標ファイルサイズ (MB)", min_value=10, value=160, step=10, help="200MB以下を推奨")
audio_bitrate = st.sidebar.selectbox("音声ビットレート (kbps)", [64, 128, 192], index=1)
use_hw = st.sidebar.checkbox("ハードウェア加速 (Mac)", value=True, help="MacのMシリーズチップで使用可能。オフにすると標準x264を使用")

st.sidebar.markdown("---")
if st.sidebar.button("アプリを終了 (閉じる)", type="primary"):
    st.sidebar.write("終了中...")
    import time
    time.sleep(1)
    # プロセスをキルして終了させる
    import signal
    os.kill(os.getpid(), signal.SIGINT)


# セッション状態の初期化
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'working_dir' not in st.session_state:
    st.session_state.working_dir = None

# ファイルアップロード
uploaded_file = st.file_uploader("動画ファイルを選択", type=['mp4', 'mov', 'mkv', 'avi', 'webm'])

# リセットボタン（新しいファイルを処理する場合）
if st.session_state.processed_files:
    if st.button("新しいファイルを圧縮する"):
        # 一時ディレクトリのクリーンアップ
        if st.session_state.working_dir and os.path.exists(st.session_state.working_dir):
            shutil.rmtree(st.session_state.working_dir)
        st.session_state.processed_files = []
        st.session_state.working_dir = None
        st.rerun()

if uploaded_file is not None:
    # まだ処理していない、かつ未処理状態の場合のみ圧縮ボタンを表示
    if not st.session_state.processed_files:
        st.info(f"ファイルサイズ: {uploaded_file.size / (1024*1024):.2f} MB")
        
        if st.button("圧縮開始", type="primary"):
            # 一時ディレクトリの作成（セッションで保持）
            temp_dir = tempfile.mkdtemp()
            st.session_state.working_dir = temp_dir
            
            input_path = os.path.join(temp_dir, uploaded_file.name)
            
            # アップロードされたファイルを保存
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            progress_bar = st.progress(0, text="準備中...")
            
            # コンプレッサーの初期化
            compressor = VideoCompressor(target_size_mb=target_size, use_hw_accel=use_hw)
            
            # 圧縮実行
            with st.spinner("圧縮処理中... (これには時間がかかる場合があります)"):
                try:
                    result_paths = compressor.compress(input_path, output_dir=temp_dir)
                    progress_bar.progress(100, text="完了！")
                    
                    # 結果をセッションに保存
                    if result_paths:
                        st.session_state.processed_files = result_paths
                        st.rerun() # 画面更新してダウンロードボタンを表示
                    else:
                        st.warning("処理されたファイルがありませんでした。")
                        
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

    # 処理完了後の表示（セッションにデータがある場合）
    if st.session_state.processed_files:
        st.success("圧縮完了！ 以下のファイルをダウンロードできます。")
        st.write("※「新しいファイルを圧縮する」を押すまで、この画面は保持されます。")
        
        for i, path in enumerate(st.session_state.processed_files):
            if os.path.exists(path):
                file_name = os.path.basename(path)
                file_size = os.path.getsize(path) / (1024*1024)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {file_name} ({file_size:.2f} MB)")
                with col2:
                    with open(path, "rb") as f:
                        file_data = f.read()
                        st.download_button(
                            label="ダウンロード",
                            data=file_data,
                            file_name=file_name,
                            mime="video/mp4",
                            key=f"download_{i}"
                        )


st.markdown("---")
st.caption("Powered by Streamlit & FFmpeg")

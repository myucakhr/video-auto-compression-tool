#!/bin/bash
cd "$(dirname "$0")"

# ターミナルのタイトル設定
echo -n -e "\033]0;動画自動圧縮ツール\007"

echo "========================================================"
echo "  🎥 動画自動圧縮ツールを起動しています..."
echo "  初回起動時は準備に少し時間がかかる場合があります。"
echo "========================================================"
echo ""


# FFmpegのチェック
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpegが見つかりません"
    osascript -e 'display dialog "FFmpegが必要です。\n\nHomebrewなどを利用してインストールしてください。\n例: brew install ffmpeg" buttons {"OK"} default button "OK" with icon stop'
    osascript -e 'tell application "Terminal" to close first window' & exit
fi

# 仮想環境の作成確認

if [ ! -d "venv" ]; then
    echo "📦 必要なファイルを準備しています..."
    python3 -m venv venv
fi

# 仮想環境のアクティベート
source venv/bin/activate

# 依存関係のインストール（更新があれば）
pip install -q -r requirements.txt

# Streamlitアプリの起動
echo "🚀 ブラウザを起動します..."
streamlit run app.py

# アプリ終了後の処理
echo "アプリを終了しました。"
# Terminal.appのウィンドウを閉じる (macOS専用)
osascript -e 'tell application "Terminal" to close first window' & exit

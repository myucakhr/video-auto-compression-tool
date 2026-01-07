#!/bin/bash
cd "$(dirname "$0")"

# 仮想環境の作成確認
if [ ! -d "venv" ]; then
    echo "仮想環境を作成しています..."
    python3 -m venv venv
fi

# 仮想環境のアクティベート
source venv/bin/activate

# 依存関係のインストール
echo "依存関係をインストール中..."
pip install -r requirements.txt

# Streamlitアプリの起動
echo "Webアプリを起動します..."
streamlit run app.py

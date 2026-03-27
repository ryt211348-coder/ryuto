#!/bin/bash
cd "$(dirname "$0")"
echo "=========================================="
echo "  TikTok スキンケア企画メーカー 起動中..."
echo "=========================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません"
    read -p "Enterキーで終了..."
    exit 1
fi

python3 -c "import flask" 2>/dev/null || {
    echo "必要なパッケージをインストール中..."
    pip3 install -r requirements.txt 2>&1 | tail -3
}

echo "サーバーを起動しています..."
echo "ブラウザが自動で開きます。"
echo ""
echo "終了するにはこのウィンドウを閉じてください。"
echo ""

(sleep 2 && open "http://localhost:5000/planner") &

python3 -c "
from waitress import serve
from app import app
print('Server running at http://localhost:5000')
serve(app, host='0.0.0.0', port=5000)
"

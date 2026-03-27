#!/bin/bash
cd "$(dirname "$0")"
echo "=========================================="
echo "  TikTok バイラル分析ツール 起動中..."
echo "=========================================="
echo ""

# Python3の確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません"
    echo "brew install python を実行してください"
    read -p "Enterキーで終了..."
    exit 1
fi

# 依存パッケージの確認・インストール
python3 -c "import flask" 2>/dev/null || pip3 install -q flask rich click jinja2 requests TikTokApi playwright yt-dlp 2>/dev/null

# サーバー起動 & ブラウザ自動オープン
echo "サーバーを起動しています..."
echo "ブラウザが自動で開きます。"
echo ""
echo "終了するにはこのウィンドウを閉じてください。"
echo ""

# 2秒後にブラウザを開く
(sleep 2 && open "http://localhost:5000") &

python3 app.py

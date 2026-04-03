"""デモレポートを生成するスクリプト（動作確認・見た目確認用）."""

import random
import time
from tiktok_analyzer.extractor import VideoInfo
from tiktok_sheet_tool import compute_sheet_data
from generate_report import generate_html_report

# 三崎優太っぽいダミーデータを生成
SAMPLE_TITLES = [
    "青汁王子が暴露する年収1億円の裏側",
    "これ知らないと損する節税テクニック3選",
    "高級車買ったら税務署から連絡きた話",
    "1日のルーティン公開します",
    "破産から復活した方法を全部話します",
    "この投資だけはやめとけ",
    "月収100万円稼ぐために最初にやったこと",
    "詐欺に遭いました...被害額がヤバい",
    "起業して最初の1年で学んだこと",
    "フォロワー100万人達成の裏側",
    "税金で人生終わりかけた話",
    "年商10億の会社の作り方",
    "成功者が絶対にやらない3つのこと",
    "お金持ちになるための習慣TOP5",
    "この副業が今一番稼げます",
    "借金3億からの逆転劇",
    "高級マンションのルームツアー",
    "SNSで稼ぐ最強の方法教えます",
    "炎上して学んだこと全部話す",
    "億万長者の朝のルーティン",
    "絶対に手を出すな!この投資",
    "確定申告で99%の人が間違えること",
    "会社員辞めて起業した結果",
    "親に1000万円プレゼントしてみた",
    "ドバイに移住した本当の理由",
    "ビジネスで一番大事なスキル",
    "年収300万から1億になった転機",
    "ブランド品買い漁ってみた",
    "成功する人としない人の決定的な違い",
    "人生で最も後悔していること",
    "飲食店経営のリアルな数字公開",
    "この株だけは絶対買え",
    "僕が毎日やってる投資法",
    "脱税と節税の違いを解説",
    "1億円の使い道ベスト10",
    "起業初心者がやりがちなミス",
    "お金持ちが絶対やってる朝の習慣",
    "月収1000万のフリーランスの1日",
    "ホリエモンに言われた衝撃の一言",
    "100万円チャレンジやってみた",
    "闇金の取り立てがヤバすぎた",
    "新NISAで絶対やるべきこと",
    "仮想通貨で2000万溶かした話",
    "富裕層だけが知ってる節税法",
    "美容にかけてる金額がエグい",
    "逮捕された時の話します",
    "マッチングアプリの闇を暴露",
    "経営者のカバンの中身公開",
    "Z世代に伝えたい投資の始め方",
    "海外移住のメリットとデメリット",
    "100万円分のブランド品開封",
    "絶対に失敗しないビジネスモデル",
    "お金に困らない人の特徴5選",
    "年商50億社長の財布の中身",
    "ラーメン屋始めたら地獄だった",
    "TikTokで月100万稼ぐ方法",
    "筋トレ始めて人生変わった話",
    "高級時計コレクション全部見せます",
    "借金持ちが絶対やるべきこと",
    "ビジネスパートナーの選び方",
    "1000万円の福袋開封してみた",
]

def generate_demo():
    videos = []
    base_ts = int(time.time())

    # 2年分の投稿データを生成（不規則な投稿頻度）
    day_offset = 0
    for i in range(min(len(SAMPLE_TITLES), 60)):
        # 投稿間隔を不規則に（活動期と休止期を作る）
        if i < 10:
            day_offset += random.randint(1, 4)    # 最近: 高頻度
        elif i < 20:
            day_offset += random.randint(2, 7)    # やや高頻度
        elif i < 35:
            day_offset += random.randint(3, 14)   # まばら
        else:
            day_offset += random.randint(5, 21)   # 初期: かなりまばら

        ts = base_ts - 86400 * day_offset
        view_base = random.randint(50_000, 5_000_000)
        like_ratio = random.uniform(0.03, 0.12)

        videos.append(VideoInfo(
            video_id=str(7000000000 + i),
            title=SAMPLE_TITLES[i % len(SAMPLE_TITLES)],
            url=f"https://www.tiktok.com/@misakism13/video/{7000000000 + i}",
            view_count=view_base,
            like_count=int(view_base * like_ratio),
            comment_count=int(view_base * random.uniform(0.005, 0.03)),
            share_count=int(view_base * random.uniform(0.002, 0.015)),
            duration=random.randint(15, 60),
            upload_date=str(ts),
            description=SAMPLE_TITLES[i % len(SAMPLE_TITLES)] + " #青汁王子 #ビジネス #投資",
            thumbnail="",
        ))

    sd = compute_sheet_data("https://www.tiktok.com/@misakism13", videos)
    # デモ用にフォロワー数を手動設定
    sd.followers = "25万人"
    sd.followers_raw = 250_000

    output = "report_misakism13_demo.html"
    generate_html_report("https://www.tiktok.com/@misakism13", videos, sd, output)
    print(f"デモレポート生成完了: {output}")
    print(f"動画数: {len(videos)}本")
    print(f"総再生数: {sd.total_views:,}")

if __name__ == "__main__":
    generate_demo()

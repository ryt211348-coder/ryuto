"""内蔵チャンネルデータ - 競合分析対象アカウント一覧."""

# 全81アカウント（CSVデータから変換）
# TikTok/Instagram両方持つアカウントは両方登録
BUILTIN_CHANNELS = [
    {"name": "@noako_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@noako_cosme", "followers": 140000, "genre": "アイメイク", "note": "『〜行ったら買って』が人気"},
    {"name": "@noako_cosme", "platform": "Instagram", "url": "https://www.instagram.com/noako_cosme/", "followers": 128000, "genre": "アイメイク", "note": ""},
    {"name": "@biyouhin_honne", "platform": "TikTok", "url": "https://www.tiktok.com/@biyouhin_honne", "followers": 26000, "genre": "コスメの豆知識", "note": "擬人化AI系"},
    {"name": "@maimai..007", "platform": "TikTok", "url": "https://www.tiktok.com/@maimai..007", "followers": 3000, "genre": "美容ライター", "note": ""},
    {"name": "@maimai.007", "platform": "Instagram", "url": "https://www.instagram.com/maimai.007", "followers": 320000, "genre": "美容ライター", "note": ""},
    {"name": "@cosmedana.chan", "platform": "TikTok", "url": "https://www.tiktok.com/@cosmedana.chan", "followers": 19000, "genre": "スキンケア、コスメ", "note": "コスメ大量転がしで信頼感"},
    {"name": "@bucha_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@bucha_cosme", "followers": 23000, "genre": "スキンケア、コスメ", "note": "3人辛口レビュー"},
    {"name": "@bucha_cosme", "platform": "Instagram", "url": "https://www.instagram.com/bucha_cosme", "followers": 19000, "genre": "スキンケア、コスメ", "note": ""},
    {"name": "@cosme_sanshimai", "platform": "TikTok", "url": "https://www.tiktok.com/@cosme_sanshimai", "followers": 37000, "genre": "年齢別コスメ", "note": "20,30,40代の3人"},
    {"name": "@tentalk.cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@tentalk.cosme", "followers": 72000, "genre": "商品比較", "note": "店頭辛口評価スタイル"},
    {"name": "@tentalk.cosme", "platform": "Instagram", "url": "https://www.instagram.com/tentalk.cosme", "followers": 31000, "genre": "商品比較", "note": ""},
    {"name": "@tettei_re", "platform": "TikTok", "url": "https://www.tiktok.com/@tettei_re", "followers": 136000, "genre": "コスメ紹介", "note": "辛口レビュー、最強訴求"},
    {"name": "@tettei_re", "platform": "Instagram", "url": "https://www.instagram.com/tettei_re/", "followers": 113000, "genre": "コスメ紹介", "note": ""},
    {"name": "@shozikiebi", "platform": "TikTok", "url": "https://www.tiktok.com/@shozikiebi", "followers": 130000, "genre": "スキンケア、コスメ、ヘアケア", "note": "元美容部員の正直レビュー"},
    {"name": "@shozikiebi_", "platform": "Instagram", "url": "https://www.instagram.com/shozikiebi_", "followers": 92000, "genre": "スキンケア、コスメ、ヘアケア", "note": ""},
    {"name": "@cosme_katari.club", "platform": "TikTok", "url": "https://www.tiktok.com/@cosme_katari.club", "followers": 140000, "genre": "バズ商品、検証系", "note": ""},
    {"name": "@karaimo_desuu", "platform": "TikTok", "url": "https://www.tiktok.com/@karaimo_desuu", "followers": 105000, "genre": "辛口レビュー", "note": ""},
    {"name": "@choa_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@choa_cosme", "followers": 125000, "genre": "韓国系コスメ、スキンケア", "note": ""},
    {"name": "@seibun_otakuchan", "platform": "TikTok", "url": "https://www.tiktok.com/@seibun_otakuchan", "followers": 380000, "genre": "成分レビュー", "note": "成分オタク、ガチレビュー"},
    {"name": "@nagi.skincare", "platform": "TikTok", "url": "https://www.tiktok.com/@nagi.skincare", "followers": 130000, "genre": "スキンケア", "note": "ニキビ特化から幅広く"},
    {"name": "@cosme_daisuki.kaigi", "platform": "TikTok", "url": "https://www.tiktok.com/@cosme_daisuki.kaigi", "followers": 250000, "genre": "ガチ検証", "note": "2人組、親近感あるコスメオタク"},
    {"name": "@_kayodoll_", "platform": "TikTok", "url": "https://www.tiktok.com/@_kayodoll_", "followers": 470000, "genre": "ルーティン、美容グッズ", "note": "ナレーション4種使い分け"},
    {"name": "@coco_home__", "platform": "TikTok", "url": "https://www.tiktok.com/@coco_home__", "followers": 140000, "genre": "美容商品紹介", "note": "ダイエット飯も人気"},
    {"name": "@mote_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@mote_cosme", "followers": 185000, "genre": "ナチュラル系コスメ", "note": "買わないと損する神コスメ"},
    {"name": "@tantei_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@tantei_cosme", "followers": 140000, "genre": "ガチ検証", "note": "検証のプロ"},
    {"name": "@r___cosme2021", "platform": "TikTok", "url": "https://www.tiktok.com/@r___cosme2021", "followers": 140000, "genre": "目元メイク", "note": ""},
    {"name": "@cosme_kaiju", "platform": "TikTok", "url": "https://www.tiktok.com/@cosme_kaiju", "followers": 131000, "genre": "プチプラコスメ、スキンケア", "note": ""},
    {"name": "@cosme_kaiju", "platform": "Instagram", "url": "https://www.instagram.com/cosme_kaiju/", "followers": 39000, "genre": "プチプラコスメ、スキンケア", "note": ""},
    {"name": "@bibichan_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@bibichan_cosme", "followers": 260000, "genre": "コスメ、スキンケア、ヘアケア", "note": "ガチレビュー"},
    {"name": "@ossy_beautylog", "platform": "TikTok", "url": "https://www.tiktok.com/@ossy_beautylog", "followers": 100000, "genre": "本気レビュー", "note": ""},
    {"name": "@kojicosme", "platform": "TikTok", "url": "https://www.tiktok.com/@kojicosme", "followers": 86000, "genre": "スキンケア、コスメ", "note": ""},
    {"name": "@bihadanaritaina", "platform": "TikTok", "url": "https://www.tiktok.com/@bihadanaritaina", "followers": 97000, "genre": "スキンケア、ヘアケア正直レビュー", "note": ""},
    {"name": "@hru._.u3", "platform": "TikTok", "url": "https://www.tiktok.com/@hru._.u3", "followers": 202000, "genre": "自己肯定感高い系", "note": "Vlogっぽい共感・憧れ"},
    {"name": "@biyou_shidax", "platform": "TikTok", "url": "https://www.tiktok.com/@biyou_shidax", "followers": 70000, "genre": "コスメ紹介", "note": "成分解説"},
    {"name": "@give_me_jishin", "platform": "TikTok", "url": "https://www.tiktok.com/@give_me_jishin", "followers": 98000, "genre": "垢抜け", "note": ""},
    {"name": "@totsugeki_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@totsugeki_cosme", "followers": 110000, "genre": "バズ商品、新作レビュー", "note": ""},
    {"name": "@55.co.jp", "platform": "TikTok", "url": "https://www.tiktok.com/@55.co.jp", "followers": 78000, "genre": "美容、vlog", "note": ""},
    {"name": "@guga9791", "platform": "TikTok", "url": "https://www.tiktok.com/@guga9791", "followers": 100000, "genre": "メイク紹介", "note": ""},
    {"name": "@yuna_kireii", "platform": "TikTok", "url": "https://www.tiktok.com/@yuna_kireii", "followers": 84000, "genre": "セイロ垢抜け", "note": ""},
    {"name": "@taka_biyou", "platform": "TikTok", "url": "https://www.tiktok.com/@taka_biyou", "followers": 32000, "genre": "スキンケア、コスメ", "note": "男性"},
    {"name": "@mire_k_23", "platform": "TikTok", "url": "https://www.tiktok.com/@mire_k_23", "followers": 81000, "genre": "スキンケア、プチプラ", "note": ""},
    {"name": "@mire_k_23", "platform": "Instagram", "url": "https://www.instagram.com/mire_k_23/", "followers": 92000, "genre": "スキンケア、プチプラ", "note": ""},
    {"name": "@kashiyui_beauty", "platform": "TikTok", "url": "https://www.tiktok.com/@kashiyui_beauty", "followers": 34000, "genre": "スキンケア商品、改善方法", "note": ""},
    {"name": "@sana_kakifly", "platform": "TikTok", "url": "https://www.tiktok.com/@sana_kakifly", "followers": 70000, "genre": "ヘアアレンジ", "note": "美容師"},
    {"name": "@shabon_official", "platform": "TikTok", "url": "https://www.tiktok.com/@shabon__official", "followers": 130000, "genre": "美容メディア", "note": ""},
    {"name": "@shabon_official", "platform": "Instagram", "url": "https://www.instagram.com/shabon_official", "followers": 664000, "genre": "美容メディア", "note": ""},
    {"name": "@hikaru_0177", "platform": "TikTok", "url": "https://www.tiktok.com/@hikaru_0177", "followers": 48000, "genre": "韓国コスメ、成分マニア", "note": ""},
    {"name": "@hikaru_0177", "platform": "Instagram", "url": "https://www.instagram.com/hikaru_0177", "followers": 321000, "genre": "韓国コスメ、成分マニア", "note": ""},
    {"name": "@emme_tokyo", "platform": "Instagram", "url": "https://www.instagram.com/emme_tokyo.jp/", "followers": 776000, "genre": "スキンケア全般", "note": "最大手"},
    {"name": "@nene_cosme_nene", "platform": "Instagram", "url": "https://www.instagram.com/nene_cosme_nene/", "followers": 131000, "genre": "目元メイク", "note": ""},
    {"name": "@nera_beauty", "platform": "Instagram", "url": "https://www.instagram.com/nera.beauty", "followers": 148000, "genre": "美容メディア", "note": ""},
    {"name": "@karin_beauty_diet", "platform": "Instagram", "url": "https://www.instagram.com/karin_beauty_diet", "followers": 94000, "genre": "美容鍋", "note": ""},
    {"name": "@serina.beauty_", "platform": "Instagram", "url": "https://www.instagram.com/serina.beauty_", "followers": 75000, "genre": "スキンケア紹介", "note": ""},
    {"name": "@tesuko_test", "platform": "Instagram", "url": "https://www.instagram.com/tesuko_test/", "followers": 108000, "genre": "スキンケア、コスメ", "note": "テスト系"},
    {"name": "@maripii_cosme", "platform": "TikTok", "url": "https://www.tiktok.com/@maripii_cosme", "followers": 14000, "genre": "コスメ・メイク", "note": "目元メイク人気"},
    {"name": "@maripii_cosme", "platform": "Instagram", "url": "https://www.instagram.com/maripii_cosme", "followers": 123000, "genre": "コスメ・メイク", "note": ""},
    {"name": "@charico2019", "platform": "TikTok", "url": "https://www.tiktok.com/@charico2019", "followers": 23000, "genre": "コスメ紹介", "note": "リップ紹介多め"},
    {"name": "@charico2019", "platform": "Instagram", "url": "https://www.instagram.com/charico2019", "followers": 220000, "genre": "コスメ紹介", "note": ""},
]

# TikTokアカウントのみ抽出（Apifyスクレイピング用）
TIKTOK_ACCOUNTS = [ch["name"] for ch in BUILTIN_CHANNELS if ch["platform"] == "TikTok"]

# Instagramアカウントのみ抽出
INSTAGRAM_ACCOUNTS = [ch["name"] for ch in BUILTIN_CHANNELS if ch["platform"] == "Instagram"]

# フォロワー数でソート済みのTOP TikTokアカウント（5万以上）
TOP_TIKTOK_ACCOUNTS = sorted(
    [ch for ch in BUILTIN_CHANNELS if ch["platform"] == "TikTok" and ch.get("followers", 0) >= 50000],
    key=lambda x: x.get("followers", 0),
    reverse=True,
)

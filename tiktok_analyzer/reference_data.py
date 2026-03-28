"""ビルトイン参考台本データ - CSVアップロード不要で使える."""

# 伸びていない動画の分析データ
FAILURE_SCRIPTS = [
    {
        "url": "https://www.tiktok.com/@food_mini_labo/video/7608176663985229063",
        "views": 2000,
        "analysis": "「ちょっと待って！」の時点で具体的な動画の趣旨が全く伝わらない。早口すぎる。BGMうるさい。",
        "transcript": "",
    },
    {
        "url": "https://www.tiktok.com/@cosme_plus/video/7612612799763598612",
        "views": 2000,
        "analysis": "ぱっと見で毛だということはわかるが頭皮をズームしたものだとはわからない。背景の毛がキャラよりも太く長く森林のような感じになっていないとダメ。下から風を当てるのはやめて、の状態がうまくイメージできない。",
        "transcript": "うわぁぁぁ！熱い 風が強い！下から風を当てるのはやめて！キューティクルが逆剥けしてパサパサになっちゃうよ！！風は必ず「上から下」あ〜気持ちいい。大体8割くらい乾いたら最後に「冷風」に切り替えて！冷やすことでキュッと引き締まって綺麗にまとまるよ！！",
    },
    {
        "url": "https://www.tiktok.com/@cosme_plus/video/7610377984217812244",
        "views": 3000,
        "analysis": "もっとネガティブに訴求する必要があるが、楽しそうにしている声色と表情で違和感。ズームすぎて何をキャラに変えているのか全くわからない。初手で伝わらないからアウト。",
        "transcript": "ちょっと！！泡だてないで洗顔するのはやめて 摩擦で肌が荒れちゃう 泡だてネットでしっかり泡だてて肌に密着させた方が汚れを吸着させて綺麗にできるわよ",
    },
    {
        "url": "https://www.tiktok.com/@cosme_plus/video/7610719912020938004",
        "views": 7000,
        "analysis": "伸びている動画とは正反対で、ニキビが楽しそうにしている。ニキビの形がニキビではない。映像だけで伝わるものでないと尺も勿体無い。非現実的すぎる。",
        "transcript": "僕はニキビ 今日は僕が元気になる食べものを紹介するよ！牛乳にチーズ 乳製品は皮脂の分泌を活発にする栄養剤だよ！！",
    },
    {
        "url": "https://www.tiktok.com/@biyouhin_honne/video/7613321036624317716",
        "views": 30000,
        "analysis": "スキンケアの代表がタオルは変。笑っているのが訴求として弱い。「聞け！」が怒りの感情でないと、聞かなきゃやばいという感情にならない。表情とセリフを一致させる必要がある。",
        "transcript": "",
    },
    {
        "url": "https://www.tiktok.com/@biyouhin_honne/video/7614055058229038357",
        "views": 63000,
        "analysis": "声が明るすぎるし、キャラの顔も笑顔だからネガティブな訴求になっていない。",
        "transcript": "",
    },
    {
        "url": "https://www.tiktok.com/@biyouhin_honne/video/7609971102311255317",
        "views": 100000,
        "analysis": "「ニキビに悩んでるお前たち聞け！」声の抑揚が少し足りない。もっと怒りの声にするべき。全体的に白すぎる印象。",
        "transcript": "",
    },
]

# 伸びている動画の分析データ
SUCCESS_SCRIPTS = [
    {
        "url": "",
        "title": "ニキビに効く生活ハック方法",
        "views": 4900000,
        "analysis": "ニキビは気になると触りがちでそれがどれくらい悪影響なのかが冒頭のニキビの色や表情・声色でわかりやすい。擬人化するなら手とか眉毛があった方が良い。指が大きく写っていることでミクロの世界を体験できる。段階的にニキビについて解説しているので悩んでいる人たちが改善策を見つけることができる。冒頭強いかつループ再生する構成。",
        "voice": "赤ニキビ:20代男性怒鳴り声 白ニキビ:冷静にニヤッと脅す感じのイケボ 黒ニキビ:少し若い感じで元気 黄色ニキビ:トーンダウンから右肩上がり 紫ニキビ:大将っぽい低い声",
        "transcript": "その指を今すぐ引っ込めろ！俺は白ニキビ アクネ菌にとって最高級の高カロリー弁当だ 外のバイ菌がこれに気づいたら一気に大炎上して戦場に変わるぜ 俺は黒ニキビ 俺は汚れてるんじゃなくて皮脂が外気に触れて酸化してるだけ 無理に絞り出すともっと太いのが育つぜ うわぁぁ！！指を近づけるな！俺は赤ニキビ 今、白血球軍団が増えすぎたバイ菌に総攻撃を仕掛けてる最中なんだ",
    },
    {
        "url": "",
        "title": "最近の保湿ライフハック",
        "views": 3800000,
        "analysis": "顔にオイル＋シャワー＋女性で見た瞬間にクレンジングのことだとわかる。物だけをポンと置くのではなく、それが使われるときの一番共感度の高い状況を映像でパッとわからせることが大事。目がくりっとしてディズニーっぽいキャラの感じが良い。",
        "voice": "クレンジングオイル:女性の芯の通った声 コーティング剤:女性で落ち着いた若い声 角質:少し早口でオタクっぽい女性 ビタミンC美容液:イケボの男性",
        "transcript": "待ちなさーい！私はクレンジングオイル 塗ってすぐ流さないで！少量の水で白く濁る「乳化」の時間がないと毛穴の汚れを捕まえられないの 私は角質 肌の表面は全部死んだ細胞って知ってた？でも死んでるからこそバイ菌と通さない最強の盾になれるの",
    },
    {
        "url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809",
        "views": 3600000,
        "analysis": "枕のキャラを邪魔しない程度に人間が映っている。汚い・悪い顔から自分の枕も…？と置き換えられるし、毎日使う物だからたくさんの人が没入してしまう。キャラに手がついていることで人間っぽさが増す。",
        "voice": "枕:男性バカにするような敵役っぽい バスタオル:若い男性臆病な感じ フライパン:声変わり前の少年泣いている スポンジ:男性高めの声博識そう まな板:大人な男性イケボ紳士 タオル:男性早口で捲し立てる",
        "transcript": "俺様を1週間も放置するとはいい度胸だな たった今便座の1万倍の細菌が貴様の顔面を食い荒らしてるぞ 愚かだな！ハハハハハハハ！",
    },
    {
        "url": "https://www.tiktok.com/@monotachinohonne/video/7610772635319864583",
        "views": 2500000,
        "analysis": "角栓ぽい見た目+かわいさがある。角栓＝嫌なもの+元気そうな挨拶→ギャップ。化粧品(+)×怒ったセリフ(-)のプラマイの組み合わせが必須。",
        "voice": "",
        "transcript": "よぉ！俺は角栓だ！俺がいっぱい詰まれば立派なイチゴ鼻の完成だぜ ガハハハ〜 気になるからって指で無理やり押し出そうとするなよー 肌を痛めて毛穴がもっと広がるだけだ …へっ、俺を消したいって？仕方ねえ 俺の弱点を教えてやるよ",
    },
    {
        "url": "",
        "title": "俺は髪の毛",
        "views": 2300000,
        "analysis": "身体のミクロな世界を覗き見する感覚になるから自分ごと化しやすい。キャラと口調がそれぞれ立っていないといけない。基本的に冒頭はかなり怒っている感じがいい。緩急をつける必要がある。",
        "voice": "髪の毛:20代男性怒り 毛穴:女おばさんぽい バスタオル:落ち着いた30代男性呆れてる シャワー:10代から20代の男性怒り 日焼け止め:アナウンサーぽい男性優しい",
        "transcript": "俺は髪の毛 誰のせいでこんなに傷んでると思ってるんだ 毎日濡れた髪に櫛を通したりタオルでゴシゴシ 挙句の果てには焼き始める もっといたわってくれよ",
    },
    {
        "url": "",
        "title": "美容液の効果を最大限に引き出す方法",
        "views": 1700000,
        "analysis": "「美容液を使ってるお前たち聞け！」で始まるから美容液の話だとわかる。美容液を使っている女性・少数の男性が手を止める。",
        "voice": "美容液1:若い男性冒頭は怒っている",
        "transcript": "",
    },
    {
        "url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845",
        "views": 1600000,
        "analysis": "「スキンケアにお金かけてるお前たち聞け！」表情・体の動きが多彩で良い。怒っている表情と声色でスキンケアにはお金をかけなくてもいいかも？という欲求に刺さっている。",
        "voice": "",
        "transcript": "",
    },
    {
        "url": "",
        "title": "フェイスパックの活用法と美容の秘訣",
        "views": 1200000,
        "analysis": "冒頭の表情もかなり大きく動いているし、特に声の張り具合が大きくて良い。頰がピンクになっていて可愛い、怒っている口調とキャラの可愛さのギャップ。女性にはウケやすいデザインにする必要もありそう。",
        "voice": "",
        "transcript": "",
    },
    {
        "url": "",
        "title": "ニキビ対策のライフハック",
        "views": 1100000,
        "analysis": "かなり映像がリアル。丸いフォルムと目、声が可愛くて手を止めた可能性が高い。ニキビがリアルで汚い分、キャラの可愛さで補えている・ギャップになって良い。",
        "voice": "",
        "transcript": "",
    },
]

# 全体的な法則まとめ
STYLE_RULES = {
    "success_rules": [
        "冒頭0.3秒で「何の動画か」が映像だけで完結している",
        "等身大＋人の手や顔が一緒に映っている（ミクロの世界を覗き見する感覚）",
        "キャラの表情・声・動きに緩急がある",
        "冒頭は怒り・焦りなどネガティブ感情で掴む",
        "複数キャラの声のトーン・口調・年齢感をキャラごとに変える",
        "怒っている声と可愛いキャラのギャップが止まる要因になる",
        "「〇〇に悩んでるお前たち聞け！」か、映像で状況が成立している",
        "悩みが具体的であればあるほど自分ごと化しやすい（「ニキビ」より「赤ニキビ」の方が強い）",
        "ためになる情報が段階的に出てくる構成",
        "ループ再生につながる構成にする",
        "化粧品(+)×怒ったセリフ(-)のプラマイの組み合わせが必須",
    ],
    "failure_rules": [
        "冒頭で何かわからない（ズームしすぎ）",
        "背景との大きさが不自然（等身大でない）",
        "非現実要素が多すぎる（キャラが人間と同サイズなど）",
        "声・表情がセリフと一致していない（「聞け！」なのに笑顔・明るい声）",
        "映像だけでキャラが特定できない（「私は〇〇」と言わないとわからない）",
        "悩みの設定が抽象的すぎる",
        "楽しそうにしている声色と表情でネガティブ訴求が死ぬ",
    ],
    "voice_guidelines": [
        "冒頭キャラは怒り・焦りなどネガティブ感情",
        "複数キャラの声・口調・年齢感がそれぞれ違う必要がある",
        "声の質も大事（イケボが最後に来ると映える等）",
        "怒りの声色が足りないと訴求が弱くなる",
    ],
}


# キーワードごとの関連動画・アカウント情報
KEYWORD_REFERENCES = {
    "ニキビ スキンケア": {
        "desc": "ニキビの原因・対策・ケア方法",
        "videos": [
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605570234803555605", "title": "ニキビに効く生活ハック方法（ニキビ擬人化）", "views": 4900000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7610719912020938004", "title": "僕はニキビ 今日は僕が元気になる食べもの", "views": 7000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609971102311255317", "title": "ニキビに悩んでるお前たち聞け！", "views": 100000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@uraakahost/video/7613334704762146055", "title": "ニキビが擬人化して走る", "views": 13000, "account": "@uraakahost"},
            {"url": "https://www.tiktok.com/@beauty_ai_biyouzatsugaku/video/7615585171626282261", "title": "ニキビの擬人化（赤ニキビ）", "views": 800, "account": "@beauty_ai_biyouzatsugaku"},
            {"url": "https://www.tiktok.com/@life_upgrade_lab.jp/video/7608089536547048724", "title": "僕はヘアオイル（ニキビとの関連）", "views": 1030000, "account": "@life_upgrade_lab.jp"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7613385224214433045", "title": "化粧したまま寝るき!!（ニキビ警告）", "views": 4000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@tv76317/video/7608890482671897876", "title": "ニキビケア解説", "views": 700000, "account": "@tv76317"},
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7608499192977181970", "title": "ニキビ擬人化（モノの本音）", "views": 1300000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605205417135754517", "title": "ニキビケアAI解説", "views": 1270000, "account": "@health_hack_ai"},
        ],
        "accounts": [
            {"name": "@health_hack_ai", "url": "https://www.tiktok.com/@health_hack_ai", "note": "AIスキンケア系 490万再生"},
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@uraakahost", "url": "https://www.tiktok.com/@uraakahost", "note": "ニキビ擬人化系"},
        ],
    },
    "毛穴 ケア": {
        "desc": "毛穴の黒ずみ・角栓・いちご鼻対策",
        "videos": [
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7610772635319864583", "title": "よぉ！俺は角栓だ！", "views": 2500000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "毛穴に悩んでるお前たち聞け！", "views": 800000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605570234803555605", "title": "私はあなたの毛穴", "views": 100000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7610377984217812244", "title": "泡だてないで洗顔するのはやめて", "views": 3000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7613696925551840533", "title": "脂性肌で顔が油田になってるお前たち聞け！", "views": 30000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "俺様を1週間も放置するとは（枕×毛穴）", "views": 3600000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7609994237874097428", "title": "私はシートマスク！", "views": 5000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7612566064408415508", "title": "毛穴ケア解説", "views": 17000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@tokyo.esthetic/video/7615572145439083796", "title": "毛囊炎の解説", "views": 8000, "account": "@tokyo.esthetic"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614055058229038357", "title": "毛穴ケア商品紹介", "views": 63000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@monotachinohonne", "url": "https://www.tiktok.com/@monotachinohonne", "note": "モノの本音・擬人化系 250万再生"},
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@health_hack_ai", "url": "https://www.tiktok.com/@health_hack_ai", "note": "AIスキンケア系"},
        ],
    },
    "スキンケア ルーティン": {
        "desc": "朝夜のスキンケア手順",
        "videos": [
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "最近の保湿ライフハック（コスメ擬人化）", "views": 3800000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "スキンケアにお金かけてるお前たち聞け！", "views": 1600000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7613321036624317716", "title": "スキンケアにお金をかけているお前たち聞け（タオル）", "views": 30000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7615546660550331669", "title": "スキンケア解説（アニメ風）", "views": 68000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7611155337894219029", "title": "濡れたままトリートメントするのはやめて！", "views": 19000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7606951455450352917", "title": "私はフェイスパック", "views": 66000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7610712059528940820", "title": "スキンケアばっかり意識して食事管理していないお前たち聞け！", "views": 50000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@lifeha9man/video/7613680445170945300", "title": "私を常温で置きっぱなしにしないで（化粧水擬人化）", "views": 50000, "account": "@lifeha9man"},
            {"url": "https://www.tiktok.com/@lifeha9man/video/7607400925254225168", "title": "私たちをもっと丁寧に扱ってちょうだいね！", "views": 40000, "account": "@lifeha9man"},
            {"url": "https://www.tiktok.com/@lifeha9man/video/7617797547624516884", "title": "4つの診断でわかるあなたの美容タイプ", "views": 20000, "account": "@lifeha9man"},
        ],
        "accounts": [
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック系 380万再生"},
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@cosme_plus", "url": "https://www.tiktok.com/@cosme_plus", "note": "コスメ情報"},
        ],
    },
    "美白 透明感": {
        "desc": "くすみ対策・トーンアップ・ビタミンC美容液",
        "videos": [
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "ビタミンC美容液「俺を朝肌に召喚しろ」", "views": 3800000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "美容液の効果を最大限に引き出す方法", "views": 1700000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "フェイスパックの活用法と美容の秘訣", "views": 1200000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7615546660550331669", "title": "美白ケア解説", "views": 68000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614055058229038357", "title": "透明感アップのコツ", "views": 63000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック系"},
            {"name": "@cosme_plus", "url": "https://www.tiktok.com/@cosme_plus", "note": "コスメ情報"},
        ],
    },
    "乾燥肌 保湿": {
        "desc": "保湿ケア・インナードライ対策",
        "videos": [
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "最近の保湿ライフハック", "views": 3800000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "スキンケアにお金かけてるお前たち聞け！", "views": 1600000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "インナードライのお前達聞け！", "views": 780000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7613696925551840533", "title": "脂性肌のお前たち聞け（保湿ジェル）", "views": 750000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614055058229038357", "title": "保湿ケア商品紹介", "views": 63000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック系"},
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@cosme_plus", "url": "https://www.tiktok.com/@cosme_plus", "note": "コスメ情報"},
        ],
    },
    "韓国 スキンケア": {
        "desc": "韓国コスメ・アヌア・クオリティファーストなど話題の商品",
        "videos": [
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "フェイスパックの活用法と美容の秘訣", "views": 1200000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7609994237874097428", "title": "シートマスク（アヌアのドクダミシカ紹介）", "views": 5000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7613696925551840533", "title": "脂性肌のお前たち聞け（アヌア・オルビス紹介）", "views": 750000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "スキンケアにお金かけてるお前たち聞け！", "views": 1600000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7606951455450352917", "title": "フェイスパック（クオリティファースト紹介）", "views": 66000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@cosme_plus", "url": "https://www.tiktok.com/@cosme_plus", "note": "コスメ情報"},
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック系"},
        ],
    },
    "敏感肌 赤み 鎮静": {
        "desc": "敏感肌向けスキンケア・CICA",
        "videos": [
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "肌質のわからないお前たち聞け！", "views": 950000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614055058229038357", "title": "敏感肌向けケア紹介", "views": 63000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@tokyo.esthetic/video/7615572145439083796", "title": "毛嚢炎の解説と対策", "views": 8000, "account": "@tokyo.esthetic"},
            {"url": "https://www.tiktok.com/@cosme_plus/video/7610377984217812244", "title": "泡だてないで洗顔するのはやめて（摩擦注意）", "views": 3000, "account": "@cosme_plus"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7613696925551840533", "title": "脂性肌のお前たち聞け（肌タイプ解説）", "views": 750000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
            {"name": "@tokyo.esthetic", "url": "https://www.tiktok.com/@tokyo.esthetic", "note": "エステ系"},
            {"name": "@cosme_plus", "url": "https://www.tiktok.com/@cosme_plus", "note": "コスメ情報"},
        ],
    },
    "ニキビ跡 治し方": {
        "desc": "ニキビ跡・クレーター対策",
        "videos": [
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605570234803555605", "title": "ニキビに効く生活ハック（紫ニキビ→クレーター警告）", "views": 4900000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605205417135754517", "title": "角質ケアの効果的な方法", "views": 1270000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609971102311255317", "title": "ニキビに悩んでるお前たち聞け！", "views": 100000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@uraakahost/video/7613334704762146055", "title": "ニキビ跡ケア", "views": 13000, "account": "@uraakahost"},
            {"url": "https://www.tiktok.com/@beauty_ai_biyouzatsugaku/video/7615585171626282261", "title": "ニキビ跡対策AI解説", "views": 800, "account": "@beauty_ai_biyouzatsugaku"},
        ],
        "accounts": [
            {"name": "@health_hack_ai", "url": "https://www.tiktok.com/@health_hack_ai", "note": "AIスキンケア系"},
            {"name": "@beauty_ai_biyouzatsugaku", "url": "https://www.tiktok.com/@beauty_ai_biyouzatsugaku", "note": "美容AI雑学"},
            {"name": "@biyouhin_honne", "url": "https://www.tiktok.com/@biyouhin_honne", "note": "美容品本音レビュー"},
        ],
    },
    "美容 ライフハック": {
        "desc": "美容の裏技・豆知識・擬人化フォーマット",
        "videos": [
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605570234803555605", "title": "ニキビに効く生活ハック方法", "views": 4900000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "俺様を1週間も放置するとは（枕擬人化）", "views": 3600000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7610772635319864583", "title": "よぉ！俺は角栓だ！", "views": 2500000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@lifeha9man/video/7607400925254225168", "title": "俺は髪の毛（ライフハック）", "views": 2300000, "account": "@lifeha9man"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "美容液の効果を最大限に引き出す方法", "views": 1700000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "スキンケアにお金かけてるお前たち聞け！", "views": 1600000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7608499192977181970", "title": "美容ライフハック（モノの本音）", "views": 1300000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605205417135754517", "title": "美容AI解説", "views": 1270000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "フェイスパックの活用法", "views": 1200000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@life_upgrade_lab.jp/video/7608089536547048724", "title": "僕はヘアオイル", "views": 1030000, "account": "@life_upgrade_lab.jp"},
        ],
        "accounts": [
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック系 360万再生"},
            {"name": "@health_hack_ai", "url": "https://www.tiktok.com/@health_hack_ai", "note": "AIスキンケア系 490万再生"},
            {"name": "@lifeha9man", "url": "https://www.tiktok.com/@lifeha9man", "note": "ライフハック系 230万再生"},
        ],
    },
    "擬人化 スキンケア": {
        "desc": "コスメ・肌悩み擬人化フォーマット（最も伸びるフォーマット）",
        "videos": [
            {"url": "https://www.tiktok.com/@health_hack_ai/video/7605570234803555605", "title": "ニキビ擬人化（赤白黒黄紫の5段階）", "views": 4900000, "account": "@health_hack_ai"},
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "コスメ擬人化（クレンジング・角質・ビタミンC）", "views": 3800000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@life_hack_ai_world/video/7604846779409943809", "title": "日用品擬人化（枕・タオル・スポンジ）", "views": 3600000, "account": "@life_hack_ai_world"},
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7610772635319864583", "title": "角栓擬人化「よぉ！俺は角栓だ！」", "views": 2500000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@lifeha9man/video/7607400925254225168", "title": "髪の毛・毛穴・バスタオル擬人化", "views": 2300000, "account": "@lifeha9man"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7609598384671853845", "title": "鏡擬人化「スキンケアにお金かけてるお前たち聞け！」", "views": 1600000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@monotachinohonne/video/7608499192977181970", "title": "モノの本音（擬人化シリーズ）", "views": 1300000, "account": "@monotachinohonne"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "フェイスパック擬人化", "views": 1200000, "account": "@biyouhin_honne"},
            {"url": "https://www.tiktok.com/@life_upgrade_lab.jp/video/7608089536547048724", "title": "ヘアオイル擬人化「僕はヘアオイル」", "views": 1030000, "account": "@life_upgrade_lab.jp"},
            {"url": "https://www.tiktok.com/@biyouhin_honne/video/7614801399645277460", "title": "美顔器擬人化「美顔器買おうか悩んでるお前達聞け！」", "views": 1300000, "account": "@biyouhin_honne"},
        ],
        "accounts": [
            {"name": "@monotachinohonne", "url": "https://www.tiktok.com/@monotachinohonne", "note": "モノの本音・擬人化特化"},
            {"name": "@life_hack_ai_world", "url": "https://www.tiktok.com/@life_hack_ai_world", "note": "ライフハック擬人化 380万再生"},
            {"name": "@health_hack_ai", "url": "https://www.tiktok.com/@health_hack_ai", "note": "AI美容擬人化 490万再生"},
        ],
    },
}

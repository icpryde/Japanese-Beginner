# -*- coding: utf-8 -*-
"""Per-day vocabulary specs for build_vocab_day.py.

Each word: id (clean romaji slug, used for image+audio filenames),
japanese, romaji (as printed), english, alt (image alt text),
audio (EXACT filename in the raw 'Day N - Vocabulary Audio' folder),
img: True if the word has an illustration on the sheet.

Illustrated words (img=True) must appear in reading order
(top->bottom, left column then right, page by page) so they line up with
the auto-detected illustration crops.
"""

SPECS = {
    8: {
        "week": 2, "day": 8, "lesson_id": "12645480",
        "title": "Day 8 Vocabulary",
        "raw_audio_dir": "10. Week 2 - Day 8/3.Day 8 - VocabularyText/Day 8 - Vocabulary Audio",
        "pages": ["Vocabulary_Day_8_png.png", "Vocabulary_Day_8_png2.png", "Vocabulary_Day_8_png3.png"],
        "words": [
            # page 1 — all illustrated (reading order)
            {"id": "onaka_ga_sukimashita", "japanese": "おなかがすきました", "romaji": "onaka ga sukimashita", "english": "I'm hungry", "alt": "Hungry", "audio": "onakaga skimashita.m4a", "img": True},
            {"id": "hirugohan", "japanese": "ひるごはん", "romaji": "hirugohan", "english": "lunch", "alt": "Lunch", "audio": "hirugohan.m4a", "img": True},
            {"id": "tabemasu", "japanese": "たべます", "romaji": "tabemasu", "english": "to eat", "alt": "To eat", "audio": "tabemas.m4a", "img": True},
            {"id": "ikimasu", "japanese": "いきます", "romaji": "ikimasu", "english": "to go", "alt": "To go", "audio": "ikimas.m4a", "img": True},
            {"id": "raamen", "japanese": "ラーメン（らーめん）", "romaji": "raamen", "english": "ramen", "alt": "Ramen", "audio": "raamen.m4a", "img": True},
            {"id": "mise", "japanese": "みせ", "romaji": "mise", "english": "store", "alt": "Store", "audio": "mise.m4a", "img": True},
            {"id": "benkyoo", "japanese": "べんきょう", "romaji": "benkyoo", "english": "study", "alt": "Study", "audio": "benkyoo.m4a", "img": True},
            {"id": "sensee", "japanese": "せんせい", "romaji": "sensee", "english": "teacher", "alt": "Teacher", "audio": "sensee.m4a", "img": True},
            {"id": "ryoo", "japanese": "りょう", "romaji": "ryoo", "english": "dormitory", "alt": "Dormitory", "audio": "ryoo.m4a", "img": True},
            {"id": "heya", "japanese": "へや", "romaji": "heya", "english": "room", "alt": "Room", "audio": "heya.m4a", "img": True},
            # page 2 top — illustrated
            {"id": "gyuudon", "japanese": "ぎゅうどん", "romaji": "gyuudon", "english": "beef bowl", "alt": "Beef bowl", "audio": "gyuudon.m4a", "img": True},
            {"id": "sushi", "japanese": "すし", "romaji": "sushi", "english": "sushi", "alt": "Sushi", "audio": "sushi.m4a", "img": True},
            {"id": "ryoori", "japanese": "りょうり", "romaji": "ryoori", "english": "food", "alt": "Food", "audio": "ryoori.m4a", "img": True},
            # page 2 — text-only (oishii sits in the illustrated block but has no picture)
            {"id": "oishii", "japanese": "おいしい", "romaji": "oishii", "english": "delicious", "alt": "Delicious", "audio": "oishii.m4a"},
            # page 2 — adjectives / na-adjectives (text-only), reading order
            {"id": "shizukana", "japanese": "しずか（な）", "romaji": "shizuka(na)", "english": "quiet", "alt": "Quiet", "audio": "shizukana.m4a"},
            {"id": "takai", "japanese": "たかい", "romaji": "takai", "english": "expensive; tall", "alt": "Expensive", "audio": "takai.m4a"},
            {"id": "ookii", "japanese": "おおきい", "romaji": "ookii", "english": "big", "alt": "Big", "audio": "ookii.m4a"},
            {"id": "muzukashii", "japanese": "むずかしい", "romaji": "muzukashii", "english": "difficult", "alt": "Difficult", "audio": "muzukashii.m4a"},
            {"id": "omoshiroi", "japanese": "おもしろい", "romaji": "omoshiroi", "english": "interesting; fun", "alt": "Interesting", "audio": "omoshiroi.m4a"},
            {"id": "nigiyakana", "japanese": "にぎやか（な）", "romaji": "nigiyaka(na)", "english": "lively (busy)", "alt": "Lively", "audio": "nigiyakana.m4a"},
            {"id": "shinsetsuna", "japanese": "しんせつ（な）", "romaji": "shinsetsu(na)", "english": "kind", "alt": "Kind", "audio": "shinsetsuna.m4a"},
            {"id": "kireena", "japanese": "きれい（な）", "romaji": "kiree(na)", "english": "beautiful; clean", "alt": "Beautiful", "audio": "kireena.m4a"},
            {"id": "yuumeena", "japanese": "ゆうめい（な）", "romaji": "yuumee(na)", "english": "famous", "alt": "Famous", "audio": "yumeena.m4a"},
            {"id": "shoppai", "japanese": "しょっぱい", "romaji": "shoppai", "english": "salty", "alt": "Salty", "audio": "shoppai.m4a"},
            {"id": "hiroi", "japanese": "ひろい", "romaji": "hiroi", "english": "wide", "alt": "Wide", "audio": "hiroi.m4a"},
            {"id": "semai", "japanese": "せまい", "romaji": "semai", "english": "narrow", "alt": "Narrow", "audio": "semai.m4a"},
            # page 3 — text-only
            {"id": "totemo", "japanese": "とても", "romaji": "totemo", "english": "very much", "alt": "Very much", "audio": "totemo.m4a"},
            {"id": "amari", "japanese": "あまり", "romaji": "amari", "english": "not really", "alt": "Not really", "audio": "amari.m4a"},
        ],
    },
}

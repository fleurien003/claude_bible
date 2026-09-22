#!/usr/bin/env python3
"""One-time fetch: pull the full World English Bible (public domain, WEB)
from bible-api.com, chapter by chapter, matched book-for-book against our
Korean data/bible-ko-full.json (same 66-book canonical order) so the page
can show Korean/English side by side. Resumable — re-running skips any
book/chapter already written to the output file.
"""
import json
import os
import re
import sys
import time
import urllib.parse

import requests

BASE = "https://bible-api.com"
OUT_PATH = "/home/user/claude_bible/data/bible-en-web.json"
KO_PATH = "/home/user/claude_bible/data/bible-ko-full.json"

# same order as data/bible-ko-full.json (39 OT + 27 NT)
ENGLISH_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes",
    "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]

session = requests.Session()


def load_progress():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data):
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT_PATH)


def fetch_chapter(book_en, chapter, verse_count=None, retries=6):
    # Single-chapter books (Obadiah, Philemon, 2 John, 3 John, Jude): the API
    # treats "Book 1" as book+verse 1, not the whole chapter, for these —
    # a book:verse range is needed to get everything.
    if verse_count:
        ref = urllib.parse.quote(f"{book_en} {chapter}:1-{verse_count}")
    else:
        ref = urllib.parse.quote(f"{book_en} {chapter}")
    url = f"{BASE}/{ref}?translation=web"
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 404:
                return None  # past the last chapter of this book
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 0)) or (5 * (attempt + 1))
                print(f"    429 rate limited, {wait}초 대기 ({attempt+1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise
            print(f"    재시도 {attempt+1}/{retries} ({e})", file=sys.stderr)
            time.sleep(3)
    raise RuntimeError(f"{book_en} {chapter}: 재시도 소진 (429 지속)")


def main():
    with open(KO_PATH, encoding="utf-8") as f:
        ko_bible = json.load(f)
    if len(ko_bible) != len(ENGLISH_NAMES):
        raise RuntimeError(f"책 개수 불일치: 한글 {len(ko_bible)}권, 영어 {len(ENGLISH_NAMES)}권")

    out = load_progress()

    for ko_book, en_name in zip(ko_bible, ENGLISH_NAMES):
        ko_name = ko_book["korean"]
        n_chapters = len(ko_book["chapters"])
        book_entry = out.setdefault(ko_name, {"english": en_name, "chapters": {}})
        print(f"{ko_name} ({en_name}), {n_chapters}장", file=sys.stderr)

        for chapter in range(1, n_chapters + 1):
            if str(chapter) in book_entry["chapters"]:
                continue
            verse_count = len(ko_book["chapters"][chapter - 1]["verses"]) if n_chapters == 1 else None
            data = fetch_chapter(en_name, chapter, verse_count=verse_count)
            if data is None:
                print(f"  {en_name} {chapter} -> 404, 건너뜀", file=sys.stderr)
                continue
            verses = [
                {
                    "verseNum": str(v["verse"]),
                    "verse": re.sub(r"\s+", " ", v["text"]).strip(),
                }
                for v in data.get("verses", [])
            ]
            book_entry["chapters"][str(chapter)] = verses
            if chapter % 10 == 0:
                save_progress(out)
            time.sleep(0.6)

        save_progress(out)
        print(f"  저장됨 ({len(book_entry['chapters'])}/{n_chapters}장)", file=sys.stderr)

    total = sum(len(b["chapters"]) for b in out.values())
    print(f"완료: 총 {total}장", file=sys.stderr)


if __name__ == "__main__":
    main()

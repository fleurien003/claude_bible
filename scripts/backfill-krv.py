#!/usr/bin/env python3
"""One-time backfill: fetch missing 쉬운성경 chapters (시편51-150, 이사야51-66,
예레미야51-52) from hangl.net's 개역개정 board and merge them into the main
bible.json, tagged with translation='개역개정' so the gap is filled and
clearly marked. Not part of the daily pipeline — run once, commit the result.
"""
import json
import re
import time
import sys

import requests

BASE = "https://hangl.net"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

session = requests.Session()
session.headers.update({"User-Agent": UA})

TITLE_RE = re.compile(r"개역개정\s+(\S+)\s+0*(\d+)장")
NEXT_RE = re.compile(
    r'class="bd_rd_next[^"]*"\s+href="([^"]+)".*?<b>개역개정\s+(\S+)\s+0*(\d+)장</b>',
    re.S,
)
CONTENT_RE = re.compile(r'rhymix_content xe_content">(.*?)</div>', re.S)
VERSE_RE = re.compile(r"(\d+):(\d+)\s+(.*?)\s*(?=<br|$)", re.S)
LINK_RE = re.compile(r'href="/korkrv/(\d+)\?[^"]*"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def find_chapter_post(book_kr, chapter):
    """정확한 장 하나를 검색으로 찾는다. 책마다 장 번호 zero-padding
    자릿수가 달라서(시편 051, 이사야 51) 여러 폭으로 시도한다. 책 이름만
    검색하면 사이트가 결과를 최신 글(=장 번호가 큰 것) 위주로만 보여주고
    페이지네이션이 걸려서 50장 이전 장들이 안 보이는 문제가 있어, 반드시
    장 번호까지 포함해서 검색한다."""
    for width in (3, 2, 1):
        keyword = f"{book_kr} {chapter:0{width}d}"
        r = session.get(
            f"{BASE}/korkrv", params={"search_target": "title", "search_keyword": keyword}
        )
        r.raise_for_status()
        for post_id, inner in LINK_RE.findall(r.text):
            clean = TAG_RE.sub("", inner)
            m = re.search(r"개역개정\s*" + re.escape(book_kr) + r"\s*0*(\d+)장", clean)
            if m and int(m.group(1)) == chapter:
                return post_id
    return None


def search_start(book_kr, chapter):
    post_id = find_chapter_post(book_kr, chapter)
    if not post_id:
        raise RuntimeError(f"검색 결과 없음: {book_kr} {chapter}")
    return post_id


def fetch_chapter(post_id):
    r = session.get(f"{BASE}/korkrv/{post_id}")
    r.raise_for_status()
    html = r.text

    title_m = TITLE_RE.search(html)
    if not title_m:
        raise RuntimeError(f"제목 파싱 실패: post {post_id}")
    book_kr, chapter = title_m.group(1), int(title_m.group(2))

    content_m = CONTENT_RE.search(html)
    if not content_m:
        raise RuntimeError(f"본문 파싱 실패: post {post_id}")
    content = content_m.group(1)
    raw_verses = []
    for vm in VERSE_RE.finditer(content):
        vchapter, vnum, text = vm.groups()
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            raw_verses.append((vchapter, vnum, text))

    # 제목의 장 번호와 본문 절 앞의 장 번호가 어긋나는 게시물이 실제로
    # 있었음(제목 오타로 보임) — 본문 절 번호를 신뢰의 기준으로 삼는다.
    if raw_verses:
        from collections import Counter

        real_chapter = int(Counter(v[0] for v in raw_verses).most_common(1)[0][0])
        if real_chapter != chapter:
            print(
                f"  주의: post {post_id} 제목은 {chapter}장인데 본문은 {real_chapter}장 — 본문 기준으로 사용",
                file=sys.stderr,
            )
        chapter = real_chapter

    verses = [
        {"chapterNum": str(chapter), "verseNum": vnum, "verse": text}
        for _, vnum, text in raw_verses
    ]

    next_m = NEXT_RE.search(html)
    next_info = None
    if next_m:
        next_href, next_book, next_chapter = next_m.groups()
        next_id = next_href.rsplit("/", 1)[-1]
        next_info = (next_id, next_book, int(next_chapter))

    return book_kr, chapter, verses, next_info


def crawl_range(start_book, start_chapter, end_book, end_chapter):
    """Crawl chapters from start_book/start_chapter forward via next-links
    until end_book/end_chapter (inclusive) is reached. If the next-link
    chain skips or repeats a chapter (seen once on the live site), patch
    the gap with a direct search lookup instead of trusting the chain."""
    post_id = search_start(start_book, start_chapter)
    by_chapter = {}
    seen_ids = set()
    while True:
        if post_id in seen_ids:
            break
        seen_ids.add(post_id)
        book_kr, chapter, verses, next_info = fetch_chapter(post_id)
        print(f"  fetched {book_kr} {chapter}장 ({len(verses)}절)", file=sys.stderr)
        if book_kr == start_book and chapter not in by_chapter:
            by_chapter[chapter] = verses
        if book_kr == end_book and chapter == end_chapter:
            break
        if not next_info:
            raise RuntimeError(f"다음 링크 없음, {book_kr} {chapter}에서 중단")
        post_id, _, _ = next_info
        time.sleep(0.4)

    missing = [c for c in range(start_chapter, end_chapter + 1) if c not in by_chapter]
    if missing:
        print(f"  체인 순회에서 빠진 장 발견, 직접 검색으로 보강: {missing}", file=sys.stderr)
        for c in missing:
            post_id = find_chapter_post(start_book, c)
            if not post_id:
                raise RuntimeError(f"{start_book} {c}장을 어디서도 찾지 못함")
            _, fetched_chapter, verses, _ = fetch_chapter(post_id)
            print(f"  보강 fetched {start_book} {fetched_chapter}장 ({len(verses)}절)", file=sys.stderr)
            by_chapter[fetched_chapter] = verses
            time.sleep(0.4)

    return [(start_book, c, by_chapter[c]) for c in range(start_chapter, end_chapter + 1)]


def main():
    bible_path = "/root/.claude/uploads/fa6d517e-3055-5015-a58c-245d80d52035/c1f83aaf-bible.json"
    with open(bible_path, encoding="utf-8") as f:
        bible = json.load(f)

    jobs = [
        ("시편", 51, "시편", 150),
        ("이사야", 51, "이사야", 66),
        ("예레미야", 51, "예레미야", 52),
    ]

    filled = {}
    for start_book, start_ch, end_book, end_ch in jobs:
        print(f"크롤 시작: {start_book} {start_ch} -> {end_book} {end_ch}", file=sys.stderr)
        chapters = crawl_range(start_book, start_ch, end_book, end_ch)
        filled.setdefault(start_book, []).extend(chapters)

    added = 0
    for book in bible:
        name = book["korean"]
        if name not in filled:
            continue
        existing_nums = {c["chapterNum"] for c in book["chapters"]}
        for book_kr, chapter, verses in filled[name]:
            cnum = str(chapter)
            if cnum in existing_nums:
                continue
            book["chapters"].append(
                {"chapterNum": cnum, "translation": "개역개정", "verses": verses}
            )
            added += 1
        book["chapters"].sort(key=lambda c: int(c["chapterNum"]))

    print(f"총 {added}개 장 보강 완료", file=sys.stderr)

    out_path = "/home/user/claude_bible/data/bible-ko-full.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, separators=(",", ":"))
    print(f"저장: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

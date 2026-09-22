#!/usr/bin/env python3
"""전체 성경(한글/영어)을 장 단위 작은 파일로 쪼갠다 — 클라이언트가
매삼주오 통독 화면에서 그날 필요한 2~5개 장만 가져오면 되게, 7MB짜리
전체 파일을 통째로 내려받지 않아도 되게 하기 위함. 책 순서(1~66,
data/bible-ko-full.json 순서 그대로)와 장 번호로 파일명을 매긴다.
한 번 실행해서 커밋해두는 정적 산출물이며, 원본 데이터가 바뀌지 않는 한
다시 돌릴 필요 없다.
"""
import json
import os

KO_PATH = "data/bible-ko-full.json"
EN_PATH = "data/bible-en-web.json"
OUT_KO = "data/bible/ko"
OUT_EN = "data/bible/en"


def main():
    ko = json.load(open(KO_PATH, encoding="utf-8"))
    en = json.load(open(EN_PATH, encoding="utf-8"))

    os.makedirs(OUT_KO, exist_ok=True)
    os.makedirs(OUT_EN, exist_ok=True)

    book_index = {}  # korean name -> 1-based index, for reading-plan.json lookups
    count_ko = count_en = 0

    for i, book in enumerate(ko, start=1):
        name = book["korean"]
        book_index[name] = i
        en_book = en.get(name)

        for ch in book["chapters"]:
            cnum = int(ch["chapterNum"])
            fname = f"{i:02d}-{cnum:03d}.json"

            ko_out = {
                "book_kr": name,
                "chapter": cnum,
                "translation": ch.get("translation", "쉬운성경"),
                "verses": [{"n": v["verseNum"], "t": v["verse"]} for v in ch["verses"]],
            }
            with open(os.path.join(OUT_KO, fname), "w", encoding="utf-8") as f:
                json.dump(ko_out, f, ensure_ascii=False, separators=(",", ":"))
            count_ko += 1

            if en_book and str(cnum) in en_book["chapters"]:
                en_verses = en_book["chapters"][str(cnum)]
                en_out = {
                    "book_en": en_book["english"],
                    "chapter": cnum,
                    "verses": [{"n": v["verseNum"], "t": v["verse"]} for v in en_verses],
                }
                with open(os.path.join(OUT_EN, fname), "w", encoding="utf-8") as f:
                    json.dump(en_out, f, ensure_ascii=False, separators=(",", ":"))
                count_en += 1

    with open("data/bible/book-index.json", "w", encoding="utf-8") as f:
        json.dump(book_index, f, ensure_ascii=False, separators=(",", ":"))

    print(f"한글 {count_ko}장, 영어 {count_en}장 내보냄 -> {OUT_KO} / {OUT_EN}")


if __name__ == "__main__":
    main()

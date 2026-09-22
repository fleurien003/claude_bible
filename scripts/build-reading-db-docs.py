#!/usr/bin/env python3
"""매삼주오 통독 스케줄(data/reading-plan.json)과 장별 본문(data/bible/{ko,en})을
하루 단위로 미리 합쳐서, artifact의 db 컬렉션 'reading'에 그대로 넣을 수 있는
문서(JSON) 파일들을 만든다. 클라이언트는 이제 raw.githubusercontent.com을
fetch()하지 않고 이 db 문서 하나만 읽으면 그날 통독에 필요한 모든 본문을 얻는다.
한 번 실행해서 ArtifactData batch로 업로드하고 나면, 통독 스케줄 자체가
바뀌지 않는 한 다시 돌릴 필요 없다.
"""
import json
import os

OUT_DIR = "scratch/reading_docs"


def pad2(n):
    return f"{n:02d}"


def pad3(n):
    return f"{n:03d}"


def main():
    plan = json.load(open("data/reading-plan.json", encoding="utf-8"))
    os.makedirs(OUT_DIR, exist_ok=True)

    for day in plan:
        readings_out = []
        for r in day["readings"]:
            fname = f"{pad2(r['idx'])}-{pad3(r['chapter'])}.json"
            ko_path = os.path.join("data/bible/ko", fname)
            en_path = os.path.join("data/bible/en", fname)
            ko = json.load(open(ko_path, encoding="utf-8")) if os.path.exists(ko_path) else None
            en = json.load(open(en_path, encoding="utf-8")) if os.path.exists(en_path) else None
            readings_out.append({
                "track": r["track"],
                "idx": r["idx"],
                "book_kr": r["book_kr"],
                "book_en": r["book_en"],
                "chapter": r["chapter"],
                "translation": (ko or {}).get("translation", "쉬운성경"),
                "koVerses": (ko or {}).get("verses", []),
                "enVerses": (en or {}).get("verses", []),
            })
        doc = {"date": day["date"], "weekday": day["weekday"], "readings": readings_out}
        out_path = os.path.join(OUT_DIR, day["date"] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

    sizes = [os.path.getsize(os.path.join(OUT_DIR, day["date"] + ".json")) for day in plan]
    print(f"{len(plan)}개 문서 생성 -> {OUT_DIR}")
    print(f"최대 크기: {max(sizes)} bytes, 평균: {sum(sizes)//len(sizes)} bytes")
    over = [s for s in sizes if s > 256 * 1024]
    if over:
        print(f"경고: 256KiB 초과 문서 {len(over)}개!")


if __name__ == "__main__":
    main()

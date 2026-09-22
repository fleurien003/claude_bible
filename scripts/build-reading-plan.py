#!/usr/bin/env python3
"""매삼주오 통독(평일 3장, 주일 5장, 연 1독) 스케줄 생성기.
역사/예언서, 시가서, 신약 세 갈래를 비율대로 섞어서(largest-remainder
방식) 창세기부터 쭉 가면 레위기 언저리에서 지치는 문제를 피한다.
날짜 배정은 START_DATE부터 시작하고, 평일 3장 / 일요일 5장을 그 갈래
순서열에서 순서대로 뽑아 채운다. 언제든 다시 실행해서 재생성 가능
(순수 함수, 날짜만 바뀌면 됨) — 매일 자동 실행되는 파이프라인이 아니라
한 번 만들어서 커밋해두는 정적 스케줄이다.
"""
import datetime
import json
import sys

START_DATE = datetime.date(2026, 9, 22)  # 오늘부터 시작
WEISDOM_BOOKS = {"욥기", "시편", "잠언", "전도서", "아가"}


def load_tracks():
    ko = json.load(open("data/bible-ko-full.json", encoding="utf-8"))
    en = json.load(open("data/bible-en-web.json", encoding="utf-8"))

    track_a, track_b, track_c = [], [], []
    for i, book in enumerate(ko, start=1):
        name = book["korean"]
        testament = book["testament"]
        en_book = en[name]
        bucket = (
            track_c if testament == "NT" else track_b if name in WEISDOM_BOOKS else track_a
        )
        for ch in sorted(book["chapters"], key=lambda c: int(c["chapterNum"])):
            bucket.append(
                {
                    "idx": i,
                    "book_kr": name,
                    "book_en": en_book["english"],
                    "chapter": int(ch["chapterNum"]),
                }
            )
    return {"A": track_a, "B": track_b, "C": track_c}


def build_sequence(counts):
    """largest-remainder 비례 배분: 각 스텝마다 목표비율 대비 가장 뒤처진
    트랙을 골라, 같은 트랙이 몰아서 계속 나오지 않고 고르게 섞이게 한다."""
    total = sum(counts.values())
    taken = {k: 0 for k in counts}
    seq = []
    for i in range(1, total + 1):
        best_key, best_score = None, -1.0
        for k, c in counts.items():
            if taken[k] >= c:
                continue
            score = (c / total) * i - taken[k]
            if score > best_score:
                best_score, best_key = score, k
        seq.append(best_key)
        taken[best_key] += 1
    return seq


def main():
    tracks = load_tracks()
    counts = {k: len(v) for k, v in tracks.items()}
    seq = build_sequence(counts)
    pointers = {k: 0 for k in tracks}

    plan = []
    d = START_DATE
    i = 0
    total = len(seq)
    while i < total:
        n_slots = 5 if d.weekday() == 6 else 3  # Monday=0 ... Sunday=6
        day_readings = []
        for _ in range(n_slots):
            if i >= total:
                break
            track = seq[i]
            entry = tracks[track][pointers[track]]
            pointers[track] += 1
            day_readings.append({"track": track, **entry})
            i += 1
        plan.append({"date": d.isoformat(), "weekday": d.weekday(), "readings": day_readings})
        d += datetime.timedelta(days=1)

    out_path = "data/reading-plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, separators=(",", ":"))

    print(f"기간: {plan[0]['date']} ~ {plan[-1]['date']} ({len(plan)}일)", file=sys.stderr)
    print(f"총 {total}장, 트랙별: {counts}", file=sys.stderr)
    print(f"저장: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

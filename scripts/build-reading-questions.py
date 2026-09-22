#!/usr/bin/env python3
"""매삼주오 통독 스케줄의 하루치 본문(track A/B/C: 역사·예언서 / 시가서 / 신약)에 맞춰
그날 읽은 내용을 직접 가리키는 묵상 질문 2개를 만들어, db 'reading' 문서에 update로
얹을 작은 페이로드 파일들을 만든다. (본문 텍스트는 건드리지 않고 questions 필드만 추가한다.)
"""
import json
import os

OUT_DIR = "scratch/reading_questions"

TEMPLATES = {
    "A": [
        '오늘 {book} {chapter}장에서 일어난 일을 보라. 그 안의 순종 또는 불순종이 내 삶의 어느 지점과 닮아 있는가?',
        '오늘 {book} {chapter}장에서 하나님의 뜻과 사람의 판단이 어긋난 지점이 있다면 무엇인가? 나는 지금 어디서 그런 어긋남을 겪고 있는가?',
        '오늘 {book} {chapter}장의 인물이 하나님 앞에서 보인 태도는 무엇인가? 오늘 나는 그와 같은 자리에서 무엇을 선택하겠는가?',
    ],
    "B": [
        '오늘 {book} {chapter}장에서 마음에 가장 오래 머문 한 구절은 무엇이며, 그것이 지금 내 상황에 어떤 말을 건네는가?',
        '오늘 {book} {chapter}장이 노래하거나 가르치는 것을 내 언어로 다시 옮긴다면 어떻게 쓰겠는가?',
        '오늘 {book} {chapter}장의 말씀 중, 지금 내 마음의 근심이나 기쁨과 가장 가까이 맞닿은 구절은 어디인가?',
    ],
    "C": [
        '오늘 {book} {chapter}장에서 예수님(또는 본문 속 인물)의 말씀이나 행동 중, 오늘 하루 구체적으로 따라 해볼 수 있는 것은 무엇인가?',
        '오늘 {book} {chapter}장의 말씀이 내가 오늘 만날 사람이나 결정할 일에 어떻게 적용될 수 있는가?',
        '오늘 {book} {chapter}장에서 하나님 나라의 모습이 어떻게 그려지는가? 그 모습이 오늘 내가 살아가는 자리에서는 어떤 모습이어야 하는가?',
    ],
}


def make_question(track, book, chapter, variant_idx):
    tpl_list = TEMPLATES.get(track, TEMPLATES["A"])
    tpl = tpl_list[variant_idx % len(tpl_list)]
    return tpl.format(book=book, chapter=chapter)


def main():
    plan = json.load(open("data/reading-plan.json", encoding="utf-8"))
    os.makedirs(OUT_DIR, exist_ok=True)

    for i, day in enumerate(plan):
        readings = day["readings"]
        if not readings:
            continue
        first = readings[0]
        # 둘째 질문은 첫 읽을거리와 트랙(갈래)이 다른 첫 항목을 찾아 쓰고,
        # 다 같은 트랙뿐이면 마지막 항목을 다른 variant로 쓴다.
        other = next((r for r in readings[1:] if r["track"] != first["track"]), None) or readings[-1]
        q1 = make_question(first["track"], first["book_kr"], first["chapter"], i)
        variant_offset = i + 1 if other is not readings[-1] or other["track"] != first["track"] else i + 2
        q2 = make_question(other["track"], other["book_kr"], other["chapter"], variant_offset)

        out_path = os.path.join(OUT_DIR, day["date"] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"questions": [q1, q2]}, f, ensure_ascii=False, separators=(",", ":"))

    print(f"{len(plan)}개 질문 페이로드 생성 -> {OUT_DIR}")


if __name__ == "__main__":
    main()

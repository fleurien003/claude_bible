// 두란노 생명의삶(https://www.duranno.com/qt/view/bible.asp) 오늘의 QT를 긁어와
// data/qt/YYYY-MM-DD.json 으로 저장한다. GitHub Actions에서 매일 자동 실행된다.
import fs from 'node:fs';
import path from 'node:path';
import iconv from 'iconv-lite';
import * as cheerio from 'cheerio';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

function todayKST() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date());
  const get = (t) => parts.find((p) => p.type === t).value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

async function fetchHtml(date) {
  const url = `https://www.duranno.com/qt/view/bible.asp?qtDate=${date}`;
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  return iconv.decode(buf, 'euc-kr');
}

function textWithLineBreaks($, el) {
  const $clone = $(el).clone();
  $clone.find('br').replaceWith('\n');
  return $clone.text().replace(/[ \t]+/g, ' ').replace(/\n[ \t]+/g, '\n').trim();
}

function parse(html, date) {
  const $ = cheerio.load(html);
  const h1 = $('.font-size h1').first();
  const reference = h1.find('span').first().text().replace(/\s+/g, ' ').trim();
  const subtitle = h1.find('em').first().text().replace(/\s+/g, ' ').trim();
  const hymn = textWithLineBreaks($, $('.song.box p').eq(1));

  const sections = [];
  let current = null;
  $('.bible').first().children().each((_, el) => {
    const $el = $(el);
    if ($el.is('p.title')) {
      current = { title: $el.text().trim(), verses: [] };
      sections.push(current);
    } else if ($el.is('table')) {
      if (!current) { current = { title: '', verses: [] }; sections.push(current); }
      current.verses.push({
        num: $el.find('th').first().text().trim(),
        text: $el.find('td').first().text().replace(/\s+/g, ' ').trim(),
      });
    }
  });

  let helper = '';
  let prayer = '';
  $('.helper.box').each((_, el) => {
    const $el = $(el);
    const title = $el.find('p.title').first().text().trim();
    const body = textWithLineBreaks($, $el.find('p').eq(1));
    if (title.includes('묵상')) helper = body;
    if (title.includes('기도')) prayer = body;
  });

  return {
    date, reference, subtitle, hymn, sections, helper, prayer,
    source: 'duranno_livinglife',
    fetchedAt: new Date().toISOString(),
  };
}

async function main() {
  const date = process.argv[2] || todayKST();
  const fixture = process.env.QT_FIXTURE;
  const html = fixture ? fs.readFileSync(fixture, 'utf8') : await fetchHtml(date);
  const data = parse(html, date);

  if (!data.reference || data.sections.length === 0 || data.sections.every((s) => s.verses.length === 0)) {
    throw new Error(`파싱 실패: reference="${data.reference}", sections=${data.sections.length}`);
  }

  const outDir = path.join(process.cwd(), 'data', 'qt');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `${date}.json`);
  fs.writeFileSync(outFile, JSON.stringify(data, null, 2) + '\n', 'utf8');
  console.log(`저장 완료: ${outFile}`);
  console.log(`본문: ${data.reference} — ${data.subtitle}`);
}

main().catch((e) => {
  console.error('두란노 QT 수집 실패:', e.message);
  process.exit(1);
});

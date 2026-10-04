# Daily-news failure evidence

Observed on 2026-10-04 against the existing `SOURCE_URL`,
`https://60s.lylme.com/`. Read-only fetch returned a 2026 / 10月4日 header and
16 news list items: an unpublished-news notice followed by 15 headlines from
yesterday. The exact visible notice is:

> 今天的简讯未更新，下面是昨天的简讯！

Feeding the raw response to `_DailyPageParser` showed 16 items. Calling
`_page_for_today(html, date(2026, 10, 4))` reproduced
`Daily news page returned invalid headlines.` This is an upstream publication
delay exposing missing freshness handling, not evidence that arbitrary extra
headlines should be accepted.

Raw fetch: `curl --fail --silent --show-error --max-time 20 --max-filesize
2000000 https://60s.lylme.com/ --output /tmp/kisara-daily-news-20261004.html`.
The temporary file is diagnostic only; do not rely on it for permanent tests
or copy full copyrighted headline content into fixtures. Use the observed
notice with synthetic headlines in regression tests.

Final product decision: after the classification-only patch still blocked
deployed delivery, the user approved a labeled yesterday-news image. Current
PRD/design supersede rejection of this notice. Keep strict actual headline
validation and skip fallback cache publication so manual requests can update.

`src/kisara/bot/dispatcher.py:159` routes `news` and `brief`. The user clarified
that `/news` is the affected command and explicitly authorized implementation;
do not add `/daily-news` or modify routing/help just to add a spelling.

Baseline: `./hako python -m pytest tests/unit/test_daily_news.py -q`:
34 passed. Both reproduction and tests used the existing Docker wrapper;
no private config was loaded and no QQ message was sent.

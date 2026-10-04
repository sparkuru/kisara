# Implementation and validation

1. Recognize one exact notice and validate 15 actual headlines and today's date.
2. Extend page/result fields, warning rendering/text, and in-memory fallback
   image delivery without changing callers' method signatures.
3. Skip fallback HTML/PNG cache publication; discard/refetch cached fallback.
   Preserve published caching and independent previous result bytes.
4. Replace superseded rejection regressions with successful labeled output,
   repeated refetch, publication recovery, malformed-list, cached-fallback,
   and byte isolation tests. Add scheduler once-per-day fallback coverage.
5. Sync docs and main-owned storage spec, including manual updated-news fetch.
6. Run focused checks:
   `./hako python -m pytest tests/unit/test_daily_news.py tests/unit/test_news_push.py tests/unit/test_news_delivery.py tests/unit/test_dispatcher.py -q`.
7. Reviewer runs `./dev.sh --all -q`, reviews all result/cache/delivery data flow
   and changed artifacts, and checks `git diff --check`.
8. Main renders observed public HTML to an isolated temporary PNG using the
   existing Docker runtime and available CJK fonts, then visually checks the
   warning. No host toolchain or separate dev wrapper.
9. Update evidence and concrete commit plan; commit approval remains pending.
   No deployment/restart/live QQ validation is authorized.

Implementation agent owns service, news/push unit tests, operations/feature docs.
Main owns artifacts/specs; reviewer may fix local in-scope defects. Preserve
prior work rather than wholesale reverting it. No schema migration required.

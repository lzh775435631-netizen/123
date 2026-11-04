# Weibo monitor
Tracks six specified public Weibo UIDs. Attempts mobile public endpoint, optionally using WEIBO_COOKIE as a GitHub Actions secret. No password or cookie should ever be committed.

The first successful run establishes a baseline (does not treat old posts as new). `latest.json` stores the snapshot and errors, `state.json` keeps up to 1000 IDs per account for deduplication, and `history.jsonl` appends newly observed posts. GitHub's five-minute schedule is best-effort.

User timelines increasingly require authentication. Store a current `WEIBO_COOKIE` Actions secret containing at least `SUB` and `SUBP` from a logged-in weibo.com browser session. Never commit it. HTTP 403/418/432 or API `ok=-100` means the cookie is missing, expired, or rate-limited.

This is an experimental collector: Weibo may block requests or change endpoints. Check workflow logs before relying on alerts. No notification channel is configured yet.

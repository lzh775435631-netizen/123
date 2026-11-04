# Weibo monitor
Tracks six specified public Weibo UIDs. Attempts mobile public endpoint, optionally using WEIBO_COOKIE as a GitHub Actions secret. No password or cookie should ever be committed.

The first successful run establishes a baseline (does not treat old posts as new). latest.json records responses and errors. state.json deduplicates by post ID. GitHub Actions scheduled runs are best-effort, not guaranteed at exactly 5-minute intervals.

This is an experimental collector: Weibo may block requests or change endpoints. Check workflow logs before relying on alerts. No notification channel is configured yet.

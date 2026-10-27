# Douyin 48h Radar

Independent test service for validating a non-account Douyin search data source.

Seeds: 观看教程 / 观影教程 / 在哪看 / 后续.
Window: 0-48 hours.
No video downloading. Public metadata only.

Endpoints:
- GET /health
- GET /probe
- POST /run?max_pages=8

Secrets are stored only as Render environment variables.

# News Intelligence Workbench

一个完整的新闻情报工作台：新闻采集、分类、去重、搜索、收藏、已读、热点评分、事件聚合、趋势统计、每日简报、AI接口预留。

## 运行

### macOS / Windows
1. 安装 Python 3.11+
2. 在项目目录执行：
   `python -m venv .venv`
3. macOS/Linux：
   `source .venv/bin/activate`
   Windows：
   `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `python app.py`
6. 浏览器打开 `http://127.0.0.1:8000`

首次启动会自动建立 SQLite 数据库并写入少量演示新闻。点击“同步新闻”即可尝试抓取配置的 RSS。

## 新闻源

编辑 `sources.json`。RSS 是最稳妥的第一层来源；如果有合法的新闻 API，可以在后端增加 API 适配器。

## AI

`.env` 中可配置通用 OpenAI-compatible Chat Completions 接口：
AI_API_URL / AI_API_KEY / AI_MODEL。
如果为空，系统使用本地规则引擎完成分类、关键词、热度和简报，不依赖外部 AI。

## 生产部署

建议：
Nginx → Uvicorn/FastAPI → SQLite/PostgreSQL
定时任务每 5~10 分钟执行 `/api/sync`；生产环境可改为 Celery/cron。
新闻聚合只展示标题、短摘要、来源和原文链接，遵守新闻源的 RSS/API/版权条款。

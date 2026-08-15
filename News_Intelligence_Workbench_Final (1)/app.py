import os, re, json, hashlib, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
import feedparser, httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

BASE=Path(__file__).parent
DB=BASE/"news.db"
load_dotenv(BASE/".env")
app=FastAPI(title="News Intelligence Workbench")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

CATS=["全部","财经","经济","国际","政治","科技","AI","社会","体育","文化","健康","军事","汽车","房产","商业","娱乐"]
STOP=set("the and for with from that this news today are was were has have will into about over after before".split())

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS articles(
      id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT UNIQUE, title TEXT, summary TEXT,
      source TEXT, url TEXT, category TEXT, published_at TEXT, collected_at TEXT,
      keywords TEXT, score REAL DEFAULT 0, read INTEGER DEFAULT 0, saved INTEGER DEFAULT 0,
      event_key TEXT DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_cat_time ON articles(category,published_at);
    CREATE INDEX IF NOT EXISTS idx_score ON articles(score);
    """)
    if c.execute("select count(*) n from articles").fetchone()["n"]==0:
        demo=[
        ("全球市场重新评估主要央行政策路径，投资者关注资产配置变化","财经","财经观察"),
        ("多国领导人就最新国际议题举行会谈，各方释放进一步沟通信号","国际","环球新闻"),
        ("人工智能产业持续扩张，新一轮应用进入规模化落地阶段","AI","科技前沿"),
        ("最新经济数据公布，消费与企业活动呈现结构性变化","经济","经济观察"),
        ("芯片、云计算与AI基础设施成为科技产业关注重点","科技","产业研究"),
        ("城市公共服务数字化持续推进，多项便民措施陆续上线","社会","社会新闻"),
        ("传统文化与现代创意结合，文化消费出现新的表达方式","文化","文化频道"),
        ("重要赛事进入关键阶段，多支队伍公布最新阵容信息","体育","体育前线"),
        ]
        now=datetime.now(timezone.utc).isoformat()
        for i,(t,cat,src) in enumerate(demo):
            add_article(c,t,"这是演示摘要。同步真实 RSS 后会自动替换为新闻源提供的摘要。",src,"",cat,now)
    c.commit(); c.close()

def classify(text, fallback="国际"):
    rules={
      "AI":["artificial intelligence","ai ","大模型","人工智能","生成式","chatgpt","openai"],
      "科技":["technology","tech","chip","semiconductor","software","芯片","科技","机器人","云计算"],
      "财经":["business","markets","stocks","finance","market","股市","金融","市场","投资"],
      "经济":["economy","economic","inflation","gdp","就业","经济","通胀","消费"],
      "政治":["government","president","election","parliament","policy","政府","总统","选举","政策"],
      "国际":["world","international","ukraine","russia","china","global","国际","全球"],
      "体育":["sport","football","soccer","nba","tennis","体育","足球","篮球"],
      "健康":["health","medical","virus","healthcare","健康","医疗"],
      "文化":["culture","arts","book","film","文化","艺术","电影"],
      "汽车":["auto","car","vehicle","汽车","新能源车"],
      "房产":["housing","property","real estate","房产","房地产"],
      "军事":["military","defense","war","军方","军事","国防"],
      "社会":["society","community","crime","社会","社区"],
      "娱乐":["entertainment","celebrity","music","娱乐","明星"]
    }
    s=text.lower()
    for cat,keys in rules.items():
        if any(k.lower() in s for k in keys): return cat
    return fallback

def keywords(title, summary):
    words=re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,}", (title+" "+summary).lower())
    out=[]
    for w in words:
        if w in STOP or w in out: continue
        out.append(w)
    return out[:8]

def score(title, summary, published):
    hot=["breaking","urgent","latest","major","war","election","crisis","ai","人工智能","重大","突发","政策","市场"]
    s=35+sum(8 for x in hot if x in (title+" "+summary).lower())
    return min(99,s)

def add_article(c,title,summary,source,url,category,published):
    h=hashlib.sha256((title.strip().lower()+source).encode()).hexdigest()
    cat=classify(title+" "+summary,category)
    kws=keywords(title,summary)
    sc=score(title,summary,published)
    event=" ".join(kws[:3])
    c.execute("""INSERT OR IGNORE INTO articles
      (hash,title,summary,source,url,category,published_at,collected_at,keywords,score,event_key)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (h,title,summary or "",source,url or "",cat,published,datetime.now(timezone.utc).isoformat(),json.dumps(kws,ensure_ascii=False),sc,event))
    return c.rowcount

async def sync_sources():
    srcs=json.loads((BASE/"sources.json").read_text(encoding="utf8"))
    c=db(); added=0; errors=[]
    for s in srcs:
        try:
            async with httpx.AsyncClient(timeout=15,follow_redirects=True,headers={"User-Agent":"NewsHub/1.0"}) as client:
                r=await client.get(s["url"]); r.raise_for_status()
            feed=feedparser.parse(r.content)
            for e in feed.entries[:50]:
                title=(getattr(e,"title","") or "").strip()
                if not title: continue
                raw=getattr(e,"summary","") or getattr(e,"description","") or ""
                summary=BeautifulSoup(raw,"html.parser").get_text(" ",strip=True)[:500]
                published=getattr(e,"published","") or getattr(e,"updated","") or datetime.now(timezone.utc).isoformat()
                added+=add_article(c,title,summary,s["name"],getattr(e,"link",""),s.get("category","国际"),published)
        except Exception as ex:
            errors.append({"source":s["name"],"error":str(ex)})
    c.commit(); c.close()
    return {"added":added,"errors":errors,"time":datetime.now(timezone.utc).isoformat()}

@app.on_event("startup")
def startup(): init()

@app.get("/")
def home(): return FileResponse(BASE/"static/index.html")

@app.get("/api/categories")
def categories(): return {"categories":CATS}

@app.get("/api/news")
def news(category="全部",q="",sort="latest",page:int=1,limit:int=30):
    c=db(); where=[]; args=[]
    if category!="全部": where.append("category=?"); args.append(category)
    if q:
        where.append("(title LIKE ? OR summary LIKE ? OR source LIKE ? OR keywords LIKE ?)")
        x=f"%{q}%"; args += [x,x,x,x]
    w=(" WHERE "+" AND ".join(where)) if where else ""
    order="score DESC, published_at DESC" if sort=="hot" else "published_at DESC"
    total=c.execute("select count(*) n from articles"+w,args).fetchone()["n"]
    rows=c.execute(f"select * from articles{w} order by {order} limit ? offset ?",args+[limit,(page-1)*limit]).fetchall()
    return {"total":total,"items":[dict(r) for r in rows]}

@app.get("/api/hot")
def hot(limit:int=10):
    c=db(); rows=c.execute("select * from articles order by score desc,published_at desc limit ?",(limit,)).fetchall()
    return {"items":[dict(r) for r in rows]}

@app.get("/api/stats")
def stats():
    c=db()
    total=c.execute("select count(*) n from articles").fetchone()["n"]
    saved=c.execute("select count(*) n from articles where saved=1").fetchone()["n"]
    unread=c.execute("select count(*) n from articles where read=0").fetchone()["n"]
    cats=[dict(r) for r in c.execute("select category,count(*) n from articles group by category order by n desc")]
    return {"total":total,"saved":saved,"unread":unread,"categories":cats}

@app.post("/api/article/{id}/save")
def save(id:int):
    c=db(); c.execute("update articles set saved=1-saved where id=?",(id,)); c.commit()
    return {"ok":True}

@app.post("/api/article/{id}/read")
def read(id:int):
    c=db(); c.execute("update articles set read=1 where id=?",(id,)); c.commit()
    return {"ok":True}

@app.post("/api/sync")
async def sync(): return await sync_sources()

@app.get("/api/digest")
def digest():
    c=db(); rows=c.execute("select * from articles order by score desc,published_at desc limit 10").fetchall()
    items=[dict(r) for r in rows]
    return {"title":"今日新闻简报","summary":"基于当前聚合新闻自动生成的热点摘要。生产环境可接入AI模型进一步生成事件时间线、影响分析和多观点总结。","top":items}

init()

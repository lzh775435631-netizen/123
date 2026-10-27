import json
import os, re, time
from datetime import datetime, timezone
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
import asyncio

app=FastAPI(title="Douyin 48h Radar")
BASE=os.getenv("SANDBASE_BASE_URL","https://api.sandbase.ai")
KEY=os.getenv("SANDBASE_API_KEY","")
SEEDS=["观看教程","观影教程","在哪看","后续"]

def headers():
    if not KEY: raise HTTPException(503,"SANDBASE_API_KEY missing")
    return {"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}

@app.get("/health")
def health():
    return {"ok":True,"key_configured":bool(KEY),"seeds":SEEDS,"window_hours":48}

@app.get("/probe")
async def probe():
    if not KEY: raise HTTPException(503,"SANDBASE_API_KEY missing")
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.get(BASE,headers=headers())
        return {"dns_http_reachable":True,"status":r.status_code,"base":BASE}
    except Exception as e:
        return {"dns_http_reachable":False,"error":type(e).__name__+": "+str(e),"base":BASE}

# Endpoint path/body are configurable until live API response is verified.
SEARCH_PATH=os.getenv("SANDBASE_SEARCH_PATH","/v1/api/douyin/search/video-search-v2")

def extract_items(data:Any):
    if isinstance(data,list): return data
    if not isinstance(data,dict): return []
    for path in [("data","data"),("data","items"),("data","aweme_list"),("data",),("items",),("aweme_list",)]:
        x=data
        ok=True
        for k in path:
            if isinstance(x,dict) and k in x: x=x[k]
            else: ok=False; break
        if ok and isinstance(x,list): return x
    return []

def getv(d,*keys):
    for k in keys:
        if isinstance(d,dict) and d.get(k) is not None:return d.get(k)
    return None

@app.get("/run")
@app.post("/run")
async def run(max_pages:int=8):
    if max_pages<1 or max_pages>30: raise HTTPException(400,"max_pages 1..30")
    cutoff=time.time()-48*3600
    raw=[]; errors=[]
    async with httpx.AsyncClient(timeout=30) as c:
        for keyword in SEEDS:
            cursor=0; search_id=None; backtrace=None
            for page in range(max_pages):
                body={"keyword":keyword,"cursor":cursor,"sort_type":"2","publish_time":"2"}
                if search_id: body["search_id"]=search_id
                if backtrace is not None: body["backtrace"]=backtrace
                try:
                    r=await c.post(BASE+SEARCH_PATH,headers=headers(),json=body)
                    if r.status_code>=400:
                        errors.append({"keyword":keyword,"page":page+1,"status":r.status_code,"body":r.text[:500]}); break
                    data=r.json(); items=extract_items(data)
                    if not items: break
                    for it in items:
                        ts=getv(it,"create_time","publish_time","timestamp")
                        try: ts=float(ts or 0)
                        except: ts=0
                        if ts and ts>=cutoff: raw.append({"seed":keyword,"item":it})
                    container=data.get("data",data) if isinstance(data,dict) else {}
                    if not isinstance(container,dict): break
                    has_more=container.get("has_more")
                    cursor=container.get("cursor",container.get("next_cursor",cursor))
                    search_id=container.get("search_id",search_id)
                    backtrace=container.get("backtrace",backtrace)
                    if has_more in (False,0,"0",None): break
                except Exception as e:
                    errors.append({"keyword":keyword,"page":page+1,"error":type(e).__name__+": "+str(e)}); break
    uniq={}
    for row in raw:
        it=row["item"]; aid=str(getv(it,"aweme_id","id","video_id") or "")
        key=aid or str(hash(str(it)))
        uniq[key]=row
    return {"window_hours":48,"seeds":SEEDS,"raw_in_window":len(raw),"unique_in_window":len(uniq),"errors":errors,"sample":list(uniq.values())[:20]}


@app.on_event("startup")
async def auto_run_on_startup():
    if os.getenv("AUTO_RUN","1") != "1":
        return
    async def job():
        await asyncio.sleep(3)
        try:
            result = await run(max_pages=int(os.getenv("AUTO_MAX_PAGES","8")))
            print("RADAR_RESULT_START", flush=True)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            print("RADAR_RESULT_END", flush=True)
        except Exception as e:
            print("RADAR_ERROR", repr(e), flush=True)
    asyncio.create_task(job())

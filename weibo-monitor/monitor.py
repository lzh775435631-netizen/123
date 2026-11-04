import os, json, time, urllib.request, urllib.parse, datetime, pathlib
UIDS = ["7877681517","7786328008","7867345199","7364841355","5574460906","2945603301"]
ROOT = pathlib.Path(__file__).resolve().parent
STATE = ROOT / "state.json"
OUT = ROOT / "latest.json"
COOKIE = os.environ.get("WEIBO_COOKIE", "")
def fetch(uid):
    url = "https://m.weibo.cn/api/container/getIndex?" + urllib.parse.urlencode({"type":"uid","value":uid,"containerid":"107603"+uid,"page":1})
    headers={"User-Agent":"Mozilla/5.0 (compatible; WeiboMonitor/1.0)","Referer":"https://m.weibo.cn/u/"+uid,"Accept":"application/json"}
    if COOKIE: headers["Cookie"]=COOKIE
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=20) as response:
        obj=json.load(response)
    if obj.get("ok") != 1: raise RuntimeError("Weibo response not successful: "+str(obj.get("msg",obj.get("ok"))))
    cards=obj.get("data",{}).get("cards",[])
    posts=[]
    for card in cards:
        for item in ([card] if card.get("mblog") else card.get("card_group",[])):
            m=item.get("mblog")
            if not m: continue
            posts.append({"id":str(m.get("id","")),"uid":uid,"created_at":m.get("created_at"),"text":m.get("text"),"reposts_count":m.get("reposts_count"),"comments_count":m.get("comments_count"),"attitudes_count":m.get("attitudes_count"),"url":"https://m.weibo.cn/detail/"+str(m.get("id","")),"pics":[p.get("large",{}).get("url") for p in m.get("pics",[])],"user_name":m.get("user",{}).get("screen_name")})
    return posts
def main():
    old=json.loads(STATE.read_text()) if STATE.exists() else {}
    state=dict(old); results={}; new=[]; errors={}
    for uid in UIDS:
        try:
            posts=fetch(uid)
            results[uid]=posts
            previous=set(old.get(uid,[]))
            if previous:
                new.extend(p for p in posts if p["id"] not in previous)
            state[uid]=list(dict.fromkeys([p["id"] for p in posts]+old.get(uid,[])))[:500]
            print(uid,"posts:",len(posts),"new:",sum(p["id"] not in previous for p in posts) if previous else 0)
        except Exception as exc:
            errors[uid]=str(exc)
            print(uid,"ERROR:",str(exc))
        time.sleep(2)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.write_text(json.dumps({"checked_at":now,"accounts":results,"new_posts":new,"errors":errors},ensure_ascii=False,indent=2))
    if results: STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    if errors: raise SystemExit("Some accounts failed; see latest.json")
if __name__=="__main__": main()

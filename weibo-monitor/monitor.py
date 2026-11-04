import datetime, html, json, os, pathlib, re, time, urllib.error, urllib.parse, urllib.request

UIDS = ["7877681517", "7786328008", "7867345199", "7364841355", "5574460906", "2945603301"]
ROOT = pathlib.Path(__file__).resolve().parent
STATE, OUT, HISTORY = ROOT / "state.json", ROOT / "latest.json", ROOT / "history.jsonl"
COOKIE = os.environ.get("WEIBO_COOKIE", "").strip()

def clean_text(value):
    value = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

def request_json(url, uid):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Referer": f"https://m.weibo.cn/u/{uid}", "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "MWeibo-Pwa": "1", "X-Requested-With": "XMLHttpRequest",
    }
    if COOKIE: headers["Cookie"] = COOKIE
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read(500).decode("utf-8", "replace")
        hint = " (Weibo risk control; refresh WEIBO_COOKIE with SUB/SUBP)" if exc.code in (403, 418, 432) else ""
        raise RuntimeError(f"HTTP {exc.code}{hint}; body={body!r}") from exc

def fetch(uid):
    query = urllib.parse.urlencode({"type": "uid", "value": uid, "containerid": "107603" + uid, "page": 1})
    obj = request_json("https://m.weibo.cn/api/container/getIndex?" + query, uid)
    if obj.get("ok") != 1:
        hint = "; valid WEIBO_COOKIE (SUB/SUBP) required" if obj.get("ok") == -100 else ""
        raise RuntimeError(f"Weibo ok={obj.get('ok')}, msg={obj.get('msg')!r}{hint}")
    posts = []
    for card in obj.get("data", {}).get("cards", []):
        for item in ([card] if card.get("mblog") else card.get("card_group", [])):
            m = item.get("mblog")
            if not m: continue
            post_id = str(m.get("id", ""))
            pics = [(p.get("large") or {}).get("url") or p.get("url") for p in (m.get("pics") or [])]
            posts.append({"id": post_id, "uid": uid, "user_name": (m.get("user") or {}).get("screen_name"),
                "created_at": m.get("created_at"), "text": clean_text(m.get("text")),
                "url": "https://m.weibo.cn/detail/" + post_id, "pics": [p for p in pics if p],
                "reposts_count": m.get("reposts_count", 0), "comments_count": m.get("comments_count", 0),
                "attitudes_count": m.get("attitudes_count", 0)})
    if not posts: raise RuntimeError("successful response contained no post cards")
    return posts

def main():
    print(f"Starting: accounts={len(UIDS)} cookie={'present' if COOKIE else 'missing'}", flush=True)
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    state, results, new_posts, errors = dict(old), {}, [], {}
    for uid in UIDS:
        try:
            posts = fetch(uid); results[uid] = posts; previous = set(old.get(uid, []))
            fresh = [p for p in posts if p["id"] not in previous] if previous else []
            new_posts.extend(fresh)
            state[uid] = list(dict.fromkeys([p["id"] for p in posts] + old.get(uid, [])))[:1000]
            print(f"{uid} OK posts={len(posts)} new={len(fresh)} latest={posts[0]['id']}", flush=True)
        except Exception as exc:
            errors[uid] = str(exc); print(f"{uid} ERROR {exc}", flush=True)
        time.sleep(1)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.write_text(json.dumps({"checked_at": now, "cookie_configured": bool(COOKIE), "accounts": results,
        "new_posts": new_posts, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    if results: STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    if new_posts:
        with HISTORY.open("a", encoding="utf-8") as stream:
            for post in new_posts: stream.write(json.dumps({"collected_at": now, **post}, ensure_ascii=False) + "\n")
    print(f"Finished: successful={len(results)} failed={len(errors)} new={len(new_posts)}", flush=True)
    if errors: raise SystemExit(1)

if __name__ == "__main__": main()

import os
import random
import time
import hashlib
import hmac
import base64
import urllib.parse
import requests
import yaml
import feedparser

# Load topics from topics.yaml (edit that file to change categories/keywords)
with open("topics.yaml", "r", encoding="utf-8") as f:
    TOPICS = yaml.safe_load(f)

# Categories come from topics.yaml keys if present; otherwise use defaults
CATEGORIES = list(TOPICS.keys()) if isinstance(TOPICS, dict) and TOPICS else [
    "politics", "currency", "tech", "ai", "current_affairs",
    "hollywood", "bollywood", "formula_one", "social_challenge",
    "world_tension", "world_affairs", "new_cars", "auto_tech"
]

# RSS and news feeds per category (no auth required; always respect site terms)
FEEDS = {
    "politics": [
        "https://news.google.com/rss/search?q=politics&hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "currency": [
        "https://news.google.com/rss/search?q=forex%20OR%20currency%20OR%20exchange%20rate&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.reuters.com/markets/currencies/rss",
    ],
    "tech": [
        "https://news.google.com/rss/search?q=technology&hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.theverge.com/rss/index.xml",
    ],
    "ai": [
        "https://news.google.com/rss/search?q=artificial%20intelligence%20OR%20AI%20OR%20machine%20learning&hl=en-IN&gl=IN&ceid=IN:en",
        "https://venturebeat.com/category/ai/feed",
        "https://feeds.feedburner.com/thenextweb",
    ],
    "current_affairs": [
        "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.reuters.com/world/rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "hollywood": [
        "https://news.google.com/rss/search?q=Hollywood&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.hollywoodreporter.com/feed/",
        "https://variety.com/feed/",
    ],
    "bollywood": [
        "https://news.google.com/rss/search?q=Bollywood&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.hindustantimes.com/feeds/rss/bollywood/rssfeed.xml",
        "https://indianexpress.com/section/entertainment/bollywood/feed/",
    ],
    "formula_one": [
        "https://news.google.com/rss/search?q=Formula%20One%20OR%20F1&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.formula1.com/content/fom-website/en/latest/all.xml",
        "https://www.motorsport.com/rss/f1/news/",
    ],
    "social_challenge": [
        "https://news.google.com/rss/search?q=%22social%20media%22%20trend%20OR%20challenge&hl=en-IN&gl=IN&ceid=IN:en",
        "https://mashable.com/feeds/rss/all",
    ],
    "world_tension": [
        "https://news.google.com/rss/search?q=conflict%20OR%20sanctions%20OR%20ceasefire%20OR%20military%20escalation&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.reuters.com/world/rss",
    ],
    "world_affairs": [
        "https://news.google.com/rss/search?q=diplomacy%20OR%20summit%20OR%20bilateral%20talks%20OR%20treaty&hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "new_cars": [
        "https://news.google.com/rss/search?q=new%20car%20launch%20OR%20EV%20OR%20hybrid&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.autocarindia.com/rss",
        "https://www.cartoq.com/feed/",
    ],
    "auto_tech": [
        "https://news.google.com/rss/search?q=ADAS%20OR%20battery%20technology%20OR%20charging%20infrastructure%20OR%20infotainment%20OR%20Lidar&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.electrive.com/feed/",
    ],
}

MAX_TWEET = 280

def sanitize(text: str) -> str:
    return " ".join((text or "").split())

def pick_category() -> str:
    # Rotate deterministically by hour to balance topics
    epoch_hour = int(time.time() // 3600)
    return CATEGORIES[epoch_hour % len(CATEGORIES)] if CATEGORIES else "current_affairs"

def gather_items(category: str):
    items = []
    for url in FEEDS.get(category, []):
        try:
            feed = feedparser.parse(url)
            src = sanitize(getattr(feed.feed, "title", "") or "News")
            for e in feed.entries[:10]:
                title = sanitize(getattr(e, "title", "") or "")
                link = sanitize(getattr(e, "link", "") or "")
                if title:
                    items.append({"title": title, "link": link, "source": src})
        except Exception:
            continue
    # Deduplicate by title hash
    seen = set()
    unique = []
    for it in items:
        h = hashlib.sha256(it["title"].encode("utf-8")).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(it)
    return unique

# --------- Minimal, formal, no-link formatting ---------

def rewrite_title(title: str, category: str) -> str:
    """Rewrite headline to a concise, formal sentence with no links."""
    t = (title or "").strip()
    # Drop trailing " - Source"
    if " - " in t:
        t = t.split(" - ").strip()
    # Remove hype prefixes
    replacements = {
        "BREAKING:": "",
        "BREAKING": "",
        "Watch:": "",
        "WATCH:": "",
        "Report:": "",
        "REPORT:": "",
        "Explained:": "",
        "EXPLAINED:": "",
        "Live:": "",
        "LIVE:": "",
    }
    for k, v in replacements.items():
        t = t.replace(k, v).strip()
    # Remove any accidental URLs
    t = t.replace("http://", "").replace("https://", "")
    # Capitalize start for formality
    if t:
        t = t.upper() + t[1:]
    return t

def build_post(item, category):
    """Return a minimal, formal post with 2–3 hashtags and NO URL."""
    tags = {
        "politics": ["#Politics", "#Policy"],
        "currency": ["#Markets", "#Forex"],
        "tech": ["#Tech", "#Innovation"],
        "ai": ["#AI", "#MachineLearning"],
        "current_affairs": ["#News", "#CurrentAffairs"],
        "hollywood": ["#Hollywood", "#Entertainment"],
        "bollywood": ["#Bollywood", "#Entertainment"],
        "formula_one": ["#F1", "#Motorsport"],
        "social_challenge": ["#Social", "#Trends"],
        "world_tension": ["#World", "#Geopolitics"],
        "world_affairs": ["#World", "#Diplomacy"],
        "new_cars": ["#Cars", "#Auto"],
        "auto_tech": ["#AutoTech", "#EVs"],
    }
    chosen = tags.get(category, ["#News", "#Update"])

    # Human, minimal, formal: rewrite headline; include no links at all
    text = rewrite_title(item.get("title", ""), category)

    # Prefer 3 hashtags if space allows, else 2
    hash_text_2 = " " + " ".join(chosen[:2])
    hash_text_3 = " " + " ".join(chosen[:3]) if len(chosen) >= 3 else hash_text_2

    if len(text + hash_text_3) <= MAX_TWEET:
        return text + hash_text_3
    if len(text + hash_text_2) <= MAX_TWEET:
        return text + hash_text_2

    # Trim title to fit with 2 hashtags
    room = MAX_TWEET - len(hash_text_2) - 1
    trimmed = (text[:room] + "…") if room > 0 else text[:279]
    return trimmed + hash_text_2

# --------- OAuth 1.0a user-context signing for X API v2 ---------

def percent_encode(s):
    return urllib.parse.quote(str(s), safe="~")

def oauth1_headers(method, url, params, consumer_key, consumer_secret, token, token_secret):
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": hashlib.sha256(os.urandom(32)).hexdigest(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    all_params = {**params, **oauth_params}
    param_str = "&".join(f"{percent_encode(k)}={percent_encode(all_params[k])}" for k in sorted(all_params))
    base_str = "&".join([method.upper(), percent_encode(url), percent_encode(param_str)])
    signing_key = "&".join([percent_encode(consumer_secret), percent_encode(token_secret)])
    signature = base64.b64encode(hmac.new(signing_key.encode(), base_str.encode(), 'sha1').digest()).decode()
    oauth_params["oauth_signature"] = signature
    auth_header = "OAuth " + ", ".join(f'{k}="{percent_encode(v)}"' for k, v in oauth_params.items())
    return {"Authorization": auth_header, "Content-Type": "application/json"}

def post_tweet(text):
    # Using X API v2 manage tweets endpoint with OAuth 1.0a user context
    url = "https://api.x.com/2/tweets"
    ck = os.environ["X_API_KEY"]
    cs = os.environ["X_API_SECRET"]
    at = os.environ["X_ACCESS_TOKEN"]
    ats = os.environ["X_ACCESS_TOKEN_SECRET"]
    headers = oauth1_headers("POST", url, {}, ck, cs, at, ats)
    resp = requests.post(url, json={"text": text}, headers=headers, timeout=20)
    if resp.status_code >= 300:
        raise RuntimeError(f"X API error {resp.status_code}: {resp.text}")
    return resp.json()

def main():
    category = pick_category()
    items = gather_items(category)
    if not items:
        print("No items found; skipping.")
        return
    pick_pool = items[:8] if len(items) >= 8 else items
    item = random.choice(pick_pool)
    post = build_post(item, category)
    print("Posting:", post)
    post_tweet(post)
    print("Posted OK")

if __name__ == "__main__":
    main()

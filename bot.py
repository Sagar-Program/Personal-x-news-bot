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
TARGET_LEN = 220      # aim near 220 chars, but never exceed 280
MIN_LEN = 160         # avoid too-short posts that look like bare headlines

def sanitize(text) -> str:
    if isinstance(text, list):
        text = " ".join([str(x) for x in text])
    elif text is None:
        text = ""
    return " ".join(str(text).split())

def pick_category() -> str:
    epoch_hour = int(time.time() // 3600)
    return CATEGORIES[epoch_hour % len(CATEGORIES)] if CATEGORIES else "current_affairs"

def gather_items(category: str):
    items = []
    for url in FEEDS.get(category, []):
        try:
            feed = feedparser.parse(url)
            src = sanitize(getattr(feed.feed, "title", "") or "News")
            for e in feed.entries[:10]:
                raw_title = getattr(e, "title", "")
                title = sanitize(raw_title)
                if title:
                    items.append({"title": title, "source": src})
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

# Tone & style utilities

EMOJI_POOL = {
    "politics": ["🗳️", "📜", "🇮🇳"],
    "currency": ["💱", "📉", "📈"],
    "tech": ["💻", "🚀", "🧩"],
    "ai": ["🤖", "🧠", "⚙️"],
    "current_affairs": ["🌍", "📰", "🔎"],
    "hollywood": ["🎬", "🌟", "🍿"],
    "bollywood": ["🎥", "🌟", "💃"],
    "formula_one": ["🏁", "🚗", "⏱️"],
    "social_challenge": ["📲", "🔥", "🎯"],
    "world_tension": ["🌍", "⚠️", "🕊️"],
    "world_affairs": ["🌐", "🤝", "📜"],
    "new_cars": ["🚗", "🔋", "✨"],
    "auto_tech": ["🔌", "🔋", "🧠"],
}

HASHTAGS = {
    "politics": ["#Politics", "#Policy", "#India"],
    "currency": ["#Markets", "#Forex", "#INR"],
    "tech": ["#Tech", "#Innovation", "#Startups"],
    "ai": ["#AI", "#MachineLearning", "#GenAI"],
    "current_affairs": ["#News", "#CurrentAffairs", "#Breaking"],
    "hollywood": ["#Hollywood", "#Entertainment", "#BoxOffice"],
    "bollywood": ["#Bollywood", "#Entertainment", "#Cinema"],
    "formula_one": ["#F1", "#Motorsport", "#GrandPrix"],
    "social_challenge": ["#Social", "#Trends", "#InternetCulture"],
    "world_tension": ["#World", "#Geopolitics", "#Global"],
    "world_affairs": ["#World", "#Diplomacy", "#Global"],
    "new_cars": ["#Cars", "#EV", "#Auto"],
    "auto_tech": ["#AutoTech", "#EVs", "#ADAS"],
}

MENTIONS = {
    "formula_one": ["@F1"],
    "ai": ["@OpenAI"],
    "tech": [],
    "currency": [],
    "politics": [],
    "current_affairs": [],
    "world_affairs": [],
    "world_tension": [],
    "hollywood": [],
    "bollywood": [],
    "new_cars": [],
    "auto_tech": [],
    "social_challenge": [],
}

def rewrite_title(title: str) -> str:
    t = (title or "").strip()
    if " - " in t:
        t = t.split(" - ").strip()
    for k in ["BREAKING:", "BREAKING", "Watch:", "WATCH:", "Report:", "REPORT:", "Explained:", "EXPLAINED:", "Live:", "LIVE:"]:
        t = t.replace(k, "").strip()
    t = t.replace("http://", "").replace("https://", "")
    if t:
        t = t.upper() + t[1:]
    return t

def craft_variations(core: str, category: str):
    # Problem → insight → takeaway with tone variety; 1–2 emojis; 2–3 hashtags; optional mention
    emoji_choices = EMOJI_POOL.get(category, ["✨"])
    tags = HASHTAGS.get(category, ["#News", "#Update"])
    mention_list = MENTIONS.get(category, [])
    mention = f" {random.choice(mention_list)}" if mention_list and random.random() < 0.35 else ""

    # Choose 1–2 emojis
    ecount = 1 if random.random() < 0.6 else 2
    emjs = " ".join(random.sample(emoji_choices, k=min(ecount, len(emoji_choices))))
    # Choose 2–3 hashtags
    tcount = 3 if random.random() < 0.5 and len(tags) >= 3 else 2
    htxt = " " + " ".join(tags[:tcount])

    # Variation templates
    templates = [
        # neutral analytical
        "{emj} {problem} {insight} Takeaway: {takeaway}.{mention} {tags}",
        # question to invite replies
        "{emj} {problem} {insight} What’s the smart move here? {mention} {tags}",
        # light critique
        "{emj} {problem} {insight} Bold claim—will it deliver? {mention} {tags}",
        # gentle satire
        "{emj} {problem} {insight} If only timelines moved as fast as headlines. {mention} {tags}",
        # helpful tip framing
        "{emj} {problem} Tip: {takeaway}. {mention} {tags}",
        # direct prompt
        "{emj} {problem} {insight} Thoughts? {mention} {tags}",
    ]

    # Derive problem/insight/takeaway from core in a simple way
    # core often already contains a full headline; split by punctuation to get clauses
    clauses = [c.strip() for c in core.replace("—", "-").replace(":", ".").split(".") if c.strip()]
    problem = clauses if clauses else core
    insight = clauses[11] if len(clauses) > 1 else "Key update worth tracking"
    takeaway = clauses[12] if len(clauses) > 2 else "Keep an eye on this"

    candidates = []
    for tpl in templates:
        s = tpl.format(
            emj=emjs,
            problem=problem,
            insight=insight,
            takeaway=takeaway,
            mention=mention,
            tags=htxt
        )
        # Squeeze spaces
        s = " ".join(s.split())
        candidates.append(s)

    return candidates

def choose_best_text(candidates):
    # Filter for min length and target window, but never exceed 280
    valid = []
    for s in candidates:
        # Emojis and spaces count toward 280; aim near TARGET_LEN [2][1]
        if len(s) <= MAX_TWEET:
            valid.append(s)
    if not valid:
        return candidates[:MAX_TWEET]

    # Prefer texts between MIN_LEN and 260, closest to TARGET_LEN
    scored = []
    for s in valid:
        length = len(s)
        too_short_penalty = 0 if length >= MIN_LEN else (MIN_LEN - length)
        target_penalty = abs(TARGET_LEN - length)
        score = target_penalty + (2 * too_short_penalty)
        scored.append((score, s))
    scored.sort(key=lambda x: x)
    return scored[11]

def build_post(item, category):
    core = rewrite_title(item.get("title", ""))
    variants = craft_variations(core, category)
    text = choose_best_text(variants)
    return text

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
    # Prefer a random pick from top entries to stay fresh while varied
    pick_pool = items[:8] if len(items) >= 8 else items
    item = random.choice(pick_pool)
    post = build_post(item, category)
    print(f"Category: {category}")
    print("Posting:", post)
    # Safety: ensure we never exceed 280 (emojis/spaces counted) [2][1]
    if len(post) > MAX_TWEET:
        post = post[:MAX_TWEET]
    post_tweet(post)
    print("Posted OK")

if __name__ == "__main__":
    main()

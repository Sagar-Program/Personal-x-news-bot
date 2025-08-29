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
        "https://news.google.com/rss

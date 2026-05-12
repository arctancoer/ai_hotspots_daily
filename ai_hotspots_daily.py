#!/usr/bin/env python3
"""Fetch AI hot topics from curated sources and write a daily top-10 report."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests


SOURCES = [
    ("OpenAI News", "https://openai.com/zh-Hans-CN/news/"),
    ("Anthropic News", "https://www.anthropic.com/news"),
    ("Gemini Latest News", "https://gemini.google/latest-news/"),
    ("Hugging Face Trending Papers", "https://huggingface.co/papers/trending"),
    ("机器之心", "https://www.jiqizhixin.com/"),
    ("量子位", "https://www.qbitai.com/"),
    ("IT之家 AI", "https://next.ithome.com/ai"),
    ("follow-builders", "https://github.com/zarazhangrui/follow-builders"),
]

AI_KEYWORDS = {
    "openai": 14,
    "chatgpt": 12,
    "gpt": 10,
    "claude": 12,
    "anthropic": 12,
    "gemini": 12,
    "google": 8,
    "deepmind": 8,
    "agent": 10,
    "智能体": 10,
    "codex": 9,
    "rag": 8,
    "多模态": 8,
    "multimodal": 8,
    "机器人": 7,
    "robot": 7,
    "模型": 7,
    "大模型": 9,
    "llm": 9,
    "ai": 6,
    "人工智能": 8,
    "生成式": 7,
    "embedding": 6,
    "推理": 6,
    "reasoning": 6,
    "融资": 5,
    "ipo": 5,
    "算力": 5,
    "compute": 5,
    "enterprise": 5,
    "企业": 5,
    "安全": 4,
    "safety": 4,
    "paper": 4,
    "论文": 4,
}

NOISE = {
    "login",
    "登录",
    "try chatgpt",
    "view all",
    "see more",
    "加载更多",
    "privacy",
    "terms",
    "subscribe",
    "立即下载",
    "rss",
    "github",
    "readme",
}


@dataclass(frozen=True)
class Item:
    title: str
    url: str
    source: str
    score: int


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._href: str | None = None
        self._parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._href = urljoin(self.base_url, href)
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._href:
            return
        text = normalize_text(" ".join(self._parts))
        if text:
            self.links.append((text, self._href))
        self._href = None
        self._parts = []


def normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n-|·")


def fetch(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AIHotspotsBot/1.0; "
            "+https://github.com/zarazhangrui/follow-builders)"
        )
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def extract_links(page_html: str, base_url: str) -> list[tuple[str, str]]:
    parser = LinkExtractor(base_url)
    parser.feed(page_html)
    return parser.links


def is_probably_topic(title: str, url: str) -> bool:
    lower = title.lower()
    if len(title) < 8 or len(title) > 180:
        return False
    if any(token in lower for token in NOISE):
        return False
    if not any(token in lower for token in AI_KEYWORDS):
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    return True


def score_item(title: str, url: str, source: str) -> int:
    lower = title.lower()
    score = 0
    for keyword, weight in AI_KEYWORDS.items():
        if keyword in lower:
            score += weight
    if re.search(r"2026|5月|may|昨天|今天|小时前|刚刚", lower):
        score += 8
    if source in {"OpenAI News", "Anthropic News", "Gemini Latest News"}:
        score += 7
    if source in {"量子位", "IT之家 AI"}:
        score += 4
    if "trending" in url or "papers" in url:
        score += 4
    if any(marker in lower for marker in ["发布", "launch", "introducing", "announces", "推出"]):
        score += 5
    if any(marker in lower for marker in ["融资", "ipo", "acquire", "收购", "估值"]):
        score += 4
    return score


def collect_items() -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    errors: list[str] = []
    seen: set[str] = set()

    for source, url in SOURCES:
        try:
            page = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and keep the digest moving.
            errors.append(f"{source}: {exc}")
            continue

        for title, link in extract_links(page, url):
            title = normalize_text(title)
            if not is_probably_topic(title, link):
                continue
            key = re.sub(r"\W+", "", title.lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            items.append(Item(title, link, source, score_item(title, link, source)))

    items.sort(key=lambda item: item.score, reverse=True)
    return items, errors


def summarize(items: Iterable[Item], errors: list[str], top_n: int) -> str:
    now = dt.datetime.now().astimezone()
    top_items = list(items)[:top_n]
    lines = [
        f"# AI 热点 Top {top_n}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        "- 信源：OpenAI、Anthropic、Gemini、Hugging Face、机器之心、量子位、IT之家、follow-builders",
        "",
    ]

    if not top_items:
        lines.append("未抓取到候选热点，请检查网络或源站结构是否变化。")
    else:
        for index, item in enumerate(top_items, start=1):
            lines.extend(
                [
                    f"## {index}. {item.title}",
                    "",
                    f"- 来源：{item.source}",
                    f"- 热度分：{item.score}",
                    f"- 链接：{item.url}",
                    "",
                ]
            )

    if errors:
        lines.extend(["## 抓取异常", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    return "\n".join(lines)


def post_webhook(markdown: str) -> None:
    webhook_url = os.getenv("AI_HOTSPOTS_WEBHOOK_URL")
    if not webhook_url:
        return
    payload = {
        "username": os.getenv("AI_HOTSPOTS_WEBHOOK_USERNAME", "AI热点机器人"),
        "channel": os.getenv("AI_HOTSPOTS_WEBHOOK_CHANNEL", ""),
        "text": markdown[:15000],
    }
    response = requests.post(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-n", type=int, default=10, help="number of topics to keep")
    parser.add_argument(
        "--output-dir",
        default="ai_hotspots_reports",
        help="directory for generated markdown reports",
    )
    parser.add_argument("--no-webhook", action="store_true", help="skip webhook delivery")
    args = parser.parse_args()

    items, errors = collect_items()
    report = summarize(items, errors, args.top_n)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    output_file = output_dir / f"ai-hotspots-{today}.md"
    output_file.write_text(report, encoding="utf-8")

    latest_file = output_dir / "latest.md"
    latest_file.write_text(report, encoding="utf-8")

    if not args.no_webhook:
        post_webhook(report)

    print(f"Wrote {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

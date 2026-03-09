import json
import time
from typing import List, Dict, Optional
import config.config as cfg
from duckduckgo_search import DDGS


class SearchResult:
    def __init__(self, title: str, url: str, content: str):
        self.title = title
        self.url = url
        self.content = content

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content
        }


class WebSearcher:
    def __init__(self):
        self.enabled = cfg.SEARCH_ENABLED
        self.result_count = cfg.SEARCH_RESULT_COUNT

    def search(self, query: str) -> List[SearchResult]:
        if not self.enabled:
            return []

        if not query or not query.strip():
            return []

        try:
            return self._do_search(query)
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def _do_search(self, query: str) -> List[SearchResult]:
        results = []

        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=self.result_count):
                    results.append(SearchResult(
                        title=r.get('title', ''),
                        url=r.get('url', ''),
                        content=r.get('body', '')
                    ))
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            results.append(SearchResult(
                title=f"搜索结果: {query}",
                url="",
                content=f"搜索出错: {str(e)}"
            ))

        return results[:self.result_count]

    def format_results(self, results: List[SearchResult]) -> str:
        if not results:
            return ""

        formatted = "\n📚 联网搜索补充信息：\n"
        for i, r in enumerate(results, 1):
            formatted += f"\n{i}. {r.title}\n"
            if r.url:
                formatted += f"   链接: {r.url}\n"
            if r.content:
                formatted += f"   {r.content[:150]}...\n"

        return formatted


_searcher_instance = None


def get_searcher() -> WebSearcher:
    global _searcher_instance
    if _searcher_instance is None:
        _searcher_instance = WebSearcher()
    return _searcher_instance

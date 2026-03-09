import json
import os
import jieba
from typing import List, Dict, Tuple
import config.config as cfg


class FAQMatcher:
    def __init__(self, data_path: str = None):
        self.data_path = data_path or cfg.FAQ_DATA_PATH
        self.threshold = cfg.FAQ_MATCH_THRESHOLD
        self.faq_data = []
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.faq_data = json.load(f)
        else:
            raise FileNotFoundError(f"FAQ data file not found: {self.data_path}")

    def reload(self):
        self._load_data()

    def _tokenize(self, text: str) -> set:
        words = set(jieba.cut(text))
        return {w.lower() for w in words if len(w) > 0}

    def _calculate_similarity(self, question1: str, question2: str) -> float:
        tokens1 = self._tokenize(question1)
        tokens2 = self._tokenize(question2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0

    def _keyword_match(self, question: str, keywords: List[str]) -> float:
        question_lower = question.lower()
        max_score = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in question_lower:
                score = len(keyword_lower) / len(question_lower)
                score = min(score, 1.0)
                max_score = max(max_score, score)

        return max_score

    def match(self, question: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
        if not question or not question.strip():
            return []
        
        results = []
        
        for faq in self.faq_data:
            similarity = self._calculate_similarity(question, faq.get('question', ''))
            keyword_score = self._keyword_match(question, faq.get('keywords', []))
            
            combined_score = max(similarity, keyword_score)
            
            if combined_score >= self.threshold:
                results.append((faq, combined_score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_answer(self, question: str) -> Tuple[str, Dict, float]:
        matches = self.match(question, top_k=1)
        
        if matches:
            faq, score = matches[0]
            return faq.get('answer', ''), faq, score
        
        return '', None, 0.0


def create_matcher() -> FAQMatcher:
    return FAQMatcher()

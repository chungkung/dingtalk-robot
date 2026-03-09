import json
import os
import jieba
from typing import List, Dict, Tuple
import config.config as cfg


class PersonnelRecommender:
    def __init__(self, data_path: str = None):
        self.data_path = data_path or cfg.PERSONNEL_DATA_PATH
        self.threshold = cfg.PERSONNEL_MATCH_THRESHOLD
        self.personnel_data = []
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.personnel_data = json.load(f)
        else:
            raise FileNotFoundError(f"Personnel data file not found: {self.data_path}")

    def reload(self):
        self._load_data()

    def _tokenize(self, text: str) -> set:
        words = set(jieba.cut(text))
        return {w.lower() for w in words if len(w) > 0}

    def _calculate_score(self, query: str, person: Dict) -> float:
        query_tokens = self._tokenize(query)
        
        name_tokens = self._tokenize(person.get('name', ''))
        if query_tokens & name_tokens:
            return 1.0
        
        project_tokens = self._tokenize(person.get('project', ''))
        if query_tokens & project_tokens:
            return 0.9
        
        resp_tokens = self._tokenize(person.get('responsibility', ''))
        if query_tokens & resp_tokens:
            return 0.8
        
        keyword_scores = []
        for keyword in person.get('keywords', []):
            keyword_tokens = self._tokenize(keyword)
            if query_tokens & keyword_tokens:
                keyword_scores.append(0.7)
        
        if keyword_scores:
            return max(keyword_scores)
        
        return 0.0

    def recommend(self, query: str, top_k: int = 2) -> List[Tuple[Dict, float]]:
        if not query or not query.strip():
            return []
        
        results = []
        
        for person in self.personnel_data:
            score = self._calculate_score(query, person)
            
            if score >= self.threshold:
                results.append((person, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_recommendation(self, query: str) -> Tuple[str, List[Dict], float]:
        matches = self.recommend(query, top_k=2)
        
        if not matches:
            return '', [], 0.0
        
        if len(matches) == 1:
            person, score = matches[0]
            return self._format_recommendation([person]), [person], score
        
        top1, top2 = matches[0], matches[1]
        if top1[1] - top2[1] > 0.3:
            return self._format_recommendation([top1[0]]), [top1[0]], top1[1]
        
        return self._format_recommendation([p[0] for p in matches]), [p[0] for p in matches], top1[1]

    def _format_recommendation(self, persons: List[Dict]) -> str:
        if not persons:
            return ''
        
        if len(persons) == 1:
            p = persons[0]
            email = p.get('email', p.get('dingtalk', ''))
            return (f"根据您的问题，建议联系：\n"
                   f"👤 {p['name']}\n"
                   f"📁 项目：{p['project']}\n"
                   f"💼 职责：{p['responsibility']}\n"
                   f"📞 电话：{p.get('phone', '暂无')}\n"
                   f"📧 邮箱：{email if email else '暂无'}")
        
        result = "根据您的问题，建议联系以下人员：\n"
        for i, p in enumerate(persons, 1):
            email = p.get('email', p.get('dingtalk', ''))
            result += (f"\n{i}. {p['name']}\n"
                      f"   📁 项目：{p['project']}\n"
                      f"   💼 职责：{p['responsibility']}\n"
                      f"   📞 电话：{p.get('phone', '暂无')}\n"
                      f"   📧 邮箱：{email if email else '暂无'}")
        
        return result


def create_recommender() -> PersonnelRecommender:
    return PersonnelRecommender()

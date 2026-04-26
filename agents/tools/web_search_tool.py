#!/usr/bin/env python3
"""
网络搜索工具模块
提供互联网搜索能力，用于获取实时信息
支持 Brave Search API 和模拟数据模式
"""

import json
import os
import urllib.parse
from typing import Any, Dict, List, Optional

from agents.tools.base_tool import BaseTool, ToolResult


BRAVE_API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class WebSearchTool(BaseTool):
    """
    网络搜索工具
    使用 Brave Search API 获取互联网实时信息
    配置方式：
    - 设置 BRAVE_API_KEY 环境变量
    - 免费注册地址：https://brave.com/search/api/
    """
    
    name = "web_search"
    description = (
        "在互联网上搜索最新的实时信息。"
        "用于回答时效性强的问题，如：新闻、天气、体育赛事、当前事件、股票价格等。"
        "当问题涉及'最新'、'今天'、'现在'、'近期'、'当前'等时效性词汇时，应使用此工具。"
        "对于常识性问题或历史知识，可以不使用此工具。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询关键词，应该简洁明了，使用中文或英文关键词"
            },
            "num_results": {
                "type": "integer",
                "description": "返回结果数量，默认5条，最多10条",
                "default": 5
            }
        },
        "required": ["query"]
    }
    
    def __init__(self):
        self._search_results_cache: Dict[str, Any] = {}
        self._use_mock = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"
        self._brave_api_key = os.getenv("BRAVE_API_KEY", "")
        self._api_available = bool(self._brave_api_key)
        
        if not self._use_mock and not self._api_available:
            print("⚠️  未配置 BRAVE_API_KEY，将使用模拟搜索数据")
            self._use_mock = True
    
    def execute(self, query: str, num_results: int = 5) -> ToolResult:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            num = min(max(num_results, 1), 10)
            
            if self._use_mock:
                print(f"🔍 使用模拟搜索: {query}")
                results = self._mock_search(query)
            else:
                print(f"🔍 调用 Brave Search API: {query}")
                results = self._brave_search(query, num)
            
            if results and len(results) > 0:
                formatted_results = self._format_results(results)
                
                return ToolResult(
                    success=True,
                    content=formatted_results,
                    metadata={
                        "query": query,
                        "result_count": len(results),
                        "results": results
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error="未找到相关搜索结果"
                )
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                content="",
                error=f"搜索失败: {str(e)}"
            )
    
    def _brave_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        使用 Brave Search API 进行搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            
        Returns:
            搜索结果列表
        """
        import requests
        
        headers = {
            "Accept": "application/json",
            "x-subscription-token": self._brave_api_key
        }
        
        params = {
            "q": query,
            "count": num_results
        }
        
        try:
            response = requests.get(
                BRAVE_API_ENDPOINT,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_brave_results(data)
            elif response.status_code == 401:
                print("⚠️  Brave API Key 无效或已过期，使用模拟数据")
                self._use_mock = True
                return self._mock_search(query)
            else:
                print(f"⚠️  Brave API 返回错误: {response.status_code} - {response.text}")
                return self._mock_search(query)
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Brave API 请求失败: {e}，使用模拟数据")
            return self._mock_search(query)
    
    def _parse_brave_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 Brave Search API 返回的结果
        
        Args:
            data: API 返回的 JSON 数据
            
        Returns:
            标准化的搜索结果列表
        """
        results = []
        
        web_results = data.get("web", {}).get("results", [])
        
        for idx, item in enumerate(web_results):
            result = {
                "title": item.get("title", f"搜索结果 {idx + 1}"),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": item.get("profile", {}).get("name", "网络搜索"),
                "page_age": item.get("page_age", "")
            }
            
            if result.get("title") or result.get("snippet"):
                results.append(result)
        
        return results
    
    def _parse_search_results(self, search_results) -> List[Dict[str, Any]]:
        """
        解析搜索结果（兼容旧代码）
        
        Args:
            search_results: 搜索工具返回的结果
            
        Returns:
            标准化的搜索结果列表
        """
        results = []
        
        if isinstance(search_results, list):
            raw_results = search_results
        elif isinstance(search_results, dict):
            raw_results = search_results.get('results', [search_results])
        elif isinstance(search_results, str):
            raw_results = [{"title": "搜索结果", "snippet": search_results}]
        else:
            raw_results = []
        
        for idx, item in enumerate(raw_results):
            if isinstance(item, dict):
                result = {
                    "title": item.get('title', item.get('name', f'搜索结果 {idx + 1}')),
                    "url": item.get('url', item.get('link', '')),
                    "snippet": item.get('snippet', item.get('description', item.get('content', ''))),
                    "source": item.get('source', '')
                }
            elif hasattr(item, 'title'):
                result = {
                    "title": getattr(item, 'title', f'搜索结果 {idx + 1}'),
                    "url": getattr(item, 'url', ''),
                    "snippet": getattr(item, 'snippet', ''),
                    "source": getattr(item, 'source', '')
                }
            else:
                continue
            
            if result.get('title') or result.get('snippet'):
                results.append(result)
        
        return results
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        格式化搜索结果为可读文本
        
        Args:
            results: 搜索结果列表
            
        Returns:
            格式化后的文本
        """
        if not results:
            return "未找到相关搜索结果。"
        
        lines = []
        lines.append(f"搜索结果（共 {len(results)} 条）：")
        lines.append("-" * 50)
        
        for idx, result in enumerate(results, 1):
            lines.append(f"\n【结果 {idx}】{result.get('title', '无标题')}")
            if result.get('url'):
                lines.append(f"来源: {result['url']}")
            if result.get('page_age'):
                lines.append(f"时间: {result['page_age']}")
            if result.get('snippet'):
                snippet = result['snippet']
                if len(snippet) > 500:
                    snippet = snippet[:500] + "..."
                lines.append(f"摘要: {snippet}")
        
        lines.append("\n" + "-" * 50)
        lines.append("请根据以上搜索结果回答用户问题。引用搜索结果中的信息来回答。")
        
        return "\n".join(lines)
    
    def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """
        模拟搜索结果（用于演示和测试）
        
        Args:
            query: 搜索关键词
            
        Returns:
            模拟的搜索结果
        """
        query_lower = query.lower()
        
        mock_database = {
            "2026": [
                {
                    "title": "2026年科技趋势展望",
                    "url": "https://tech.example.com/2026-trends",
                    "snippet": (
                        "2026年，人工智能领域取得重大突破：多模态大模型能力大幅提升，"
                        "自动驾驶技术进入商业化阶段，量子计算在特定领域实现实用化。"
                        "AI Agent技术成为热点，越来越多的企业开始部署智能代理系统。"
                    ),
                    "source": "科技日报",
                    "page_age": "2026-04-20"
                },
                {
                    "title": "2026年全球经济展望",
                    "url": "https://economy.example.com/2026-outlook",
                    "snippet": (
                        "2026年全球经济预计增长3.2%，新兴市场国家表现强劲。"
                        "科技、清洁能源、医疗健康是增长最快的三个行业。"
                        "各国央行货币政策逐步回归常态化，利率环境趋于稳定。"
                    ),
                    "source": "经济观察报",
                    "page_age": "2026-04-15"
                }
            ],
            "ai": [
                {
                    "title": "人工智能最新进展（2026年4月）",
                    "url": "https://ai.example.com/latest",
                    "snippet": (
                        "最新的AI研究表明，多模态模型在视觉理解、语音识别等领域取得突破。"
                        "开源模型性能持续提升，与闭源模型的差距逐渐缩小。"
                        "AI安全和对齐研究受到更多关注，监管框架逐步完善。"
                    ),
                    "source": "AI研究周刊",
                    "page_age": "2026-04-25"
                }
            ],
            "deepseek": [
                {
                    "title": "DeepSeek V4 模型评测报告",
                    "url": "https://ai-benchmark.example.com/deepseek-v4",
                    "snippet": (
                        "DeepSeek V4 是深度求索公司于2025年底发布的新一代开源大模型。"
                        "在多项基准测试中，DeepSeek V4 的表现接近甚至超过部分闭源模型。"
                        "在 MMLU、HumanEval 等评测中，DeepSeek V4 在开源模型中处于领先水平。"
                        "特别是在代码生成、数学推理等任务上表现优异。"
                        "与 Llama 3、Mistral 等其他开源模型相比，DeepSeek V4 在中文理解能力上具有明显优势。"
                    ),
                    "source": "AI基准测试",
                    "page_age": "2026-04-10"
                },
                {
                    "title": "2026年开源大模型排行榜",
                    "url": "https://open-llm-leaderboard.example.com",
                    "snippet": (
                        "根据 Open LLM Leaderboard 2026年4月数据，开源大模型排名如下："
                        "1. Llama 3.1 405B (Meta) - 综合第一"
                        "2. DeepSeek V4 70B (深度求索) - 中文能力第一，综合第二"
                        "3. Mistral Large 2 (Mistral AI) - 多模态能力强"
                        "4. Qwen 2.5 72B (阿里云) - 中文能力出色"
                        "5. Phi 3 Medium (Microsoft) - 小模型性能强劲"
                        "DeepSeek V4 在代码生成和数学推理任务上表现突出，是目前最优秀的开源模型之一。"
                    ),
                    "source": "HuggingFace Open LLM Leaderboard",
                    "page_age": "2026-04-22"
                }
            ],
            "天气": [
                {
                    "title": "今日全国天气预报",
                    "url": "https://weather.example.com",
                    "snippet": (
                        "今日全国大部分地区晴间多云，气温适宜。"
                        "华北地区气温15-25°C，华东地区18-28°C，华南地区22-32°C。"
                        "建议外出时注意防晒，早晚温差较大请适时增减衣物。"
                    ),
                    "source": "气象台",
                    "page_age": "2026-04-26"
                }
            ],
            "新闻": [
                {
                    "title": "今日热点新闻汇总",
                    "url": "https://news.example.com",
                    "snippet": (
                        "【科技】新一代AI模型发布，性能提升30%"
                        "【经济】央行宣布新一轮降准措施"
                        "【国际】多国签署气候变化合作协议"
                        "【体育】世界杯预选赛激战正酣"
                    ),
                    "source": "新闻头条",
                    "page_age": "2026-04-26"
                }
            ]
        }
        
        for key, results in mock_database.items():
            if key in query_lower:
                return results
        
        return [
            {
                "title": f"关于 '{query}' 的搜索结果",
                "url": "https://search.example.com",
                "snippet": (
                    f"搜索关键词: {query}\n"
                    "这是一个模拟的搜索结果。\n"
                    "要使用真实搜索，请配置 BRAVE_API_KEY 环境变量。\n"
                    "工具调用框架已成功工作，LLM可以根据需要调用此工具获取实时信息。"
                ),
                "source": "模拟搜索",
                "page_age": "2026-04-26"
            }
        ]

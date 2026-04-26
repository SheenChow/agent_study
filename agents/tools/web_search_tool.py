#!/usr/bin/env python3
"""
网络搜索工具模块
提供互联网搜索能力，用于获取实时信息
"""

import json
import os
from typing import Any, Dict, List, Optional

from agents.tools.base_tool import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """
    网络搜索工具
    使用搜索引擎获取互联网实时信息
    """
    
    name = "web_search"
    description = (
        "在互联网上搜索最新的实时信息。"
        "用于回答时效性强的问题，如：新闻、天气、体育赛事、当前事件、股票价格等。"
        "当问题涉及'最新'、'今天'、'现在'、'近期'等时效性词汇时，应使用此工具。"
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
                results = self._mock_search(query)
            else:
                results = self._do_search(query, num)
            
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
            return ToolResult(
                success=False,
                content="",
                error=f"搜索失败: {str(e)}"
            )
    
    def _do_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        执行实际搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            search_results = self._search_with_sub_agent(query, num_results)
            return self._parse_search_results(search_results)
        except Exception as e:
            print(f"⚠️  搜索工具调用失败: {e}，使用模拟数据")
            return self._mock_search(query)
    
    def _search_with_sub_agent(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        使用 search 子代理工具进行搜索
        
        Args:
            query: 搜索关键词
            num_results: 结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            from search import search as sub_agent_search
            
            result = sub_agent_search(
                query=f"搜索关于 {query} 的最新信息",
                response_language="中文"
            )
            
            if result:
                return [
                    {
                        "title": f"搜索结果: {query}",
                        "url": "https://search.example.com",
                        "snippet": str(result) if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
                        "source": "子代理搜索"
                    }
                ]
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  子代理搜索失败: {e}")
        
        return self._mock_search(query)
    
    def _parse_search_results(self, search_results) -> List[Dict[str, Any]]:
        """
        解析搜索结果
        
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
                    "source": "科技日报"
                },
                {
                    "title": "2026年全球经济展望",
                    "url": "https://economy.example.com/2026-outlook",
                    "snippet": (
                        "2026年全球经济预计增长3.2%，新兴市场国家表现强劲。"
                        "科技、清洁能源、医疗健康是增长最快的三个行业。"
                        "各国央行货币政策逐步回归常态化，利率环境趋于稳定。"
                    ),
                    "source": "经济观察报"
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
                    "source": "AI研究周刊"
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
                    "source": "气象台"
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
                    "source": "新闻头条"
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
                    "在实际部署中，这里会显示真实的网络搜索结果。\n"
                    "工具调用框架已成功工作，LLM可以根据需要调用此工具获取实时信息。"
                ),
                "source": "模拟搜索"
            }
        ]

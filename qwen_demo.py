#!/usr/bin/env python3
"""
千问模型调用Demo - 用于学习Agent推理能力
输出JSON格式，便于后续处理
"""

import json
import os
from typing import Dict, Any

import dashscope
from dotenv import load_dotenv


class QwenAgent:
    """
    简单的Agent类，展示推理能力
    """
    
    def __init__(self, api_key: str = None, model: str = "qwen-turbo"):
        """
        初始化Agent
        
        Args:
            api_key: 阿里云API Key，如果不提供则从环境变量读取
            model: 使用的模型名称，默认qwen-turbo
        """
        load_dotenv()
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API Key未提供。请设置环境变量DASHSCOPE_API_KEY "
                "或在.env文件中配置"
            )
        
        self.model = model
        dashscope.api_key = self.api_key
        
        print(f"✅ QwenAgent初始化成功，使用模型: {self.model}")
        print("-" * 50)
    
    def chat(self, 
             user_message: str, 
             system_prompt: str = None,
             return_json: bool = True) -> Dict[str, Any]:
        """
        与模型进行对话
        
        Args:
            user_message: 用户输入的消息
            system_prompt: 系统提示词，用于定义Agent行为
            return_json: 是否强制输出JSON格式
            
        Returns:
            包含模型响应的字典
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        if return_json:
            messages.append({
                "role": "assistant",
                "content": "请以JSON格式输出结果，不要包含任何其他文本。"
            })
        
        try:
            response = dashscope.Generation.call(
                model=self.model,
                messages=messages,
                result_format="message"
            )
            
            if response.status_code == 200:
                content = response.output.choices[0]["message"]["content"]
                
                result = {
                    "success": True,
                    "model": self.model,
                    "user_input": user_message,
                    "response": content,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
                if return_json:
                    try:
                        parsed_json = self._extract_json(content)
                        if parsed_json:
                            result["parsed_json"] = parsed_json
                    except json.JSONDecodeError:
                        result["parse_error"] = "无法将响应解析为JSON"
                
                return result
            else:
                return {
                    "success": False,
                    "error_code": response.code,
                    "error_message": response.message
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取JSON对象
        
        Args:
            text: 可能包含JSON的文本
            
        Returns:
            解析后的JSON对象
        """
        start_index = text.find("{")
        end_index = text.rfind("}") + 1
        
        if start_index != -1 and end_index != -1:
            json_str = text[start_index:end_index]
            return json.loads(json_str)
        else:
            return None
    
    def reasoning_demo(self, problem: str) -> Dict[str, Any]:
        """
        演示Agent的推理能力
        
        Args:
            problem: 需要解决的问题
            
        Returns:
            包含推理过程的JSON响应
        """
        system_prompt = """
你是一个智能推理助手。当用户提出问题时，你需要：
1. 仔细分析问题
2. 逐步思考解决方法
3. 给出最终答案

请以JSON格式输出，包含以下字段：
- "analysis": 对问题的分析
- "reasoning": 推理步骤（数组，每个步骤描述一步）
- "answer": 最终答案
- "confidence": 置信度（0-1的浮点数）
"""

        return self.chat(
            user_message=problem,
            system_prompt=system_prompt,
            return_json=True
        )


def main():
    """
    主函数 - 演示Agent推理能力
    """
    
    print("🤖 千问模型Agent推理Demo")
    print("=" * 50)
    
    try:
        agent = QwenAgent()
    except ValueError as e:
        print(f"❌ 错误: {e}")
        print("\n请按以下步骤操作：")
        print("1. 复制 .env.example 文件为 .env")
        print("2. 在 .env 文件中填入你的DASHSCOPE_API_KEY")
        print("3. 重新运行此脚本")
        return
    
    test_problems = [
        "如果5台机器5分钟生产5个零件，那么100台机器生产100个零件需要多长时间？",
        "一个池塘里的荷花，每天面积增长一倍，30天可以长满整个池塘。问多少天可以长满池塘的一半？",
    ]
    
    for i, problem in enumerate(test_problems, 1):
        print(f"\n📝 测试问题 {i}: {problem}")
        print("-" * 50)
        
        result = agent.reasoning_demo(problem)
        
        if result["success"]:
            print(f"✅ 模型响应:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            if "parsed_json" in result:
                print("\n📊 解析后的JSON内容:")
                print(json.dumps(result["parsed_json"], ensure_ascii=False, indent=2))
        else:
            print(f"❌ 错误: {result.get('error_message', '未知错误')}")
        
        print("=" * 50)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Agent Web 应用主入口
Flask Web服务，提供聊天界面和后台管理
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

from config import get_config_manager, ConfigManager
from agents.llm_agent import (
    get_llm_service, 
    LLMService,
    ChatMessage,
    StreamChunk,
    AgentWithTools,
    AgentStep,
    DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
)
from agents.tools.tool_manager import get_tool_manager, register_default_tools


app = Flask(__name__)
app.secret_key = 'agent-study-secret-key-2026'

config_manager: Optional[ConfigManager] = None

_active_streams: Dict[str, List[StreamChunk]] = {}


def init_app():
    """初始化应用"""
    global config_manager
    config_manager = get_config_manager()
    register_default_tools()
    print("✅ Agent Web 应用初始化完成")
    print(f"✅ 已注册工具: {get_tool_manager().list_tools()}")


@app.route('/')
def index():
    """用户聊天页面"""
    return render_template('index.html')


@app.route('/admin')
def admin():
    """后台管理页面"""
    return render_template('admin.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    try:
        config = config_manager.to_dict(mask_sensitive=True)
        return jsonify({
            "success": True,
            "data": config
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400
        
        provider = data.get('provider')
        api_key = data.get('api_key')
        model = data.get('model')
        system_prompt = data.get('system_prompt')
        
        result = config_manager.update_config(
            provider=provider,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt
        )
        
        if result["success"]:
            LLMService.clear_cache()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/models', methods=['GET'])
def get_models():
    """获取可用模型列表"""
    try:
        provider = request.args.get('provider')
        
        if not provider:
            provider_config = config_manager.get_current_provider()
            provider = config_manager.get().current_provider
        
        models = config_manager.get_available_models(provider)
        
        return jsonify({
            "success": True,
            "data": {
                "provider": provider,
                "models": models
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """获取支持的服务商列表"""
    try:
        config = config_manager.get()
        providers = []
        
        for provider_id, provider_config in config.providers.items():
            providers.append({
                "id": provider_id,
                "name": provider_config.name,
                "models": config_manager.get_available_models(provider_id)
            })
        
        return jsonify({
            "success": True,
            "data": {
                "current_provider": config.current_provider,
                "providers": providers
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """发起对话请求"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400
        
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                "success": False,
                "error": "消息内容不能为空"
            }), 400
        
        stream = data.get('stream', True)
        history = data.get('history', [])
        
        app_config = config_manager.get()
        provider_config = config_manager.get_current_provider()
        
        if not provider_config.api_key:
            return jsonify({
                "success": False,
                "error": "API Key未配置，请先在后台管理中配置"
            }), 400
        
        messages = []
        for item in history:
            messages.append(ChatMessage(
                role=item.get('role', 'user'),
                content=item.get('content', '')
            ))
        
        messages.append(ChatMessage(role='user', content=message))
        
        service = get_llm_service(
            provider=app_config.current_provider,
            api_key=provider_config.api_key
        )
        
        if stream:
            session_id = str(uuid.uuid4())
            _active_streams[session_id] = []
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "message": "对话已发起，请通过 /api/chat/stream 获取流式输出"
            })
        else:
            result = service.chat(
                messages=messages,
                model=provider_config.default_model,
                stream=False,
                system_prompt=app_config.system_prompt
            )
            
            return jsonify({
                "success": result.success,
                "content": result.content,
                "model": result.model,
                "usage": result.usage,
                "error": result.error_message
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/chat/stream', methods=['GET'])
def chat_stream():
    """流式输出接口 (SSE) - 支持工具调用"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少 session_id 参数"
            }), 400
        
        app_config = config_manager.get()
        provider_config = config_manager.get_current_provider()
        
        if not provider_config.api_key:
            def error_generator():
                yield f"data: {json.dumps({'type': 'error', 'content': 'API Key未配置'})}\n\n"
            return Response(error_generator(), mimetype='text/event-stream')
        
        messages_str = request.args.get('messages', '[]')
        try:
            messages_data = json.loads(messages_str)
        except:
            messages_data = []
        
        user_message = request.args.get('message', '')
        
        history = []
        for item in messages_data:
            history.append(ChatMessage(
                role=item.get('role', 'user'),
                content=item.get('content', '')
            ))
        
        service = get_llm_service(
            provider=app_config.current_provider,
            api_key=provider_config.api_key
        )
        
        tool_manager = get_tool_manager()
        
        system_prompt = DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
        
        def generate():
            try:
                events = []
                import re
                
                def capture_step(step: AgentStep):
                    if step.step_type == "tool_call":
                        events.append({
                            "type": "tool_call",
                            "tool": step.tool_name,
                            "query": step.tool_arguments.get("query", "") if step.tool_arguments else "",
                            "arguments": step.tool_arguments
                        })
                    elif step.step_type == "tool_result":
                        result_count = 5
                        if step.tool_result:
                            match = re.search(r'共[（(]\s*(\d+)\s*[)）]\s*条', step.tool_result)
                            if match:
                                result_count = int(match.group(1))
                        
                        events.append({
                            "type": "tool_result",
                            "tool": step.tool_name,
                            "success": "错误" not in (step.tool_result or ""),
                            "result_count": result_count
                        })
                
                agent = AgentWithTools(
                    llm_service=service,
                    model=provider_config.default_model,
                    system_prompt=system_prompt,
                    tool_manager=tool_manager
                )
                
                result = agent.chat(
                    user_message=user_message,
                    history=history,
                    step_callback=capture_step
                )
                
                for event in events:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
                if result.success:
                    for char in result.final_answer:
                        yield f"data: {json.dumps({'type': 'text', 'content': char, 'done': False}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'done', 'content': '', 'done': True, 'usage': result.usage}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'content': result.error_message or '执行失败', 'done': True}, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_data = {
                    "type": "error",
                    "content": str(e),
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        def error_generator():
            error_data = {
                "type": "error",
                "content": str(e),
                "done": True
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return Response(error_generator(), mimetype='text/event-stream')


@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """测试连接是否有效"""
    try:
        data = request.get_json() or {}
        
        provider = data.get('provider') or config_manager.get().current_provider
        api_key = data.get('api_key')
        
        if not api_key:
            provider_config = config_manager.get().providers.get(provider)
            if provider_config:
                api_key = provider_config.api_key
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API Key不能为空"
            }), 400
        
        service = get_llm_service(provider=provider, api_key=api_key)
        is_valid = service.validate_api_key(api_key)
        
        if is_valid:
            return jsonify({
                "success": True,
                "message": "连接测试成功，API Key有效"
            })
        else:
            return jsonify({
                "success": False,
                "error": "连接测试失败，API Key无效或服务不可用"
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "success": True,
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


init_app()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    
    print("=" * 50)
    print("🤖 Agent Web 应用启动中...")
    print("=" * 50)
    print(f"📱 用户界面: http://localhost:{port}/")
    print(f"⚙️  后台管理: http://localhost:{port}/admin")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True, use_reloader=False)

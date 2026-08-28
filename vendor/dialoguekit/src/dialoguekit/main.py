"""
启动uvicorn web服务 - 电商客服项目 (薄启动层)
"""
import uvicorn

from dialoguekit.config.settings import Settings
from dialoguekit.infrastructure.db_client import init_db_engine, dispose_engine
from dialoguekit.infrastructure.http_client import init_http_client, disposed_http_client
from dialoguekit.engines.builder import build_dialogue_engine
from dialoguekit.plugins.registry import plugin_registry
from dialoguekit.api.app import create_app
from dialoguekit.task.action.register import ActionRegister

# 确保电商插件被发现（plugins/ecommerce/__init__.py 会自动注册）
plugin_registry.discover("plugins")

# 构建引擎（自动加载电商插件的 flows/actions/intents）
engine = build_dialogue_engine(plugin_registry=plugin_registry)

app = create_app(engine=engine)

if __name__ == '__main__':
    settings = Settings()
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
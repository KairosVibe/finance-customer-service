import uvicorn
from dialoguekit.config.settings import Settings
from dialoguekit.infrastructure.db_client import init_db_engine, dispose_engine
from dialoguekit.infrastructure.http_client import init_http_client, disposed_http_client
from dialoguekit.engines.builder import build_dialogue_engine
from dialoguekit.plugins.registry import plugin_registry
from dialoguekit.api.app import create_app
from dialoguekit.task.action.register import ActionRegister

# 1. 发现并注册插件
plugin_registry.discover("plugins")

# 2. 构建 ActionRegister（内置 + 插件）
action_register = ActionRegister()
from dialoguekit.task.action.builtin.listener import ActionListener
from dialoguekit.task.action.builtin.response import ActionResponse
action_register.registry_action(ActionListener())
action_register.registry_action(ActionResponse())
plugin_registry.register_all_actions(action_register)

# 3. 构建引擎
engine = build_dialogue_engine(
    plugin_registry_obj=plugin_registry,
    action_register=action_register,
)

# 4. 创建 FastAPI 应用
app = create_app(engine=engine)

# 5. 生命周期
@app.on_event("startup")
async def startup():
    init_db_engine()
    init_http_client()

@app.on_event("shutdown")
async def shutdown():
    await dispose_engine()
    await disposed_http_client()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=18082)
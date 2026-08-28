"""
管理service.
FASTAPI的依赖注入：Depends
Annotated；注解。可以将类型提示和依赖注入绑定在一起
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dialoguekit.engines.dialogue_engine import DialogueEngine
from dialoguekit.repository.dialogue_repository import DialogueRepository
from dialoguekit.services.dialogue_service import DialogueStateService
from dialoguekit.infrastructure.db_client import session_factory
from dialoguekit.infrastructure import db_client
from dialoguekit.engines.builder import build_dialogue_engine
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.task.action.builtin.listener import ActionListener
from dialoguekit.task.action.builtin.response import ActionResponse
from dialoguekit.plugins.registry import plugin_registry

def get_action_register() -> ActionRegister:
    register = ActionRegister()
    register.registry_action(ActionListener())
    register.registry_action(ActionResponse())
    plugin_registry.register_all_actions(register)
    return register

ActionRegisterDep = Annotated[ActionRegister, Depends(get_action_register)]


def get_dialogue_engine(action_register: ActionRegisterDep) -> DialogueEngine:
    return build_dialogue_engine(action_register=action_register)


DialogueEngineDep = Annotated[DialogueEngine, Depends(get_dialogue_engine)]


async def get_session():
    async with db_client.session_factory() as session:
        yield session


DialogueSessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_dialogue_repository(session: DialogueSessionDep):
    return DialogueRepository(session)


DialogueRepositoryDep = Annotated[DialogueRepository, Depends(get_dialogue_repository)]


def get_dialogue_service(engine: DialogueEngineDep, repository: DialogueRepositoryDep):
    return DialogueStateService(engine, repository)


DialogueStateServiceDep = Annotated[DialogueStateService, Depends(get_dialogue_service)]
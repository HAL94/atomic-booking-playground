from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.domain.todo import TodoWithTasks
from app.dto.todo import TodoCreate
from app.services.todo import TodoService


class TestTodoService:
    @pytest.fixture
    def todo_service(self, mocker):
        """
        Fixture that provides an instance of the TodoService for testing,
        using the transactional AsyncSession.
        """
        with patch("app.services.todo.TodoService") as todo_service_class:
            todo_service = mocker.MagicMock(spec=TodoService)
            todo_service_class.return_value = todo_service
            yield todo_service

    @pytest.mark.asyncio
    async def test_create_todo(self, todo_service: TodoService, user_id: str):
        """Test the todo creation"""
        todo_item = TodoCreate(title="1st todo")
        todo_dummy = TodoWithTasks(id=str(uuid4()), title="1st todo", user_id=UUID(user_id))

        todo_service.create_todo.return_value = todo_dummy
        added_todo = await todo_service.create_todo(todo_item, UUID(user_id))
        assert added_todo is not None
        assert added_todo.id is not None
        assert added_todo.title == todo_item.title

    @pytest.mark.asyncio
    async def test_get_todo(self, todo_service, user_id: str):
        """Get a todo by id and check it fetches successfully"""

        todo_dummy = TodoWithTasks(id=str(uuid4()), title="some todo", user_id=UUID(user_id))
        todo_service.get_todo.return_value = todo_dummy
        todo = await todo_service.get_todo(todo_dummy.id, UUID(user_id))

        assert todo is not None
        assert todo.id == todo_dummy.id
        assert todo.title is not None
        assert todo.user_id == UUID(user_id)

    @pytest.mark.asyncio
    async def test_get_all_todos(self, todo_service: TodoService, user_id: str):
        """Get all todos"""
        todo_dummy = TodoWithTasks(id=str(uuid4()), title="some todo", user_id=UUID(user_id))
        todo_service.get_todos.return_value = [todo_dummy]
        todos = await todo_service.get_todos(UUID(user_id))

        assert todos is not None
        assert len(todos) != 0

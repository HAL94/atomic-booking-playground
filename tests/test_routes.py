from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.domain.todo import TodoWithTasks
from app.dto.auth import LoginUserDto, RegisterUserDto
from app.dto.todo import TodoCreate
from app.services.todo import TodoService


class TestAuthRoutes:
    """Test all auth routes"""

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient, register_user_payload: RegisterUserDto):
        """Run register endpoint which will create user"""
        response = await client.post("/auth/register", json=register_user_payload.model_dump(by_alias=True))

        assert response.status_code == status.HTTP_200_OK
        payload: dict[str, Any] = response.json()

        assert payload is not None
        user_id = payload.get("id")

        assert user_id is not None
        assert UUID(user_id) is not None

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, login_user_payload: LoginUserDto, app_session):
        """Run test for logging in user"""
        response = await client.post(
            "/auth/login", data={"username": login_user_payload.email, "password": login_user_payload.password}
        )

        app_session["data"] = response.cookies
        assert response.status_code == status.HTTP_200_OK

        payload: dict[str, Any] = response.json()
        assert payload is not None
        is_success = payload.get("success")
        assert is_success
        data: dict[str, Any] = payload.get("data", None)
        assert data is not None
        assert data.get("sessionId") is not None

    @pytest.mark.asyncio
    async def test_me(self, client: AsyncClient, app_session, user_id):
        """Test getting authorized user data from endpoint"""
        client.cookies.update(app_session["data"])
        response = await client.get("/auth/me")
        data = response.json()

        assert data is not None
        current_user_id = data.get("id")
        assert current_user_id is not None
        assert user_id is not None


class TestTodoRoutes:
    """Test all todo routes"""

    @pytest.fixture
    def todo_service(self, mocker):
        with patch("app.api.v1.todos.TodoService") as todo_service_class:
            todo_service = mocker.MagicMock(spec=TodoService)
            todo_service_class.return_value = todo_service
            yield todo_service

    @pytest.mark.asyncio
    async def test_create_todo(self, client: AsyncClient, app_session: dict[str, Any]):
        """Run create endpoint for creating todo"""
        todo_sample = TodoCreate(title="some_todo")
        client.cookies.update(app_session["data"])
        response = await client.post("/todos/", json=todo_sample.model_dump())

        assert response.status_code == status.HTTP_201_CREATED
        payload: dict[str, Any] = response.json()
        assert payload is not None
        assert isinstance(payload, dict)
        data: dict[str, Any] = payload.get("data")
        assert data is not None

        assert data.get("title") == todo_sample.title
        assert data.get("id") is not None

    @pytest.mark.asyncio
    async def test_get_todo_by_id(self, client: AsyncClient, app_session: dict[str, Any], todo_service):
        """Run get endpoint for getting a todo by id"""

        todo_dummy = TodoWithTasks(id=str(uuid4()), title="some todo", user_id=str(uuid4()))
        todo_service.get_todo.return_value = todo_dummy
        client.cookies.update(app_session["data"])
        response = await client.get(f"/todos/{todo_dummy.id}")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload is not None
        assert isinstance(payload, dict)
        data: dict[str, Any] = payload.get("data")
        assert data is not None

        assert UUID(data.get("id")) == todo_dummy.id
        assert data.get("title") == todo_dummy.title

    @pytest.mark.asyncio
    async def test_get_all_todos(self, client: AsyncClient, app_session: dict[str, Any]):
        """Run endpoint to get all todos with a limit of 20 records"""
        client.cookies.update(app_session["data"])
        response = await client.get("/todos/")
        default_size = 1

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload is not None
        data = payload.get("data")
        assert data is not None

        assert isinstance(data, list)
        assert len(data) == default_size

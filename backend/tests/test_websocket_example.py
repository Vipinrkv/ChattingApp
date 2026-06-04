import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app


def test_unauthorized_chat_websocket_connection_rejected():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/chat/00000000-0000-0000-0000-000000000000"):
                pass

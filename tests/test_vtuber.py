# tests/test_vtuber.py

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.vtuber import VtuberController
import asyncio
import json


class TestVtuberController(unittest.IsolatedAsyncioTestCase):
    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_connect_and_authenticate(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber")
        await vtuber.connect()

        mock_connect.assert_awaited_once_with("ws://127.0.0.1:8001")
        mock_ws.send.assert_awaited_once_with('{"pluginName": "AI Vtuber Controller", "requestedApiVersion": 1}')
        self.assertTrue(vtuber.connected)

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_set_expression(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber")
        await vtuber.connect()

        # 模拟设置表情响应
        mock_ws.recv.return_value = '{"responseType": "SetExpression"}'
        await vtuber.set_expression("happy")

        expected_command = {
            "requestType": "SetExpression",
            "parameters": {
                "expressionName": "Hiyori_Happy"
            }
        }
        mock_ws.send.assert_awaited_with(json.dumps(expected_command))

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_close_connection(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber")
        await vtuber.connect()

        await vtuber.close()
        mock_ws.close.assert_awaited_once()
        self.assertFalse(vtuber.connected)

if __name__ == '__main__':
    unittest.main()

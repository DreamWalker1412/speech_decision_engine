# tests/test_vtuber.py

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import json
import asyncio
import logging

# 将项目根目录添加到系统路径，以便导入src模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vtuber import VtuberController
from src.config import VTUBER_CONFIG

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestVtuberController(unittest.IsolatedAsyncioTestCase):
    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_connect_and_authenticate(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 定义认证响应的顺序
        mock_ws.recv.side_effect = [
            json.dumps({
                "messageType": "AuthenticationTokenResponse",
                "data": {
                    "authenticationToken": "valid_token"
                }
            }),
            json.dumps({
                "messageType": "AuthenticationResponse",
                "data": {
                    "authenticated": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key="dummy_key",
            vtuber_name="DummyVtuber",
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=5.0,
            watchdog_interval=5.0
        )
        await vtuber.connect()

        # 验证WebSocket连接是否被调用
        mock_connect.assert_awaited_once_with(f"ws://{VTUBER_CONFIG.get('host', '127.0.0.1')}:{VTUBER_CONFIG.get('port', 8001)}/")

        # 验证发送的AuthenticationTokenRequest是否正确
        expected_auth_token_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": unittest.mock.ANY,  # requestID是随机生成的
            "messageType": "AuthenticationTokenRequest",
            "data": {
                "pluginName": VTUBER_CONFIG["pluginName"],
                "pluginDeveloper": VTUBER_CONFIG["pluginDeveloper"],
                "pluginIcon": VTUBER_CONFIG["pluginIcon"]
            }
        }
        mock_ws.send.assert_any_await(json.dumps(expected_auth_token_request))

        # 验证发送的AuthenticationRequest是否正确
        expected_auth_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": unittest.mock.ANY,
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": VTUBER_CONFIG["pluginName"],
                "pluginDeveloper": VTUBER_CONFIG["pluginDeveloper"],
                "authenticationToken": "valid_token"
            }
        }
        mock_ws.send.assert_any_await(json.dumps(expected_auth_request))

        # 验证认证状态
        self.assertTrue(vtuber.authenticated, "认证未成功。")

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_set_expression(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 定义认证响应的顺序
        mock_ws.recv.side_effect = [
            json.dumps({
                "messageType": "AuthenticationTokenResponse",
                "data": {
                    "authenticationToken": "valid_token"
                }
            }),
            json.dumps({
                "messageType": "AuthenticationResponse",
                "data": {
                    "authenticated": True
                }
            }),
            json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key="dummy_key",
            vtuber_name="DummyVtuber",
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=5.0,
            watchdog_interval=5.0
        )
        await vtuber.connect()

        # 设置表情
        await vtuber.set_expression("happy")

        # 验证发送的SetExpression请求是否正确
        expected_set_expression_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": unittest.mock.ANY,
            "messageType": "SetExpression",
            "data": {
                "expressionName": VTUBER_CONFIG["expressions"].get("happy")
            }
        }
        mock_ws.send.assert_any_await(json.dumps(expected_set_expression_request))

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_close_connection(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 定义认证响应的顺序
        mock_ws.recv.side_effect = [
            json.dumps({
                "messageType": "AuthenticationTokenResponse",
                "data": {
                    "authenticationToken": "valid_token"
                }
            }),
            json.dumps({
                "messageType": "AuthenticationResponse",
                "data": {
                    "authenticated": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key="dummy_key",
            vtuber_name="DummyVtuber",
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=5.0,
            watchdog_interval=5.0
        )
        await vtuber.connect()

        # 关闭连接
        await vtuber.close()

        # 验证WebSocket关闭是否被调用
        mock_ws.close.assert_awaited_once()

        # 验证认证状态
        self.assertFalse(vtuber.authenticated, "认证状态应为False。")

if __name__ == '__main__':
    unittest.main()

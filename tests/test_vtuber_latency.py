# tests/test_vtuber_latency.py

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

class TestVtuberLatency(unittest.IsolatedAsyncioTestCase):
    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def asyncSetUp(self, mock_connect):
        """
        设置测试环境，使用mocking来模拟VTubeStudio API的连接和认证。
        """
        # 模拟WebSocket连接
        self.mock_ws = AsyncMock()
        mock_connect.return_value = self.mock_ws

        # 定义认证响应的顺序
        self.mock_ws.recv.side_effect = [
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
        self.vtuber = VtuberController(
            api_key=VTUBER_CONFIG.get("api_key", "dummy_api_key"),
            vtuber_name=VTUBER_CONFIG.get("vtuber_name", "Hiyori_A"),
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=1.0,    # 设置低阈值以便测试
            watchdog_interval=1.0      # 设置短间隔
        )
        await self.vtuber.connect()

    async def asyncTearDown(self):
        """
        清理测试环境，关闭连接。
        """
        await self.vtuber.close()

    async def test_set_expression_with_normal_latency(self):
        """
        测试在正常延迟情况下设置表情是否记录正确的延迟。
        """
        expression_key = "happy"
        expression_name = VTUBER_CONFIG["expressions"].get(expression_key)
        self.assertIsNotNone(expression_name, f"表达式键 '{expression_key}' 未在配置中定义。")

        # 模拟正常延迟的recv响应
        async def normal_recv():
            await asyncio.sleep(0.5)  # 延迟0.5秒，小于阈值1秒
            return json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })

        self.mock_ws.recv.side_effect = normal_recv

        # 设置表情
        await self.vtuber.set_expression(expression_key)

        # 检查延迟是否记录
        self.assertEqual(len(self.vtuber.latencies), 1)
        self.assertTrue(self.vtuber.latencies[0] >= 0.5 and self.vtuber.latencies[0] < 1.5, "延迟记录不正确。")

    async def test_set_expression_with_high_latency(self):
        """
        测试在高延迟情况下设置表情是否记录正确的延迟并触发警报。
        """
        expression_key = "happy"
        expression_name = VTUBER_CONFIG["expressions"].get(expression_key)
        self.assertIsNotNone(expression_name, f"表达式键 '{expression_key}' 未在配置中定义。")

        # 模拟高延迟的recv响应
        async def delayed_recv():
            await asyncio.sleep(2)  # 延迟2秒，超过阈值1秒
            return json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })

        self.mock_ws.recv.side_effect = delayed_recv

        # 重写 notify_admin 方法以记录是否被调用
        async def mock_notify_admin(latency, threshold):
            self.notify_called = True
            self.notify_latency = latency
            self.notify_threshold = threshold

        self.vtuber.notify_admin = mock_notify_admin
        self.notify_called = False
        self.notify_latency = 0
        self.notify_threshold = 0

        # 设置表情
        await self.vtuber.set_expression(expression_key)

        # 等待watchdog检查
        await asyncio.sleep(2)  # watchdog_interval为1秒

        # 检查延迟是否记录
        self.assertEqual(len(self.vtuber.latencies), 1)
        self.assertTrue(self.vtuber.latencies[0] >= 2.0, "延迟记录不正确。")

        # 检查是否触发了警报
        self.assertTrue(self.notify_called, "看门狗未触发警报。")
        self.assertEqual(self.notify_latency, self.vtuber.latency_threshold + 1.0, "触发警报的延迟值不正确。")

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_triggers_alert_on_high_latency(self, mock_connect):
        """
        测试看门狗在延迟超出阈值时是否触发警报。
        """
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
            # SetExpressionResponse with high latency
            json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key=VTUBER_CONFIG.get("api_key", "dummy_api_key"),
            vtuber_name=VTUBER_CONFIG.get("vtuber_name", "Hiyori_A"),
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=1.0,    # 设置低阈值以便测试
            watchdog_interval=1.0      # 设置短间隔
        )
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟设置表情时延迟超过阈值
            async def delayed_recv():
                await asyncio.sleep(2)  # 延迟2秒，超过阈值1秒
                return json.dumps({
                    "messageType": "SetExpressionResponse",
                    "data": {
                        "success": True
                    }
                })

            mock_ws.recv.side_effect = delayed_recv

            # 设置表情
            await vtuber.set_expression("happy")

            # 等待watchdog检查
            await asyncio.sleep(2)  # watchdog_interval为1秒

            # 验证 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called, "看门狗未触发警报。")
            args, kwargs = mock_notify_admin.call_args
            self.assertTrue(args[0] >= vtuber.latency_threshold, "触发警报的延迟值不正确。")
            self.assertEqual(args[1], vtuber.latency_threshold, "触发警报的阈值不正确。")

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_does_not_trigger_alert_on_normal_latency(self, mock_connect):
        """
        测试看门狗在延迟正常时不触发警报。
        """
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
            # SetExpressionResponse with normal latency
            json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key=VTUBER_CONFIG.get("api_key", "dummy_api_key"),
            vtuber_name=VTUBER_CONFIG.get("vtuber_name", "Hiyori_A"),
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=1.0,    # 设置低阈值以便测试
            watchdog_interval=1.0      # 设置短间隔
        )
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟正常延迟的recv响应
            async def normal_recv():
                await asyncio.sleep(0.5)  # 延迟0.5秒，小于阈值1秒
                return json.dumps({
                    "messageType": "SetExpressionResponse",
                    "data": {
                        "success": True
                    }
                })

            mock_ws.recv.side_effect = normal_recv

            # 设置表情
            await vtuber.set_expression("happy")

            # 等待watchdog检查
            await asyncio.sleep(2)  # watchdog_interval为1秒

            # 验证 notify_admin 是否未被调用
            mock_notify_admin.assert_not_called()

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_with_mixed_latency(self, mock_connect):
        """
        测试看门狗在混合延迟情况下的行为。
        """
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
            # SetExpressionResponse with normal latency
            json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            }),
            # SetExpressionResponse with high latency
            json.dumps({
                "messageType": "SetExpressionResponse",
                "data": {
                    "success": True
                }
            })
        ]

        # 创建VtuberController实例，提供所有必要参数
        vtuber = VtuberController(
            api_key=VTUBER_CONFIG.get("api_key", "dummy_api_key"),
            vtuber_name=VTUBER_CONFIG.get("vtuber_name", "Hiyori_A"),
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=1.0,    # 设置低阈值以便测试
            watchdog_interval=1.0      # 设置短间隔
        )
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 定义一个生成器来模拟混合延迟的recv响应
            async def mixed_recv():
                # 前3次正常延迟
                for _ in range(3):
                    await asyncio.sleep(0.5)  # 延迟0.5秒
                    yield json.dumps({
                        "messageType": "SetExpressionResponse",
                        "data": {
                            "success": True
                        }
                    })
                # 后2次高延迟
                for _ in range(2):
                    await asyncio.sleep(2)  # 延迟2秒
                    yield json.dumps({
                        "messageType": "SetExpressionResponse",
                        "data": {
                            "success": True
                        }
                    })

            recv_generator = mixed_recv()

            async def side_effect():
                return await recv_generator.__anext__()

            self.mock_ws.recv.side_effect = side_effect

            # 设置表情，前3次正常，后2次高延迟
            for _ in range(5):
                await vtuber.set_expression("happy")

            # 等待watchdog检查
            await asyncio.sleep(3)  # watchdog_interval为1秒

            # 验证 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called, "看门狗未触发警报。")
            # 检查 notify_admin 是否被调用至少一次
            self.assertGreaterEqual(mock_notify_admin.call_count, 1)

if __name__ == '__main__':
    unittest.main()

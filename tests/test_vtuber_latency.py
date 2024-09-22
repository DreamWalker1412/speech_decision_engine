# tests/test_vtuber_latency.py

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.vtuber import VtuberController
import asyncio



class TestVtuberLatency(unittest.IsolatedAsyncioTestCase):
    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_set_expression_with_normal_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        # 创建VtuberController实例，设置watchdog_interval为1秒
        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0, watchdog_interval=1.0)
        await vtuber.connect()

        # 模拟设置表情响应
        mock_ws.recv.return_value = '{"responseType": "SetExpression"}'
        await vtuber.set_expression("happy")

        # 检查延迟是否记录
        self.assertEqual(len(vtuber.latencies), 1)
        self.assertTrue(vtuber.latencies[0] < 1.0)

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_set_expression_with_high_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        # 创建VtuberController实例，设置watchdog_interval为1秒
        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0, watchdog_interval=1.0)
        await vtuber.connect()

        # 模拟设置表情响应，增加人为延迟
        async def delayed_recv():
            await asyncio.sleep(2)  # 延迟2秒
            return '{"responseType": "SetExpression"}'

        mock_ws.recv.side_effect = delayed_recv

        await vtuber.set_expression("happy")

        # 检查延迟是否记录
        self.assertEqual(len(vtuber.latencies), 1)
        self.assertTrue(vtuber.latencies[0] >= 2.0)

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_triggers_alert_on_high_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        # 创建VtuberController实例，设置watchdog_interval为1秒
        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0, watchdog_interval=1.0)
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟多个高延迟设置表情
            async def delayed_recv():
                await asyncio.sleep(2)  # 延迟2秒
                return '{"responseType": "SetExpression"}'

            mock_ws.recv.side_effect = delayed_recv

            # 设置多个高延迟表情，触发警报
            for _ in range(5):
                await vtuber.set_expression("happy")

            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)  # watchdog_interval为1秒

            # 验证 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called)
            # 检查 notify_admin 是否被调用至少一次
            self.assertGreaterEqual(mock_notify_admin.call_count, 1)

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_does_not_trigger_alert_on_normal_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        # 创建VtuberController实例，设置watchdog_interval为1秒
        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0, watchdog_interval=1.0)
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟多个正常延迟设置表情
            mock_ws.recv.return_value = '{"responseType": "SetExpression"}'
            for _ in range(5):
                await vtuber.set_expression("happy")

            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)  # watchdog_interval为1秒

            # 验证 notify_admin 没有被调用
            mock_notify_admin.assert_not_called()

    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_watchdog_with_mixed_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        # 创建VtuberController实例，设置watchdog_interval为1秒
        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0, watchdog_interval=1.0)
        await vtuber.connect()

        # Mock notify_admin to track its calls
        with patch.object(vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟设置表情：前3次正常，后2次高延迟
            normal_response = '{"responseType": "SetExpression"}'
            high_latency_response = '{"responseType": "SetExpression"}'

            async def mixed_recv():
                # 前3次正常延迟
                for _ in range(3):
                    await asyncio.sleep(0.5)  # 延迟0.5秒
                    yield normal_response
                # 后2次高延迟
                for _ in range(2):
                    await asyncio.sleep(2)  # 延迟2秒
                    yield high_latency_response

            recv_generator = mixed_recv()

            async def side_effect():
                return await recv_generator.__anext__()

            mock_ws.recv.side_effect = side_effect

            # 设置表情
            for _ in range(5):
                await vtuber.set_expression("happy")

            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)  # watchdog_interval为1秒

            # 验证 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called)
            # 检查 notify_admin 是否被调用至少一次
            self.assertGreaterEqual(mock_notify_admin.call_count, 1)

if __name__ == '__main__':
    unittest.main()

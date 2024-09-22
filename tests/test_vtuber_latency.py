# tests/test_vtuber_latency.py

import unittest
from unittest.mock import patch, AsyncMock
from src.vtuber import VtuberController
import asyncio
import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


class TestVtuberLatency(unittest.IsolatedAsyncioTestCase):
    @patch('src.vtuber.websockets.connect', new_callable=AsyncMock)
    async def test_set_expression_with_normal_latency(self, mock_connect):
        # 模拟WebSocket连接
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # 模拟认证响应
        mock_ws.recv.return_value = '{"apiVersion": 1}'

        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0)
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

        vtuber = VtuberController(api_key="dummy_key", vtuber_name="DummyVtuber", latency_threshold=1.0)
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

if __name__ == '__main__':
    unittest.main()

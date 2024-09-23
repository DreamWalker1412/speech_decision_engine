# tests/test_vtuber_integration.py

import unittest
from unittest.mock import patch, AsyncMock
from src.vtuber import VtuberController
from src.config import VTUBER_CONFIG
import asyncio

class TestVtuberIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """
        设置测试环境，连接到VTubeStudio API。
        """
        self.vtuber = VtuberController(
            api_key=VTUBER_CONFIG["api_key"],
            vtuber_name=VTUBER_CONFIG["vtuber_name"],
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=5.0,  # 增加阈值以避免在测试中触发警报
            watchdog_interval=5.0    # 设置较短的看门狗检查间隔
        )
        await self.vtuber.connect()
    
    async def asyncTearDown(self):
        """
        清理测试环境，关闭与VTubeStudio API的连接。
        """
        await self.vtuber.close()
    
    async def test_set_expression(self):
        """
        测试设置Hiyori_A的表情。
        """
        expression_key = "happy"
        expression_name = self.vtuber.expressions.get(expression_key)
        self.assertIsNotNone(expression_name, f"表达式键 '{expression_key}' 未在配置中定义。")
    
        # 设置表情
        await self.vtuber.set_expression(expression_key)
    
        # 检查是否正确设置
        # 根据VTubeStudio API的功能，添加查询当前表情的逻辑
        # 如果API没有此功能，跳过此步骤
        # 例如：
        # command = {
        #     "requestType": "GetCurrentExpression",
        #     "parameters": {}
        # }
        # await self.vtuber.websocket.send(json.dumps(command))
        # response = await self.vtuber.websocket.recv()
        # response_data = json.loads(response)
        # self.assertEqual(response_data.get("currentExpression"), expression_name)
    
    async def test_set_motion(self):
        """
        测试设置Hiyori_A的动作。
        """
        motion_key = "wave"
        motion_name = self.vtuber.motions.get(motion_key)
        self.assertIsNotNone(motion_name, f"动作键 '{motion_key}' 未在配置中定义。")
    
        # 设置动作
        await self.vtuber.set_motion(motion_key)
    
        # 检查是否正确设置
        # 根据VTubeStudio API的功能，添加查询当前动作的逻辑
        # 如果API没有此功能，跳过此步骤
    
    async def test_multiple_commands(self):
        """
        测试连续发送多个命令（表情和动作）。
        """
        # 设置表情为 happy 并挥手
        await self.vtuber.set_expression("happy")
        await self.vtuber.set_motion("wave")
    
        # 设置表情为 sad 并点头
        await self.vtuber.set_expression("sad")
        await self.vtuber.set_motion("nod")
    
        # 根据API响应进行验证（如果API支持）
    
    async def test_watchdog_alert_trigger(self):
        """
        测试看门狗在延迟超出阈值时是否触发警报。
        """
        # 设置VtuberController的阈值为1秒，watchdog间隔为1秒
        self.vtuber.latency_threshold = 1.0
        self.vtuber.watchdog_interval = 1.0
    
        # Mock notify_admin to track its calls
        with patch.object(self.vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟设置表情时延迟超过阈值
            async def delayed_set_expression(expression_key):
                await asyncio.sleep(2)  # 延迟2秒，超过阈值1秒
                await self.vtuber.set_expression(expression_key)
    
            # 设置表情，模拟高延迟
            await delayed_set_expression("happy")
    
            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)
    
            # 检查 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called, "看门狗未触发警报。")
            mock_notify_admin.assert_awaited_once_with(2.0, 1.0)
    
    async def test_watchdog_does_not_trigger_alert_on_normal_latency(self):
        """
        测试看门狗在延迟正常时不触发警报。
        """
        # 设置VtuberController的阈值为1秒，watchdog间隔为1秒
        self.vtuber.latency_threshold = 1.0
        self.vtuber.watchdog_interval = 1.0
    
        # Mock notify_admin to track its calls
        with patch.object(self.vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟设置表情时正常延迟
            mock_ws = self.vtuber.websocket
            mock_ws.recv.return_value = '{"responseType": "SetExpression"}'
    
            # 设置多个表情，延迟正常
            for _ in range(5):
                await self.vtuber.set_expression("happy")
    
            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)
    
            # 检查 notify_admin 是否未被调用
            mock_notify_admin.assert_not_called()
    
    async def test_watchdog_with_mixed_latency(self):
        """
        测试看门狗在混合延迟情况下的行为。
        """
        # 设置VtuberController的阈值为1秒，watchdog间隔为1秒
        self.vtuber.latency_threshold = 1.0
        self.vtuber.watchdog_interval = 1.0
    
        # Mock notify_admin to track its calls
        with patch.object(self.vtuber, 'notify_admin', new_callable=AsyncMock) as mock_notify_admin:
            # 模拟设置表情：前3次正常延迟，后2次高延迟
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
    
            self.vtuber.websocket.recv.side_effect = side_effect
    
            # 设置表情
            for _ in range(5):
                await self.vtuber.set_expression("happy")
    
            # 等待足够的时间让watchdog检查
            await asyncio.sleep(2)
    
            # 验证 notify_admin 是否被调用
            self.assertTrue(mock_notify_admin.called, "看门狗未触发警报。")
            # 检查 notify_admin 是否被调用至少一次
            self.assertGreaterEqual(mock_notify_admin.call_count, 1)
    
if __name__ == '__main__':
    unittest.main()

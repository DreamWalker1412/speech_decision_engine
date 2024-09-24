# tests/test_vtuber_integration.py

import sys
import os
import unittest
import json
from pathlib import Path
import asyncio
import logging

# 将项目根目录添加到系统路径，以便导入src模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vtuber import VtuberController
from src.config import VTUBER_CONFIG

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestVtuberIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """
        设置测试环境，连接到VTubeStudio API并进行认证。
        """
        # 初始化 VtuberController 实例
        self.vtuber = VtuberController(
            vtuber_name=VTUBER_CONFIG.get("vtuber_name", ""),
            host=VTUBER_CONFIG.get("host", "127.0.0.1"),
            port=VTUBER_CONFIG.get("port", 8001),
            latency_threshold=5.0,    # 设置合理的阈值
            watchdog_interval=5.0      # 设置合理的看门狗检查间隔
        )
        await self.vtuber.connect()

    async def asyncTearDown(self):
        """
        清理测试环境，关闭与VTubeStudio API的连接。
        """
        await self.vtuber.close()

    async def test_authentication_success(self):
        """
        测试成功认证流程。
        """
        self.assertTrue(self.vtuber.authenticated, "认证未成功。")
        logger.info("认证成功。")

    async def test_get_current_model_info(self):
        """
        测试获取当前模型信息功能。
        """
        # Call the method
        model_info = await self.vtuber.get_current_model_info()

        # Verify the results
        self.assertIsNotNone(model_info, "未能获取模型信息。")
        self.assertIn("modelName", model_info, "模型信息中缺少 'modelName' 字段。")
        self.assertIn("modelID", model_info, "模型信息中缺少 'modelID' 字段。")

        logger.info("成功获取并验证当前模型信息。")

    async def test_set_expression(self):
        """
        测试设置Vtuber的表情功能。
        """
        expression_key = "happy"
        expression_name = VTUBER_CONFIG["expressions"].get(expression_key)
        self.assertIsNotNone(expression_name, f"表达式键 '{expression_key}' 未在配置中定义。")

        # 设置表情
        await self.vtuber.set_expression(expression_key)

        # 查询当前表情并验证
        # current_expression = await self.vtuber.get_current_expression()
        # self.assertEqual(current_expression, expression_key, f"当前表情应为 '{expression_key}'，但实际为 '{current_expression}'。")

    async def test_set_motion(self):
        """
        测试设置Vtuber的动作功能。
        """
        motion_key = "wave"
        motion_name = VTUBER_CONFIG["motions"].get(motion_key)
        self.assertIsNotNone(motion_name, f"动作键 '{motion_key}' 未在配置中定义。")

        # 设置动作
        await self.vtuber.set_motion(motion_key)

        # 查询当前动作并验证
        # current_motion = await self.vtuber.get_current_motion()
        # self.assertEqual(current_motion, motion_key, f"当前动作应为 '{motion_key}'，但实际为 '{current_motion}'。")

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

    async def test_watchdog_does_not_trigger_alert_on_normal_latency(self):
        """
        测试看门狗在延迟正常时不触发警报。
        """
        # 设置VtuberController的阈值为1秒，watchdog间隔为1秒
        self.vtuber.latency_threshold = 1.0
        self.vtuber.watchdog_interval = 1.0

        # 重写 notify_admin 方法以记录是否被调用
        async def mock_notify_admin(latency, threshold):
            self.notify_called = True
            self.notify_latency = latency
            self.notify_threshold = threshold

        self.vtuber.notify_admin = mock_notify_admin
        self.notify_called = False
        self.notify_latency = 0
        self.notify_threshold = 0

        # 模拟正常延迟
        original_set_expression = self.vtuber.set_expression

        async def normal_set_expression(expression_key):
            # 模拟延迟
            await asyncio.sleep(0.5)  # 延迟0.5秒，小于阈值1秒
            await original_set_expression(expression_key)

        self.vtuber.set_expression = normal_set_expression

        # 设置表情，模拟正常延迟
        await self.vtuber.set_expression("happy")
        await asyncio.sleep(2)  # 等待watchdog检查

        # 检查 notify_admin 是否未被调用
        self.assertFalse(self.notify_called, "看门狗错误地触发了警报。")

    async def test_get_available_hotkeys(self):
        """
        测试获取当前模型或指定模型的可用热键列表功能。
        """
        # Call the method
        hotkeys_data = await self.vtuber.get_available_hotkeys()

        # Verify the results
        self.assertIsNotNone(hotkeys_data, "未能获取热键列表。")
        self.assertIn("modelName", hotkeys_data, "热键列表中缺少 'modelName' 字段。")
        self.assertIn("availableHotkeys", hotkeys_data, "热键列表中缺少 'availableHotkeys' 字段。")
        self.assertIsInstance(hotkeys_data["availableHotkeys"], list, "'availableHotkeys' 字段应为列表。")

        logger.info("成功获取并验证热键列表。")

    async def test_trigger_hotkey(self):
        """
        测试触发所有指定的热键。
        """
        # Read hotkey IDs from JSON file
        hotkeys_data = self.read_json_file("available_hotkeys.json")
        hotkeys = hotkeys_data["availableHotkeys"]

        for hotkey in hotkeys:
            hotkey_id = hotkey["hotkeyID"]

            # Trigger the hotkey
            triggered_hotkey_id = await self.vtuber.trigger_hotkey(hotkey_id)

            # Verify the results
            self.assertIsNotNone(triggered_hotkey_id, f"未能触发热键 {hotkey_id}。")
            self.assertEqual(triggered_hotkey_id, hotkey_id, f"触发的热键ID {triggered_hotkey_id} 不匹配 {hotkey_id}。")

            logger.info(f"成功触发并验证热键 {hotkey_id}。")

            # Wait for a short duration to allow the hotkey to execute
            await asyncio.sleep(2)  # Adjust the duration as needed

    async def test_trigger_animation(self):
        """
        测试触发所有指定名称的动画热键。
        """
        # Read animation names from JSON file
        hotkeys_data = self.read_json_file("available_hotkeys.json")
        animations = [hotkey for hotkey in hotkeys_data["availableHotkeys"] if hotkey["type"] == "TriggerAnimation"]

        for animation in animations:
            animation_name = animation["name"]

            # Trigger the animation
            triggered_hotkey_id = await self.vtuber.trigger_animation(animation_name)

            # Verify the results
            self.assertIsNotNone(triggered_hotkey_id, f"未能触发动画热键 {animation_name}。")

            logger.info(f"成功触发并验证动画热键 {animation_name}。")

            # Wait for a short duration to allow the animation to execute
            await asyncio.sleep(2)  # Adjust the duration as needed
    
    async def test_get_expression_list(self):
        """
        测试获取当前模型的表情列表功能。
        """
        # Call the method
        expressions_data = await self.vtuber.get_expression_list()

        # Verify the results
        self.assertIsNotNone(expressions_data, "未能获取表情列表。")
        self.assertIn("modelName", expressions_data, "表情列表中缺少 'modelName' 字段。")
        self.assertIn("expressions", expressions_data, "表情列表中缺少 'expressions' 字段。")
        self.assertIsInstance(expressions_data["expressions"], list, "'expressions' 字段应为列表。")

        logger.info("成功获取并验证表情列表。")

    async def test_activate_expression(self):
        """
        测试激活和停用所有指定的表情。
        """
        # Read expression data from JSON file
        expressions_data = self.read_json_file("available_expressions.json")
        expressions = expressions_data["expressions"]

        for expression in expressions:
            expression_file = expression["file"]

            # Activate the expression
            result = await self.vtuber.activate_expression(expression_file, active=True, fade_time=0.5)
            self.assertTrue(result, f"未能激活表情 {expression_file}。")
            logger.info(f"成功激活表情 {expression_file}。")

            # Wait for a short duration to allow the expression to activate
            await asyncio.sleep(2)  # Adjust the duration as needed

            # Deactivate the expression
            result = await self.vtuber.activate_expression(expression_file, active=False, fade_time=0.5)
            self.assertTrue(result, f"未能停用表情 {expression_file}。")
            logger.info(f"成功停用表情 {expression_file}。")

            # Wait for a short duration to allow the expression to deactivate
            await asyncio.sleep(2)  # Adjust the duration as needed

    async def test_get_tracking_parameters(self):
        """
        测试获取当前可用的跟踪参数列表功能。
        """
        # Call the method
        tracking_parameters = await self.vtuber.get_tracking_parameters()

        # Verify the results
        self.assertIsNotNone(tracking_parameters, "未能获取跟踪参数列表。")
        self.assertIn("modelName", tracking_parameters, "跟踪参数列表中缺少 'modelName' 字段。")
        self.assertIn("defaultParameters", tracking_parameters, "跟踪参数列表中缺少 'parameters' 字段。")
        self.assertIn("customParameters", tracking_parameters, "跟踪参数列表中缺少 'parameters' 字段。")
        self.assertIsInstance(tracking_parameters["defaultParameters"], list, "'defaultParameters' 字段应为列表。")
        self.assertIsInstance(tracking_parameters["customParameters"], list, "'customParameters' 字段应为列表。")

        logger.info("成功获取并验证跟踪参数列表。")

    async def test_get_parameter_value(self):
        """
        测试获取所有指定的参数的当前值。
        """
        # Read tracking parameters from JSON file
        tracking_parameters_data = self.read_json_file("tracking_parameters.json")
        parameters = tracking_parameters_data["defaultParameters"]

        for parameter in parameters:
            parameter_name = parameter["name"]

            # Get the parameter value
            parameter_data = await self.vtuber.get_parameter_value(parameter_name)

            # Verify the results
            self.assertIsNotNone(parameter_data, f"未能获取参数 '{parameter_name}' 的值。")
            self.assertIn("name", parameter_data, f"参数数据中缺少 'name' 字段。")
            self.assertIn("value", parameter_data, f"参数数据中缺少 'value' 字段。")
            self.assertEqual(parameter_data["name"], parameter_name, f"参数名称不匹配。期望: {parameter_name}, 实际: {parameter_data['name']}")

            logger.info(f"成功获取并验证参数 '{parameter_name}' 的值。")

            # Wait for a short duration to avoid rate limiting
            await asyncio.sleep(0.1)  # Adjust the duration as needed

    async def test_get_multiple_parameter_values(self):
        """
        测试获取多个参数的当前值功能。
        """
        # Read tracking parameters from JSON file
        tracking_parameters_data = self.read_json_file("tracking_parameters.json")
        parameters = tracking_parameters_data["defaultParameters"]
        parameter_names = [parameter["name"] for parameter in parameters]

        # Get the parameter values
        parameter_values = await self.vtuber.get_multiple_parameter_values(parameter_names)

        # Verify the results
        for parameter_name, parameter_data in zip(parameter_names, parameter_values):
            self.assertIsNotNone(parameter_data, f"未能获取参数 '{parameter_name}' 的值。")
            self.assertIn("name", parameter_data, f"参数数据中缺少 'name' 字段。")
            self.assertIn("value", parameter_data, f"参数数据中缺少 'value' 字段。")
            self.assertEqual(parameter_data["name"], parameter_name, f"参数名称不匹配。期望: {parameter_name}, 实际: {parameter_data['name']}")

            logger.info(f"成功获取并验证参数 '{parameter_name}' 的值。")

            # Wait for a short duration to avoid rate limiting
            await asyncio.sleep(0.1)  # Adjust the duration as needed

    def read_json_file(self, filename):
        """
        读取 JSON 文件并返回数据。
        """
        resources_dir = Path(__file__).resolve().parents[1] / "resources"
        file_path = resources_dir / filename

        with open(file_path, 'r', encoding="utf8") as f:
            data = json.load(f)
        return data

if __name__ == '__main__':
    unittest.main()

# src/vtuber.py

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional
import websockets
from .config import VTUBER_CONFIG

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class VtuberController:
    def __init__(self, vtuber_name: str, host: str, port: int,
                 latency_threshold: float, watchdog_interval: float):
        self.vtuber_name = vtuber_name
        self.host = VTUBER_CONFIG["host"]  # Use host from config
        self.port = VTUBER_CONFIG["port"]  # Use port from config
        self.latency_threshold = latency_threshold
        self.watchdog_interval = watchdog_interval
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.latencies = []
        self.watchdog_task = None
        self.authenticated = False
        self.token_file = Path(__file__).resolve().parents[1] / "secrets" / "vtubestudio_auth_token.txt"
        self.model_info = None

    async def request_authentication_token(self):
        """
        请求认证令牌。
        """
        logger.info("请求认证令牌。")
        request_id = "AuthRequest_" + os.urandom(8).hex()
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": "AuthenticationTokenRequest",
            "data": {
                "pluginName": VTUBER_CONFIG["pluginName"],
                "pluginDeveloper": VTUBER_CONFIG["pluginDeveloper"],
                "pluginIcon": VTUBER_CONFIG["pluginIcon"]
            }
        }
        await self.websocket.send(json.dumps(request))
        logger.info("已发送 AuthenticationTokenRequest，请在 VTube Studio 中授权。")

        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=30)  # 等待30秒用户授权
            response_data = json.loads(response)
            if response_data.get("messageType") == "AuthenticationTokenResponse":
                token = response_data["data"]["authenticationToken"]
                logger.info("成功获取认证令牌。")
                # 存储令牌
                self.store_token(token)
                return token
            elif response_data.get("messageType") == "APIError":
                error_message = response_data["data"].get("message", "未知错误。")
                logger.error(f"认证令牌请求失败: {error_message}")
                return None
            else:
                logger.error("收到未知的认证令牌响应。")
                return None
        except asyncio.TimeoutError:
            logger.error("等待认证令牌超时，用户可能未授权。")
            return None

    def store_token(self, token: str):
        """
        存储认证令牌到文件。
        """
        # Ensure the directory exists
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.token_file, 'w', encoding="utf8") as f:
            f.write(token)
        logger.info(f"认证令牌已存储到 {self.token_file}")

    def load_token(self) -> Optional[str]:
        """
        从文件加载认证令牌。
        """
        if self.token_file.exists():
            with open(self.token_file, 'r') as f:
                token = f.read().strip()
                logger.info("成功加载认证令牌。")
                return token
        else:
            logger.warning("未找到认证令牌。")
            return None

    async def authenticate(self):
        """
        使用认证令牌进行认证。
        """
        logger.info("开始认证。")
        token = self.load_token()
        if not token:
            token = await self.request_authentication_token()
            if not token:
                logger.error("无法获取认证令牌，认证失败。")
                return False

        request_id = "AuthSession_" + os.urandom(8).hex()
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": VTUBER_CONFIG["pluginName"],
                "pluginDeveloper": VTUBER_CONFIG["pluginDeveloper"],
                "authenticationToken": token
            }
        }
        await self.websocket.send(json.dumps(request))
        logger.info("已发送 AuthenticationRequest。")

        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)  # 等待10秒认证响应
            response_data = json.loads(response)
            if response_data.get("messageType") == "AuthenticationResponse":
                if response_data["data"].get("authenticated"):
                    logger.info("认证成功。")
                    self.authenticated = True
                    return True
                else:
                    reason = response_data["data"].get("reason", "未知原因。")
                    logger.error(f"认证失败: {reason}")
                    return False
            elif response_data.get("messageType") == "APIError":
                error_message = response_data["data"].get("message", "未知错误。")
                logger.error(f"认证请求失败: {error_message}")
                return False
            else:
                logger.error("收到未知的认证响应。")
                return False
        except asyncio.TimeoutError:
            logger.error("等待认证响应超时。")
            return False

    async def connect(self):
        """
        连接到 VTube Studio API 并进行认证。
        """
        # Use host and port from config
        host = self.host
        port = self.port

        uri = f"ws://{host}:{port}/"
        try:
            logger.info(f"连接到 {uri}")
            self.websocket = await websockets.connect(uri)
            authenticated = await self.authenticate()
            if not authenticated:
                logger.error("认证失败，无法继续连接。")
                await self.close()
                return
            logger.info("成功连接并认证到 VTube Studio API。")
            # 启动看门狗任务
            self.watchdog_task = asyncio.create_task(self.watchdog())
        except Exception as e:
            logger.exception(f"连接到 VTube Studio 失败: {e}")

    async def close(self):
        """
        关闭与 VTube Studio API 的连接。
        """
        if self.watchdog_task:
            self.watchdog_task.cancel()
            try:
                await self.watchdog_task
            except asyncio.CancelledError:
                pass
        if self.websocket:
            await self.websocket.close()
            logger.info("已关闭与 VTube Studio 的连接。")

    async def set_expression(self, expression_key: str):
        """
        设置 Vtuber 的表情。
        """
        if not self.authenticated:
            logger.warning("尚未认证，无法设置表情。")
            return
        expression_name = VTUBER_CONFIG["expressions"].get(expression_key)
        if not expression_name:
            logger.error(f"未知的表情键: {expression_key}")
            return
        request_id = "SetExpression_" + os.urandom(8).hex()
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": "SetExpression",
            "data": {
                "expressionName": expression_name
            }
        }
        start_time = asyncio.get_event_loop().time()
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        end_time = asyncio.get_event_loop().time()
        latency = end_time - start_time
        self.latencies.append(latency)
        logger.info(f"设置表情 '{expression_name}'，延迟: {latency:.2f} 秒")
        # 检查延迟
        if latency > self.latency_threshold:
            await self.notify_admin(latency, self.latency_threshold)

    async def set_motion(self, motion_key: str):
        """
        设置 Vtuber 的动作。
        """
        if not self.authenticated:
            logger.warning("尚未认证，无法设置动作。")
            return
        motion_name = VTUBER_CONFIG["motions"].get(motion_key)
        if not motion_name:
            logger.error(f"未知的动作键: {motion_key}")
            return
        request_id = "SetMotion_" + os.urandom(8).hex()
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": "SetMotion",
            "data": {
                "motionName": motion_name
            }
        }
        start_time = asyncio.get_event_loop().time()
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        end_time = asyncio.get_event_loop().time()
        latency = end_time - start_time
        self.latencies.append(latency)
        logger.info(f"设置动作 '{motion_name}'，延迟: {latency:.2f} 秒")
        # 检查延迟
        if latency > self.latency_threshold:
            await self.notify_admin(latency, self.latency_threshold)

    async def get_current_model_info(self):
        """
        获取当前模型信息，并将其存储到文件。
        """
        if not self.websocket:
            logger.warning("尚未连接到VTubeStudio API")
            return None

        try:
            current_model_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "GetCurrentModelInfo",
                "messageType": "CurrentModelRequest"
            }
            await self.websocket.send(json.dumps(current_model_request))
            response = await self.websocket.recv()
            model_data = json.loads(response)

            if model_data["data"]["modelLoaded"]:
                self.model_info = model_data["data"]
                logger.info("成功获取当前模型信息")
                # 保存模型信息到文件
                self.save_to_file("current_model_info.json", json.dumps(self.model_info, ensure_ascii=False, indent=4))
                return self.model_info
            else:
                logger.warning("当前没有加载模型")
                return None

        except Exception as e:
            logger.error(f"获取当前模型信息时出错: {e}")
            return None


    async def update_model_info(self):
        """
        手动更新当前模型信息。
        """
        await self.get_current_model_info()

    async def get_current_motion(self):
        """
        获取当前Vtuber的动作。
        """
        if not self.websocket:
            logger.warning("尚未连接到VTubeStudio API")
            return None

        try:
            if self.model_info:
                # 获取当前模型的热键信息
                hotkeys_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "GetHotkeys",
                    "messageType": "HotkeysInCurrentModelRequest"
                }
                await self.websocket.send(json.dumps(hotkeys_request))
                response = await self.websocket.recv()
                hotkeys_data = json.loads(response)

                # 查找激活的动作热键
                for hotkey in hotkeys_data["data"]["availableHotkeys"]:
                    if hotkey["type"] == "TriggerAnimation" and hotkey["isActive"]:
                        # 找到匹配的动作键
                        for motion_key, motion_name in VTUBER_CONFIG["motions"].items():
                            if motion_name == hotkey["file"]:
                                # 保存到文件
                                self.save_to_file("current_motion.txt", motion_key)
                                return motion_key

            logger.info("未找到当前激活的动作")
            return None

        except Exception as e:
            logger.error(f"获取当前动作时出错: {e}")
            return None

    async def get_current_expression(self):
        """
        获取当前Vtuber的表情。
        """
        if not self.websocket:
            logger.warning("尚未连接到VTubeStudio API")
            return None

        try:
            # 获取当前表情状态
            expression_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "GetExpressions",
                "messageType": "ExpressionStateRequest"
            }
            await self.websocket.send(json.dumps(expression_request))
            response = await self.websocket.recv()
            expression_data = json.loads(response)

            # 查找激活的表情
            for expression in expression_data["data"]["expressions"]:
                if expression["active"]:
                    # 找到匹配的表情键
                    for expression_key, expression_name in VTUBER_CONFIG["expressions"].items():
                        if expression_name == expression["name"]:
                            # 保存到文件
                            self.save_to_file("current_expression.txt", expression_key)
                            return expression_key

            logger.info("未找到当前激活的表情")
            return None

        except Exception as e:
            logger.error(f"获取当前表情时出错: {e}")
            return None
        
    async def get_available_hotkeys(self, model_id: Optional[str] = None):
        """
        获取当前模型或指定模型的可用热键列表。

        :param model_id: 可选的模型ID。如果不提供，则获取当前加载模型的热键。
        :return: 包含热键信息的字典，或在出错时返回None。
        """
        if not self.authenticated:
            logger.warning("尚未认证，无法获取热键列表。")
            return None

        request_id = "GetHotkeys_" + os.urandom(8).hex()
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": "HotkeysInCurrentModelRequest",
            "data": {}
        }

        if model_id:
            request["data"]["modelID"] = model_id

        try:
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data.get("messageType") == "HotkeysInCurrentModelResponse":
                hotkeys_data = response_data["data"]
                
                # 将热键信息保存到文件
                self.save_to_file("available_hotkeys.json", json.dumps(hotkeys_data, ensure_ascii=False, indent=4))
                
                logger.info(f"成功获取热键列表。模型: {hotkeys_data['modelName']}, 热键数量: {len(hotkeys_data['availableHotkeys'])}")
                return hotkeys_data
            elif response_data.get("messageType") == "APIError":
                error_message = response_data["data"].get("message", "未知错误。")
                logger.error(f"获取热键列表失败: {error_message}")
                return None
            else:
                logger.error("收到未知的热键列表响应。")
                return None

        except Exception as e:
            logger.exception(f"获取热键列表时发生错误: {e}")
            return None
        
    async def trigger_hotkey(self, hotkey_identifier: str, item_instance_id: Optional[str] = None):
        """
        触发指定的热键。

        :param hotkey_identifier: 热键的唯一ID或名称
        :param item_instance_id: 可选的Live2D项目实例ID，用于在特定Live2D项目上触发热键
        :return: 触发的热键ID，如果失败则返回None
        """
        if not self.websocket:
            logger.warning("尚未连接到VTubeStudio API")
            return None

        try:
            request_id = "TriggerHotkey_" + os.urandom(8).hex()
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": request_id,
                "messageType": "HotkeyTriggerRequest",
                "data": {
                    "hotkeyID": hotkey_identifier
                }
            }

            if item_instance_id:
                request["data"]["itemInstanceID"] = item_instance_id

            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data["messageType"] == "HotkeyTriggerResponse":
                triggered_hotkey_id = response_data["data"]["hotkeyID"]
                logger.info(f"成功触发热键: {triggered_hotkey_id}")
                
                # 保存触发的热键信息到文件
                self.save_to_file("last_triggered_hotkey.txt", f"Hotkey ID: {triggered_hotkey_id}\nTriggered at: {response_data['timestamp']}")
                
                return triggered_hotkey_id
            else:
                error_message = response_data.get("data", {}).get("message", "未知错误")
                logger.error(f"触发热键失败: {error_message}")
                return None

        except Exception as e:
            logger.exception(f"触发热键时发生错误: {e}")
            return None

    async def trigger_animation(self, animation_name: str):
        """
        触发指定名称的动画热键。

        :param animation_name: 动画的名称
        :return: 触发的热键ID，如果失败则返回None
        """
        try:
            # 首先获取可用的热键列表
            hotkeys_data = await self.get_available_hotkeys()
            if not hotkeys_data:
                logger.error("无法获取热键列表")
                return None

            # 查找匹配的动画热键
            matching_hotkey = next(
                (hotkey for hotkey in hotkeys_data['availableHotkeys'] 
                if hotkey['type'] == 'TriggerAnimation' and hotkey['name'] == animation_name),
                None
            )

            if matching_hotkey:
                return await self.trigger_hotkey(matching_hotkey['hotkeyID'])
            else:
                logger.error(f"未找到名为 '{animation_name}' 的动画热键")
                return None

        except Exception as e:
            logger.exception(f"触发动画时发生错误: {e}")
            return None
    
    async def get_expression_list(self, details: bool = True, expression_file: Optional[str] = None):
        """
        获取当前模型的表情列表，并将信息保存到文件。

        :param details: 是否请求详细信息
        :param expression_file: 可选的特定表情文件名
        :return: 包含表情信息的字典，如果出错则返回None
        """
        if not self.websocket:
            logger.warning("尚未连接到VTubeStudio API")
            return None

        try:
            request_id = "GetExpressions_" + os.urandom(8).hex()
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": request_id,
                "messageType": "ExpressionStateRequest",
                "data": {
                    "details": details
                }
            }

            if expression_file:
                request["data"]["expressionFile"] = expression_file

            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data["messageType"] == "ExpressionStateResponse":
                expressions_data = response_data["data"]
                
                if expressions_data["modelLoaded"]:
                    logger.info(f"成功获取表情列表。模型: {expressions_data['modelName']}, 表情数量: {len(expressions_data['expressions'])}")
                    
                    # 保存完整的表情信息到JSON文件
                    self.save_to_file("available_expressions.json", json.dumps(expressions_data, ensure_ascii=False, indent=4))
                    
                    return expressions_data
                else:
                    logger.warning("当前没有加载模型，无法获取表情信息")
                    return None
            else:
                error_message = response_data.get("data", {}).get("message", "未知错误")
                logger.error(f"获取表情列表失败: {error_message}")
                return None

        except Exception as e:
            logger.exception(f"获取表情列表时发生错误: {e}")
            return None

    def save_to_file(self, filename: str, data: str):
        """
        将数据保存到 ../resources 目录中的文件。
        """
        resources_dir = Path(__file__).resolve().parents[1] / "resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        file_path = resources_dir / filename

        with open(file_path, 'w', encoding="utf8") as f:
            f.write(data)
        logger.info(f"数据已保存到 {file_path}")

    async def watchdog(self):
        """
        看门狗任务，定期检查延迟是否超过阈值。
        """
        logger.info("启动看门狗任务。")
        try:
            while True:
                if self.latencies:
                    avg_latency = sum(self.latencies[-VTUBER_CONFIG["latency_window"]:]) / min(len(self.latencies), VTUBER_CONFIG["latency_window"])
                    logger.info(f"平均延迟: {avg_latency:.2f} 秒")
                    if avg_latency > self.latency_threshold:
                        await self.notify_admin(avg_latency, self.latency_threshold)
                await asyncio.sleep(VTUBER_CONFIG["watchdog_interval"])
        except asyncio.CancelledError:
            logger.info("看门狗任务已取消。")

    async def notify_admin(self, latency: float, threshold: float):
        """
        通知管理员延迟超标。
        """
        logger.warning(f"延迟 {latency:.2f} 秒超过阈值 {threshold:.2f} 秒！")
        # 在此处添加通知管理员的逻辑，例如发送邮件或消息

# vtuber.py

import asyncio
import websockets
import json
from typing import Optional

class VtuberController:
    def __init__(self, api_key: str, vtuber_name: str, host: str = "127.0.0.1", port: int = 8001):
        """
        初始化Vtuber控制器。
        
        :param api_key: VTubeStudio的API密钥
        :param vtuber_name: Vtuber的名称
        :param host: VTubeStudio API的主机地址
        :param port: VTubeStudio API的端口号
        """
        self.api_key = api_key
        self.vtuber_name = vtuber_name
        self.uri = f"ws://{host}:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False

    async def connect(self):
        """
        连接到VTubeStudio的WebSocket API，并进行身份验证。
        """
        try:
            self.websocket = await websockets.connect(self.uri)
            await self.authenticate()
            self.connected = True
            print("成功连接到VTubeStudio API")
        except Exception as e:
            print(f"无法连接到VTubeStudio API: {e}")

    async def authenticate(self):
        """
        发送认证请求到VTubeStudio API。
        """
        auth_request = {
            "pluginName": "AI Vtuber Controller",
            "requestedApiVersion": 1
        }
        await self.websocket.send(json.dumps(auth_request))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        if response_data.get("apiVersion"):
            print("认证成功")
        else:
            print("认证失败")
            raise ConnectionError("VTubeStudio API认证失败")

    async def set_expression(self, expression_name: str):
        """
        设置Vtuber的表情。
        
        :param expression_name: 表情名称，例如 "happy", "sad" 等
        """
        if not self.connected or not self.websocket:
            print("尚未连接到VTubeStudio API")
            return
        
        command = {
            "requestType": "SetExpression",
            "parameters": {
                "expressionName": expression_name
            }
        }
        try:
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            if response_data.get("responseType") == "SetExpression":
                print(f"成功设置表情为: {expression_name}")
            else:
                print(f"设置表情失败: {response_data}")
        except Exception as e:
            print(f"设置表情时出错: {e}")

    async def close(self):
        """
        关闭与VTubeStudio API的连接。
        """
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("已断开与VTubeStudio API的连接")

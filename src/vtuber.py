# src/vtuber.py

import asyncio
import websockets
import json
import time
from typing import Optional, Deque
from collections import deque
import statistics
import logging
import os

from src.config import VTUBER_CONFIG

# Create logs directory if it doesn't exist
logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(logs_dir, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "vtuber_controller.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class VtuberController:
    def __init__(
        self, 
        api_key: str, 
        vtuber_name: str, 
        host: str = "127.0.0.1", 
        port: int = 8001,
        latency_window: int = 100,
        latency_threshold: float = 2.0,
        watchdog_interval: float = 10.0  # 新增参数，默认10秒
    ):
        """
        初始化Vtuber控制器。

        :param api_key: VTubeStudio的API密钥
        :param vtuber_name: Vtuber的名称
        :param host: VTubeStudio API的主机地址
        :param port: VTubeStudio API的端口号
        :param latency_window: 用于计算统计数据的延迟记录数量
        :param latency_threshold: 延迟阈值（秒）
        :param watchdog_interval: 看门狗检查间隔（秒）
        """
        self.api_key = api_key
        self.vtuber_name = vtuber_name
        self.uri = f"ws://{host}:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False

        # 延迟监控
        self.latencies: Deque[float] = deque(maxlen=latency_window)
        self.latency_lock = asyncio.Lock()

        # 看门狗阈值
        self.latency_threshold = latency_threshold  # 秒
        self.watchdog_interval = watchdog_interval  # 秒
        self.watchdog_task = None

    async def connect(self):
        """
        连接到VTubeStudio的WebSocket API，并进行身份验证。
        """
        try:
            self.websocket = await websockets.connect(self.uri)
            await self.authenticate()
            self.connected = True
            logging.info("成功连接到VTubeStudio API")

            # 启动看门狗任务
            self.watchdog_task = asyncio.create_task(self.watchdog())
        except Exception as e:
            logging.error(f"无法连接到VTubeStudio API: {e}")

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
            logging.info("认证成功")
        else:
            logging.error("认证失败")
            raise ConnectionError("VTubeStudio API认证失败")

    async def set_expression(self, expression_name: str):
        """
        设置Vtuber的表情，并记录延迟。

        :param expression_name: 表情名称，例如 "happy", "sad" 等
        """
        if not self.connected or not self.websocket:
            logging.warning("尚未连接到VTubeStudio API")
            return
        
        command = {
            "requestType": "SetExpression",
            "parameters": {
                "expressionName": expression_name
            }
        }

        try:
            start_time = time.perf_counter()
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            end_time = time.perf_counter()

            latency = end_time - start_time
            async with self.latency_lock:
                self.latencies.append(latency)

            response_data = json.loads(response)
            if response_data.get("responseType") == "SetExpression":
                logging.info(f"成功设置表情为: {expression_name}，延迟: {latency:.3f} 秒")
            else:
                logging.error(f"设置表情失败: {response_data}")
        except Exception as e:
            logging.error(f"设置表情时出错: {e}")

    async def close(self):
        """
        关闭与VTubeStudio API的连接。
        """
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logging.info("已断开与VTubeStudio API的连接")
        
        # 取消看门狗任务
        if self.watchdog_task:
            self.watchdog_task.cancel()
            try:
                await self.watchdog_task
            except asyncio.CancelledError:
                logging.info("看门狗任务已取消")

    async def watchdog(self):
        """
        看门狗任务，定期检查延迟是否超出阈值。
        """
        try:
            while True:
                await asyncio.sleep(self.watchdog_interval)  # 使用配置的间隔时间
                async with self.latency_lock:
                    if len(self.latencies) == 0:
                        continue
                    mean_latency = statistics.mean(self.latencies)
                    std_latency = statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0.0

                logging.info(f"平均延迟: {mean_latency:.3f} 秒，标准差: {std_latency:.3f} 秒")
                if mean_latency > self.latency_threshold:
                    logging.warning(f"警报：平均延迟 {mean_latency:.3f} 秒超过阈值 {self.latency_threshold} 秒！")
                    # 在此处添加进一步的处理逻辑，例如重新连接、记录日志或发送通知
                    await self.notify_admin(mean_latency, self.latency_threshold)
        except asyncio.CancelledError:
            logging.info("看门狗任务已取消")

    async def notify_admin(self, mean_latency: float, threshold: float):
        """
        通知管理员延迟异常。
        这里仅记录日志，实际可集成邮件、短信等通知系统。
        """
        message = f"警报：Vtuber表情设置的平均延迟 {mean_latency:.3f} 秒超过阈值 {threshold} 秒！"
        logging.warning(f"通知管理员: {message}")
        # TODO: 集成实际的通知系统，例如发送邮件或短信

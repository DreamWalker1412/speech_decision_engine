# src/config.py

# 可以在这里集中管理所有配置参数
ASR_CONFIG = {
    "model": "placeholder_for_asr_model",
    # 其他ASR相关配置
}

NLU_CONFIG = {
    "model": "placeholder_for_nlu_model",
    # 其他NLU相关配置
}

TTS_CONFIG = {
    "model": "placeholder_for_tts_model",
    # 其他TTS相关配置
}

VTUBER_CONFIG = {
    "api_key": "your_api_key",
    "vtuber_name": "Hiyori_A",  # 使用Hiyori_A模型
    "host": "127.0.0.1",
    "port": 8001,
    "latency_window": 100,       # 延迟记录窗口大小
    "latency_threshold": 2.0,    # 延迟阈值（秒）
    "watchdog_interval": 10.0,   # 看门狗检查间隔（秒）
    # Hiyori_A 特定配置
    "expressions": {
        "happy": "Hiyori_Happy",
        "sad": "Hiyori_Sad",
        "thinking": "Hiyori_Thinking",
        "concerned": "Hiyori_Concerned",
        "neutral": "Hiyori_Neutral"
    },
    "motions": {
        "wave": "Hiyori_Wave",
        "nod": "Hiyori_Nod",
        # 添加更多动作
    }
}

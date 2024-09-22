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
    "vtuber_name": "YourVtuber",
    "host": "127.0.0.1",
    "port": 8001,
    "latency_window": 100,       # 延迟记录窗口大小
    "latency_threshold": 2.0,    # 延迟阈值（秒）
    # 其他Vtuber相关配置
}

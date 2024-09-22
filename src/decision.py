# decision.py

async def should_respond(analysis: dict) -> bool:
    """
    决定是否回应用户，根据意图的置信度和优先级。
    这里预留接口，待具体实现。
    
    :param analysis: NLU分析结果
    :return: 是否应该回应
    """
    raise NotImplementedError("决策逻辑尚未实现")

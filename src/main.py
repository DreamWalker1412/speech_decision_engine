# src/main.py

import asyncio
from asr import transcribe_audio
from nlu import analyze_text
from decision import should_respond
from response import ResponseGenerator
from context import ContextManager
from vtuber import VtuberController

async def process_audio_async(audio_path: str, response_generator: ResponseGenerator, context_manager: ContextManager):
    try:
        # 步骤1：转录音频
        transcribed_text = await transcribe_audio(audio_path)
        print(f"Transcribed Text: {transcribed_text}")

        # 步骤2：分析文本
        analysis = await analyze_text(transcribed_text)
        print(f"Analysis: {analysis}")

        # 步骤3：决策是否回应
        try:
            should_reply = await should_respond(analysis)
        except NotImplementedError:
            print("决策逻辑未实现，默认不回应")
            should_reply = False

        if should_reply:
            # 步骤4：生成响应
            response_text = await response_generator.generate_response(transcribed_text.lower(), analysis)
            print(f"Response Text: {response_text}")

            # 维护上下文
            context_manager.add_to_history(transcribed_text, response_text)

            # 步骤5：文本转语音
            from tts import text_to_speech  # 避免循环导入
            output_audio = "response.mp3"
            await text_to_speech(response_text, output_audio)
        else:
            print("No response triggered.")
    except NotImplementedError as nie:
        print(f"功能未实现: {nie}")
    except Exception as e:
        print(f"Error processing audio: {e}")

async def main_async():
    # 配置
    API_KEY = "your_api_key"  # 替换为您的VTubeStudio API密钥
    VTUBER_NAME = "YourVtuber"  # 替换为您的Vtuber名称

    # 初始化模块
    context_manager = ContextManager()
    vtuber = VtuberController(api_key=API_KEY, vtuber_name=VTUBER_NAME)
    await vtuber.connect()
    response_generator = ResponseGenerator(vtuber=vtuber)

    # 音频文件路径（示例）
    audio_path = "user_input.wav"

    # 运行主流程
    await process_audio_async(audio_path, response_generator, context_manager)

    # 关闭Vtuber控制器
    await vtuber.close()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

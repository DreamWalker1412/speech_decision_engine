# src/response.py

from vtuber import VtuberController

class ResponseGenerator:
    def __init__(self, vtuber: VtuberController):
        self.vtuber = vtuber

    async def generate_response(self, text: str, analysis: dict) -> str:
        intent = analysis.get("intent")
        sentiment = analysis.get("sentiment")

        if intent == "greet":
            await self.vtuber.set_expression("happy")
            return "Hello! How can I assist you today?"
        elif intent == "ask_help":
            await self.vtuber.set_expression("thinking")
            return "Sure, I'm here to help. What do you need assistance with?"
        elif intent == "goodbye":
            await self.vtuber.set_expression("sad")
            return "Goodbye! Have a great day!"
        elif intent == "book_flight":
            await self.vtuber.set_expression("neutral")
            location = analysis.get("entities", {}).get("location", "your desired destination")
            return f"Sure, I can help you book a flight to {location}. When would you like to travel?"
        else:
            if sentiment == "positive":
                await self.vtuber.set_expression("happy")
                return "I'm glad to hear that! How can I assist you further?"
            elif sentiment == "negative":
                await self.vtuber.set_expression("concerned")
                return "I'm sorry you're feeling that way. How can I help?"
            else:
                await self.vtuber.set_expression("neutral")
                return "I'm not sure how to respond to that. Could you please elaborate?"

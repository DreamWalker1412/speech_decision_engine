# context.py

class ContextManager:
    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history

    def add_to_history(self, user_input: str, ai_response: str):
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append({"user": user_input, "ai": ai_response})

    def get_context(self) -> list:
        return self.history

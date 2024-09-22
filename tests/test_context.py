# tests/test_context.py

import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.context import ContextManager



class TestContextManager(unittest.TestCase):
    def test_add_and_retrieve_history(self):
        cm = ContextManager(max_history=2)
        cm.add_to_history("Hello", "Hi there!")
        cm.add_to_history("How are you?", "I'm good, thank you!")
        self.assertEqual(len(cm.get_context()), 2)
        cm.add_to_history("Goodbye", "See you later!")
        self.assertEqual(len(cm.get_context()), 2)
        self.assertEqual(cm.get_context()[0]["user"], "How are you?")
        self.assertEqual(cm.get_context()[1]["user"], "Goodbye")

if __name__ == '__main__':
    unittest.main()

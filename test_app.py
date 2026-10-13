import unittest
from streamlit.testing.v1 import AppTest
class AppTests(unittest.TestCase):
    def test_no_liftoff_message(self):
        a=AppTest.from_file('app.py').run(timeout=30)
        self.assertFalse(a.exception)
        a.sidebar.number_input[2].set_value(0.0).run(timeout=30)
        self.assertFalse(a.exception)
        self.assertTrue(a.warning)

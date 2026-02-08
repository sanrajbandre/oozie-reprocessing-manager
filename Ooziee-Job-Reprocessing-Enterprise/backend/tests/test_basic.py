import unittest

class TestBasic(unittest.TestCase):
    def test_import(self):
        import app.main  # noqa

if __name__ == "__main__":
    unittest.main()

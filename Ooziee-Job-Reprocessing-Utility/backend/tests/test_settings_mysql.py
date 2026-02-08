import unittest

from app.settings import Settings


class TestMySQLSettings(unittest.TestCase):
    def test_mysql_url_requires_mysql_pymysql_scheme(self):
        settings = Settings(
            DB_URL="mysql://user:pass@127.0.0.1:3306/db?charset=utf8mb4",
            JWT_SECRET="a" * 32,
        )
        with self.assertRaises(RuntimeError):
            settings.validate_runtime()

    def test_mysql_url_requires_utf8mb4_charset(self):
        settings = Settings(
            DB_URL="mysql+pymysql://user:pass@127.0.0.1:3306/db",
            JWT_SECRET="a" * 32,
        )
        with self.assertRaises(RuntimeError):
            settings.validate_runtime()

    def test_mysql_url_valid(self):
        settings = Settings(
            DB_URL="mysql+pymysql://user:pass@127.0.0.1:3306/db?charset=utf8mb4",
            JWT_SECRET="a" * 32,
        )
        settings.validate_runtime()


if __name__ == "__main__":
    unittest.main()

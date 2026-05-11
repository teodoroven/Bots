from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from sqlalchemy.engine import make_url

from db.session import build_postgres_url


class DatabaseSessionSettingsTest(unittest.TestCase):

    def test_build_postgres_url_encodes_credentials_and_database_name(self):
        env: dict[str, str] = {
            "DATABASE_DRIVER": "postgresql+psycopg",
            "DATABASE_HOST": "db",
            "DATABASE_PORT": "5432",
            "DATABASE_USER": "bot@user",
            "DATABASE_PASSWORD": "pa:ss/wo@rd%42",
            "DATABASE_NAME": "autocenter",
        }

        with patch.dict(os.environ, env, clear = True):
            url: str = build_postgres_url()

        self.assertEqual(
            url,
            "postgresql+psycopg://bot%40user:pa%3Ass%2Fwo%40rd%2542@db:5432/autocenter",
        )

        parsed_url = make_url(url)
        self.assertEqual(parsed_url.username, "bot@user")
        self.assertEqual(parsed_url.password, "pa:ss/wo@rd%42")
        self.assertEqual(parsed_url.database, "autocenter")


if __name__ == "__main__":
    unittest.main()

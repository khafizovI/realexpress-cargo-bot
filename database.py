"""SQLite helper module with minimal CRUD operations."""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

from config import DB_PATH, DEFAULT_ADMIN_USERNAME, ADMIN_ID, ADMIN_IDS


class Database:
    def __init__(self, path: str):
        self.path = path
        # check_same_thread False to allow usage across async handlers
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def execute(self, query: str, params: Tuple = (), fetchone: bool = False, fetchall: bool = False):
        """Execute a query and optionally fetch data."""
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return None

    # --- Initialization ---
    def init_db(self):
        """Create tables and seed defaults."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                language TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_code TEXT UNIQUE,
                flight_number TEXT,
                status TEXT DEFAULT 'Yo''lda',
                estimated_arrival TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE
            )
            """
        )

        track_columns = {
            row["name"]
            for row in self.execute("PRAGMA table_info(tracks)", fetchall=True) or []
        }
        if "estimated_arrival" not in track_columns:
            self.execute("ALTER TABLE tracks ADD COLUMN estimated_arrival TEXT")

        # Seed default settings
        defaults = {
            "about_uz": "Biz Xitoydan O'zbekistonga cargo xizmatlarini ko'rsatamiz. Avto va avia yo'nalishlarda yuklaringizni tez va ishonchli yetkazib beramiz.",
            "about_ru": "Мы занимаемся карго-доставкой грузов из Китая в Узбекистан. Авто и авиа направления, быстрая и надежная доставка.",
            "prices_uz": "Narxlar:\nAvto: 6$ / kg\nAvia: 9$ / kg",
            "prices_ru": "Цены:\nАвто: 6$ / кг\nАвиа: 9$ / кг",
            "address_uz": "Manzilimiz: Toshkent, Chilonzor. Omborga oldindan kelishilgan holda tashrif buyuring.",
            "address_ru": "Наш адрес: Ташкент, Чиланзар. Посещение склада по предварительной договоренности.",
            "map_link": "https://maps.google.com",
            "admin_username": DEFAULT_ADMIN_USERNAME,
            "channel_username": "@yourchannel",
        }
        for key, value in defaults.items():
            self.execute(
                """
                INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)
                """,
                (key, value),
            )

        # Migrate old price_* keys into prices_* if they existed
        old_uz = self.get_setting("price_uz")
        old_ru = self.get_setting("price_ru")
        if old_uz and not self.get_setting("prices_uz"):
            self.set_setting("prices_uz", old_uz)
        if old_ru and not self.get_setting("prices_ru"):
            self.set_setting("prices_ru", old_ru)

        # Seed admins
        seed_admins = ADMIN_IDS or ([ADMIN_ID] if ADMIN_ID else [])
        for admin_id in seed_admins:
            self.execute(
                "INSERT OR IGNORE INTO admins(user_id) VALUES (?)",
                (admin_id,),
            )

    # --- Users ---
    def set_user_language(self, user_id: int, language: str):
        self.execute(
            """
            INSERT INTO users(user_id, language)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
            """,
            (user_id, language),
        )

    def get_user_language(self, user_id: int) -> str:
        row = self.execute(
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,),
            fetchone=True,
        )
        return row["language"] if row and row["language"] else "uz"

    # --- Tracks ---
    def add_track(
        self,
        track_code: str,
        flight_number: str,
        status: str = "Yo'lda",
        estimated_arrival: Optional[str] = None,
    ) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO tracks(track_code, flight_number, status, estimated_arrival)
            VALUES (?, ?, ?, ?)
            """,
            (
                track_code.strip(),
                flight_number.strip(),
                status,
                estimated_arrival.strip() if estimated_arrival else None,
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_track_by_code(self, track_code: str) -> Optional[sqlite3.Row]:
        return self.execute(
            """
            SELECT * FROM tracks WHERE track_code = ?
            """,
            (track_code.strip(),),
            fetchone=True,
        )

    def delete_tracks_by_flight(self, flight_number: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM tracks WHERE flight_number = ?",
            (flight_number.strip(),),
        )
        self.conn.commit()
        return cur.rowcount

    def list_tracks(self, limit: Optional[int] = None) -> List[sqlite3.Row]:
        query = """
        SELECT track_code, flight_number, status, estimated_arrival, created_at
        FROM tracks
        ORDER BY datetime(created_at) DESC
        """
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        else:
            params = ()
        return self.execute(query, params, fetchall=True) or []

    def track_stats(self) -> Dict[str, int]:
        total = self.execute("SELECT COUNT(*) AS c FROM tracks", fetchone=True)["c"]
        active = self.execute(
            """
            SELECT COUNT(*) AS c FROM tracks
            WHERE status IN ("Yo'lda", "В пути", "Yo`lda", "v puti", "V puti")
            """,
            fetchone=True,
        )["c"]
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent = self.execute(
            """
            SELECT COUNT(*) AS c FROM tracks
            WHERE datetime(created_at) >= ?
            """,
            (since_24h.strftime("%Y-%m-%d %H:%M:%S"),),
            fetchone=True,
        )["c"]
        since_7d = datetime.utcnow() - timedelta(days=7)
        recent_7d = self.execute(
            """
            SELECT COUNT(*) AS c FROM tracks
            WHERE datetime(created_at) >= ?
            """,
            (since_7d.strftime("%Y-%m-%d %H:%M:%S"),),
            fetchone=True,
        )["c"]
        return {"total": total, "active": active, "recent": recent, "recent_7d": recent_7d}

    def user_count(self) -> int:
        row = self.execute("SELECT COUNT(*) AS c FROM users", fetchone=True)
        return row["c"] if row else 0

    def admin_count(self) -> int:
        row = self.execute("SELECT COUNT(*) AS c FROM admins", fetchone=True)
        return row["c"] if row else 0

    def list_user_ids(self) -> List[int]:
        rows = self.execute("SELECT DISTINCT user_id FROM users", fetchall=True)
        return [r["user_id"] for r in rows] if rows else []

    # --- Settings ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
            fetchone=True,
        )
        if row:
            return row["value"]
        return default

    def set_setting(self, key: str, value: str):
        self.execute(
            """
            INSERT INTO settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    # --- Admins ---
    def add_admin(self, user_id: int):
        self.execute(
            "INSERT OR IGNORE INTO admins(user_id) VALUES (?)",
            (user_id,),
        )

    def is_admin(self, user_id: int) -> bool:
        row = self.execute(
            "SELECT 1 FROM admins WHERE user_id = ?",
            (user_id,),
            fetchone=True,
        )
        return bool(row)

    def list_admins(self) -> List[int]:
        rows = self.execute("SELECT user_id FROM admins", fetchall=True)
        return [r["user_id"] for r in rows] if rows else []


# Shared singleton instance
db = Database(DB_PATH)


def init_db():
    db.init_db()

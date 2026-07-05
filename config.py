"""
config.py — 安防维保管理系统配置
服务端部署路径：/fs/1000/ftp/技术文档/安防维保管理系统/
"""
import os
import sqlite3
from pathlib import Path


class Config:
    def __init__(self):
        self.app_dir = Path(__file__).parent
        self.data_dir = self.app_dir / "data"
        self.db_path = self.data_dir / "database.db"
        self.images_dir = self.data_dir / "images"
        self.reports_dir = self.data_dir / "reports"

        self._init_directories()
        self._init_database()

    def _init_directories(self):
        """首次运行时创建数据目录"""
        if not self.data_dir.exists():
            print("首次运行，创建数据目录...")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                locations TEXT,
                work_log TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                image_name TEXT,
                thumbnail_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (log_date) REFERENCES daily_logs (date) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()


# 全局配置实例
config = Config()

import sqlite3
from datetime import datetime
from config import config

class Database:
    def __init__(self):
        self.db_path = config.db_path
    
    def save_daily_log(self, date, locations, work_log):
        """保存或更新每日日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_logs (date, locations, work_log, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (date, locations, work_log, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def load_daily_log(self, date):
        """加载指定日期的日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, locations, work_log 
            FROM daily_logs 
            WHERE date = ?
        ''', (date,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'date': result[0],
                'locations': result[1],
                'work_log': result[2]
            }
        return None
    
    def get_monthly_logs(self, year_month):
        """获取指定月份的所有日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, locations, work_log 
            FROM daily_logs 
            WHERE date LIKE ?
            ORDER BY date
        ''', (f"{year_month}%",))
        
        results = cursor.fetchall()
        conn.close()
        
        logs = []
        for result in results:
            logs.append({
                'date': result[0],
                'locations': result[1],
                'work_log': result[2]
            })
        return logs
    
    def save_image_info(self, log_date, image_name, thumbnail_name):
        """保存图片信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO images (log_date, image_name, thumbnail_name)
            VALUES (?, ?, ?)
        ''', (log_date, image_name, thumbnail_name))
        
        conn.commit()
        conn.close()
    
    def get_images_for_date(self, log_date):
        """获取指定日期的图片信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT image_name, thumbnail_name 
            FROM images 
            WHERE log_date = ?
            ORDER BY id
        ''', (log_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'image_name': r[0], 'thumbnail_name': r[1]} for r in results]
    
    def delete_images_for_date(self, log_date):
        """删除指定日期的所有图片记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM images WHERE log_date = ?', (log_date,))
        
        conn.commit()
        conn.close()
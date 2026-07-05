from PIL import Image
import io
import hashlib
import os
from pathlib import Path
from config import config

class ImageProcessor:
    @staticmethod
    def _next_free_index(date):
        """找到最小未使用的 original_索引，避免文件名冲突"""
        try:
            date_dir = config.images_dir / date
            used = set()
            if date_dir.exists():
                for p in date_dir.glob("original_*.jpg"):
                    name = p.name
                    try:
                        idx = int(name.replace("original_", "").replace(".jpg", ""))
                        used.add(idx)
                    except Exception:
                        continue
            for i in range(1000):
                if i not in used:
                    return i
            return max(used) + 1 if used else 0
        except Exception:
            return 0

    @staticmethod
    def process_image(image_data, date, index=None):
        """处理图片：保存原图和生成缩略图；自动选择不冲突的索引"""
        try:
            # 创建日期目录
            date_dir = config.images_dir / date
            date_dir.mkdir(exist_ok=True)
            
            # 打开图片
            image = Image.open(io.BytesIO(image_data))
            
            # 根据 EXIF 自动纠正方向
            try:
                from PIL import ImageOps
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass
            
            # 转换为RGB模式（如果是RGBA或其他模式）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 选择索引（若未指定）
            if index is None:
                index = ImageProcessor._next_free_index(date)
            
            # 压缩：限制最长边为 1600px（大幅减少存储）
            max_dim = 1600
            w, h = image.size
            if w > max_dim or h > max_dim:
                ratio = min(max_dim / w, max_dim / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                image = image.resize((new_w, new_h), Image.LANCZOS)
            
            # 保存原图（quality 80 压缩）
            original_path = date_dir / f"original_{index}.jpg"
            image.save(original_path, "JPEG", quality=80)
            
            # 生成缩略图：保持原始宽高比，最长边 200px
            thumbnail = image.copy()
            thumbnail.thumbnail((200, 200))
            
            thumbnail_path = date_dir / f"thumbnail_{index}.jpg"
            thumbnail.save(thumbnail_path, "JPEG", quality=80)
            
            return {
                'image_name': original_path.name,
                'thumbnail_name': thumbnail_path.name
            }
            
        except Exception as e:
            print(f"图片处理错误: {e}")
            return None

    @staticmethod
    def ensure_thumbnail(date, image_name):
        """保证缩略图存在：根据 original_X.jpg 生成 thumbnail_X.jpg（若缺失则创建）"""
        try:
            date_dir = config.images_dir / date
            if not date_dir.exists():
                return None
            # 推断索引
            if not image_name.startswith("original_") or not image_name.endswith(".jpg"):
                return None
            idx = image_name.replace("original_", "").replace(".jpg", "")
            thumb_name = f"thumbnail_{idx}.jpg"
            thumb_path = date_dir / thumb_name
            if thumb_path.exists():
                return thumb_name
            # 从原图生成
            original_path = date_dir / image_name
            if not original_path.exists():
                return None
            img = Image.open(original_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            thumbnail = img.copy()
            thumbnail.thumbnail((151, 113))
            thumbnail.save(thumb_path, "JPEG", quality=80)
            return thumb_name
        except Exception:
            return None
    
    @staticmethod
    def get_thumbnail_path(date, thumbnail_name):
        """获取缩略图完整路径"""
        return config.images_dir / date / thumbnail_name
    
    @staticmethod
    def get_original_path(date, image_name):
        """获取原图完整路径"""
        return config.images_dir / date / image_name
    
    @staticmethod
    def cleanup_images(date, keep_count=4):
        """清理多余的图片，只保留指定数量"""
        date_dir = config.images_dir / date
        if not date_dir.exists():
            return
        
        images = list(date_dir.glob("original_*.jpg"))
        if len(images) > keep_count:
            for img_path in sorted(images)[keep_count:]:
                img_path.unlink()
                
                # 删除对应的缩略图
                thumb_name = img_path.name.replace("original_", "thumbnail_")
                thumb_path = date_dir / thumb_name
                if thumb_path.exists():
                    thumb_path.unlink()
    
    @staticmethod
    def delete_image_files(date, image_name, thumbnail_name):
        """删除指定的图片文件"""
        date_dir = config.images_dir / date
        
        # 删除原图
        original_path = date_dir / image_name
        if original_path.exists():
            original_path.unlink()
        
        # 删除缩略图
        thumbnail_path = date_dir / thumbnail_name
        if thumbnail_path.exists():
            thumbnail_path.unlink()

    @staticmethod
    def compute_md5_bytes(data: bytes) -> str:
        """计算二进制数据的 MD5"""
        try:
            m = hashlib.md5()
            m.update(data)
            return m.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def compute_md5_file(path: Path) -> str:
        """计算文件的 MD5"""
        try:
            m = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    m.update(chunk)
            return m.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def list_original_paths(date) -> list:
        """列出当日 original_*.jpg 的完整路径（按修改时间升序）"""
        date_dir = config.images_dir / date
        if not date_dir.exists():
            return []
        items = []
        try:
            for f in os.listdir(date_dir):
                if f.startswith("original_") and f.endswith(".jpg"):
                    p = date_dir / f
                    if p.is_file():
                        try:
                            mt = os.path.getmtime(p)
                        except Exception:
                            mt = 0
                        items.append((p, mt))
        except Exception:
            items = []
        items.sort(key=lambda x: x[1])
        return [p for p, _ in items]

    @staticmethod
    def find_duplicate_by_bytes(date, image_data: bytes) -> str:
        """若 image_data 与已有 original_* 内容相同，返回重复的原图文件名；否则返回空字符串"""
        try:
            new_md5 = ImageProcessor.compute_md5_bytes(image_data)
            if not new_md5:
                return ""
            for p in ImageProcessor.list_original_paths(date):
                if ImageProcessor.compute_md5_file(p) == new_md5:
                    return p.name  # original_X.jpg
            return ""
        except Exception:
            return ""

    @staticmethod
    def rebuild_images_from_fs(date) -> list:
        """从文件系统重建图片记录（最多4张，附缩略图名）"""
        originals = ImageProcessor.list_original_paths(date)[:4]
        result = []
        for p in originals:
            name = p.name
            thumb = ImageProcessor.ensure_thumbnail(date, name) or name.replace("original_", "thumbnail_")
            result.append({"image_name": name, "thumbnail_name": thumb})
        return result

    @staticmethod
    def list_images(date):
        """获取指定日期的图片列表（从数据库）"""
        from database import Database
        db = Database()
        from config import config
        images = db.get_images_for_date(date)
        # 如果数据库没有记录，从文件系统重建
        if not images:
            rebuilt = ImageProcessor.rebuild_images_from_fs(date)
            for img in rebuilt:
                db.save_image_info(date, img["image_name"], img["thumbnail_name"])
            images = rebuilt
        # 同步 fs：删除不在磁盘的记录
        valid = []
        for img in images:
            orig_path = config.images_dir / date / img["image_name"]
            if orig_path.exists():
                valid.append(img)
        return valid

    @staticmethod
    def delete_image(date, index):
        """删除指定索引的图片（文件和数据库记录）"""
        from database import Database
        db = Database()
        images = db.get_images_for_date(date)
        target = None
        for img in images:
            name = img["image_name"]
            if name == f"original_{index}.jpg":
                target = img
                break
        if target:
            ImageProcessor.delete_image_files(date, target["image_name"], target["thumbnail_name"])
            # 数据库清理 - 直接删除对应 date 和 image_name 的记录
            import sqlite3
            from config import config
            conn = sqlite3.connect(config.db_path)
            conn.execute("DELETE FROM images WHERE log_date=? AND image_name=?", (date, target["image_name"]))
            conn.commit()
            conn.close()
            return True
        return False
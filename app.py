"""
app.py — 安防维保管理系统 Flask 后端
移动端 Web API 入口
"""
import os
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (
    Flask, request, jsonify, send_file, send_from_directory,
    render_template, abort, make_response
)
from flask_cors import CORS

from config import config
from database import Database
from image_processor import ImageProcessor
from report_generator import ReportGenerator

# ── 应用初始化 ────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

db = Database()
img_proc = ImageProcessor()
rpt_gen = ReportGenerator()

# ── 辅助函数 ──────────────────────────────────────────────

def api_response(data=None, success=True, message="", status=200):
    """统一 JSON 响应格式"""
    return jsonify({
        "success": success,
        "message": message,
        "data": data
    }), status


def validate_date(date_str):
    """验证日期格式 YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def validate_month(month_str):
    """验证月份格式 YYYY-MM"""
    try:
        datetime.strptime(month_str, "%Y-%m")
        return True
    except (ValueError, TypeError):
        return False


# ─═ 页面路由 ═────────────────────────────────────────────

@app.route("/")
def index():
    """移动端主页（强缓存禁用）"""
    today = datetime.now().strftime("%Y-%m-%d")
    resp = make_response(render_template("index.html", today=today))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/static/<path:filename>")
def serve_static(filename):
    resp = make_response(send_from_directory("static", filename))
    if filename.endswith(".js") or filename.endswith(".css"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


# ─═ 日志 API ═────────────────────────────────────────────

@app.route("/api/daily-log", methods=["GET"])
def get_today_log():
    """获取指定日期的日志，默认今天"""
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    if not validate_date(date):
        return api_response(success=False, message="日期格式错误 (YYYY-MM-DD)", status=400)

    log = db.load_daily_log(date)
    if log:
        # 读取时自动合并换行为空格（PDF 空间紧凑需求）
        wl = log["work_log"] or ""
        wl = wl.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
        # 压缩连续空白
        import re as re_mod
        wl = re_mod.sub(r"\s+", " ", wl)
        return api_response(data={
            "date": log["date"],
            "locations": log["locations"],
            "work_log": wl
        })
    else:
        return api_response(data={
            "date": date,
            "locations": "",
            "work_log": ""
        })


@app.route("/api/daily-log", methods=["POST"])
def save_daily_log():
    """保存/更新日志"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return api_response(success=False, message="请求体为空", status=400)

    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    if not validate_date(date):
        return api_response(success=False, message="日期格式错误", status=400)

    locations = data.get("locations", "")
    work_log = data.get("work_log", "")
    # 写入时合并换行为空格（PDF 版面紧凑需求）
    import re as re_mod2
    work_log = work_log.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
    work_log = re_mod2.sub(r"\s+", " ", work_log)

    db.save_daily_log(date, locations, work_log)
    return api_response(message="保存成功")


@app.route("/api/monthly-logs/<ym>", methods=["GET"])
def get_monthly_logs(ym):
    """获取某月的所有日志列表"""
    if not validate_month(ym):
        return api_response(success=False, message="月份格式错误 (YYYY-MM)", status=400)

    logs = db.get_monthly_logs(ym)
    return api_response(data=logs)


@app.route("/api/calendar/<ym>", methods=["GET"])
def get_calendar_data(ym):
    """获取某月有日志的日期列表（用于日历标记）"""
    if not validate_month(ym):
        return api_response(success=False, message="月份格式错误", status=400)

    logs = db.get_monthly_logs(ym)
    dates_with_data = [log["date"] for log in logs]
    return api_response(data=dates_with_data)


# ─═ 图片 API ═────────────────────────────────────────────

@app.route("/api/upload-image/<date>", methods=["POST"])
def upload_image(date):
    """上传图片（支持多文件）"""
    if not validate_date(date):
        return api_response(success=False, message="日期格式错误", status=400)

    if "images" not in request.files:
        return api_response(success=False, message="未选择图片", status=400)

    files = request.files.getlist("images")
    results = []

    for f in files:
        if f.filename == "":
            continue
        try:
            img_bytes = f.read()
            result = img_proc.process_image(img_bytes, date)
            results.append(result)
        except Exception as e:
            results.append({"success": False, "error": str(e)})

    return api_response(data=results, message=f"上传了 {len(results)} 张图片")


@app.route("/api/images/<date>", methods=["GET"])
def get_images(date):
    """获取某日期的图片列表"""
    if not validate_date(date):
        return api_response(success=False, message="日期格式错误", status=400)

    images = img_proc.list_images(date)
    images_info = []
    for idx, img in enumerate(images):
        images_info.append({
            "index": idx,
            "url": f"/api/image-file/{date}/{img.get('image_name', '')}",
            "thumbnail": f"/api/thumbnail-file/{date}/{img.get('thumbnail_name', '')}",
            "name": img.get("image_name", "")
        })

    return api_response(data=images_info)


@app.route("/api/image-file/<date>/<filename>", methods=["GET"])
def serve_image(date, filename):
    """返回原图文件"""
    img_path = config.images_dir / date / filename
    if not img_path.exists():
        abort(404)
    return send_file(str(img_path), mimetype="image/jpeg")


@app.route("/api/thumbnail-file/<date>/<filename>", methods=["GET"])
def serve_thumbnail(date, filename):
    """返回缩略图"""
    thumb_path = config.images_dir / date / filename
    if not thumb_path.exists():
        abort(404)
    return send_file(str(thumb_path), mimetype="image/jpeg")


@app.route("/api/delete-image/<date>/<int:index>", methods=["DELETE"])
def delete_image(date, index):
    """删除某张图片"""
    if not validate_date(date):
        return api_response(success=False, message="日期格式错误", status=400)

    try:
        # 从数据库按序号删除，不依赖文件名
        images = img_proc.list_images(date)
        if index < 0 or index >= len(images):
            return api_response(success=False, message="图片序号无效", status=400)
        target = images[index]
        img_proc.delete_image_files(date, target["image_name"], target["thumbnail_name"])
        import sqlite3
        conn = sqlite3.connect(config.db_path)
        conn.execute("DELETE FROM images WHERE log_date=? AND image_name=?", (date, target["image_name"]))
        conn.commit()
        conn.close()
        return api_response(message="删除成功")
    except Exception as e:
        return api_response(success=False, message=str(e), status=500)


# ─═ 报告 API ═────────────────────────────────────────────

@app.route("/api/generate-report/<ym>", methods=["POST"])
def generate_report(ym):
    """生成月度 PDF 报告"""
    if not validate_month(ym):
        return api_response(success=False, message="月份格式错误", status=400)

    # 检查当月是否有数据
    logs = db.get_monthly_logs(ym)
    if not logs:
        return api_response(success=False, message="该月份没有数据", status=400)

    try:
        success, result = rpt_gen.generate_monthly_report(ym, report_format="pdf")
        if success:
            report_filename = f"维保报告_{ym}.pdf"
            report_path = config.reports_dir / report_filename
            return api_response(data={
                "filename": report_filename,
                "url": f"/api/download-report/{report_filename}",
                "path": str(report_path)
            }, message="报告生成成功")
        else:
            # PDF 失败，尝试文本报告
            success2, result2 = False, "not available"
            if success2:
                report_filename = f"维保报告_{ym}.txt"
                return api_response(data={
                    "filename": report_filename,
                    "url": f"/api/download-report/{report_filename}",
                    "path": result2
                }, message="已生成文本版报告（PDF受限）")
            return api_response(success=False, message=result, status=500)
    except Exception as e:
        return api_response(success=False, message=f"生成报告失败: {str(e)}", status=500)


@app.route("/api/reports", methods=["GET"])
def list_reports():
    """列出已生成的报告"""
    reports = []
    if config.reports_dir.exists():
        for f in sorted(config.reports_dir.iterdir(), reverse=True):
            if f.suffix in (".pdf", ".txt"):
                reports.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "url": f"/api/download-report/{f.name}"
                })
    return api_response(data=reports)


@app.route("/api/download-report/<filename>", methods=["GET"])
def download_report(filename):
    """下载报告文件"""
    file_path = config.reports_dir / filename
    if not file_path.exists():
        abort(404)

    mime = "application/pdf" if filename.endswith(".pdf") else "text/plain"
    return send_file(str(file_path), mimetype=mime, as_attachment=True,
                     download_name=filename)


# ─═ 工具 API ═────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return api_response(data={
        "status": "running",
        "db_path": str(config.db_path),
        "data_dir": str(config.data_dir),
        "images_dir": str(config.images_dir),
        "reports_dir": str(config.reports_dir)
    })


@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/test")
def test_page():
    return send_from_directory("templates", "test.html")


@app.route("/api/today", methods=["GET"])
def today_info():
    """获取今天的日期和当月字符串"""
    now = datetime.now()
    return api_response(data={
        "today": now.strftime("%Y-%m-%d"),
        "month": now.strftime("%Y-%m"),
        "year_month_cn": f"{now.year}年{now.month}月"
    })


# ─═ 启动 ─────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "::")
    debug = os.environ.get("DEBUG", "0") == "1"

    print(f"安防维保管理系统 - 后端启动")
    print(f"数据目录: {config.data_dir}")
    print(f"数据库: {config.db_path}")
    print(f"监听: {host}:{port}")
    print(f"手机访问: http://192.168.5.102:{port}")

    app.run(host=host, port=port, debug=debug, threaded=True)

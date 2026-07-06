# -*- coding: utf-8 -*-
"""
报告生成器 - 支持PDF和Web格式
修复版本 2026-07-04: 基于原始代码 + 7项已知bug修复
"""

from datetime import datetime
from pathlib import Path
from config import config
from database import Database
import calendar
import os
import re

# ReportLab相关导入
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 全角数字转换 ──────────────────────────────────────────────
_FW_DIGITS = str.maketrans('0123456789', '０１２３４５６７８９')

def _fw(s):
    """将字符串中的半角数字和英文字母转换为全角"""
    if not isinstance(s, str):
        s = str(s)
    result = s.translate(_FW_DIGITS)
    # 英文字母转全角（A-Z a-z → Ａ-Ｚ ａ-ｚ）
    result = result.translate(str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ'
    ))
    return result


class ReportGenerator:
    def __init__(self):
        self.db = Database()

    # ═══════════════════════════════════════════════════════════
    #  字体注册（3个变体应对不同风格需求）
    # ═══════════════════════════════════════════════════════════
    _FONT_REGISTERED = False

    @classmethod
    def _register_fonts(cls):
        if cls._FONT_REGISTERED:
            return
        font_path = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DroidSansFallback', font_path))
        cls._FONT_REGISTERED = True

    # ── 全角数字 ──────────────────────────────────────────
    @staticmethod
    def _fw(s):
        return _fw(s)

    def _format_date_chinese_fullwidth(self, date_str):
        """将 YYYY-MM-DD 转为全角年月日 '２０２６年６月１日'"""
        parts = date_str.split('-')
        if len(parts) != 3:
            return date_str
        y, m, d = parts
        return f"{_fw(y)}年{_fw(str(int(m)))}月{_fw(str(int(d)))}日"

    # ═══════════════════════════════════════════════════════════
    #  公共入口
    # ═══════════════════════════════════════════════════════════

    def generate_monthly_report(self, year_month, format_type="pdf", report_format=None):
        # 兼容 report_format 参数（app.py 调用时使用）
        if report_format and not format_type:
            format_type = report_format
        elif report_format:
            format_type = report_format
        """生成月度报告 - 支持PDF和Web格式"""
        try:
            if format_type.lower() == "pdf":
                return self._generate_pdf_report(year_month)
            elif format_type.lower() == "web":
                return self._generate_web_report(year_month)
            else:
                return False, "不支持的报告格式"
        except Exception as e:
            return False, f"生成报告时出错: {str(e)}"

    def _generate_pdf_report(self, year_month):
        """生成PDF报告"""
        try:
            self._register_fonts()
            logs = self.db.get_monthly_logs(year_month)
            if not logs:
                return False, "该月份没有数据"

            report_path = config.reports_dir / f"维保报告_{year_month}.pdf"

            doc = SimpleDocTemplate(
                str(report_path),
                pagesize=A4,
                leftMargin=5*mm,
                rightMargin=5*mm,
                topMargin=5*mm,
                bottomMargin=5*mm
            )
            story = []
            styles = getSampleStyleSheet()

            # 封面页
            self._add_cover_page(story, styles, year_month)

            # 维保情况简述页
            story.append(PageBreak())
            self._add_summary_page(story, styles, logs, year_month)

            # 详细维保记录页
            story.append(PageBreak())
            self._add_detailed_records_pages(story, styles, logs, year_month)

            # 移除末尾空白页：如果最后一个元素是 PageBreak 则删除
            if story and isinstance(story[-1], PageBreak):
                story.pop()

            doc.build(story)

            # 再次检查，如果 PDF 末尾有空白页则截掉
            self._remove_trailing_blank_page(str(report_path))

            return True, str(report_path)

        except ImportError:
            return False, "缺少PDF生成库，请安装reportlab"
        except Exception as e:
            return False, f"PDF生成失败: {str(e)}"

    @staticmethod
    def _remove_trailing_blank_page(pdf_path):
        """移除 PDF 末尾的空白页（使用 pymupdf/fitz）"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            if doc.page_count <= 1:
                doc.close()
                return
            last_page = doc[-1]
            text = last_page.get_text().strip()
            if not text:
                doc.delete_page(doc.page_count - 1)
                doc.save(pdf_path, incremental=False, deflate=True)
            doc.close()
        except ImportError:
            pass
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    #  辅助函数
    # ═══════════════════════════════════════════════════════════

    def _get_last_day_of_month(self, year_month):
        """获取月份的最后一天"""
        y, m = map(int, year_month.split('-'))
        return calendar.monthrange(y, m)[1]

    def _format_date_dot(self, date_str):
        """将 YYYY-MM-DD 转为 YYYY.MM.DD（规格要求的点分隔格式）"""
        return date_str.replace('-', '.')

    def _format_date_chinese(self, date_str):
        """将 YYYY-MM-DD 转为 全角中文 '２０２６年６月１日'"""
        parts = date_str.split('-')
        if len(parts) != 3:
            return date_str
        y, m, d = parts
        return f"{_fw(y)}年{_fw(str(int(m)))}月{_fw(str(int(d)))}日"

    def _format_work_log(self, work_log):
        """
        格式化工作日志：
        - 去除首尾空格
        - 中文标点后多余空格（"、 "→ "、"  ": " → "："）
        - 多个连续空格合并为一个
        - 半角数字转全角
        - 英文句号 . 后无中文标点时转为全角 ．
        """
        if not work_log:
            return "正常巡查"
        text = work_log.strip()
        # 中文标点后多余空格
        text = re.sub(r'([，。、：；])\s+', r'\1', text)
        # 冒号后和括号/数字前的多余空格都去掉
        text = re.sub(r'：\s+', '：', text)
        text = re.sub(r'（\s+', '（', text)
        text = re.sub(r'\s+）', '）', text)
        text = re.sub(r'）\s+\（', '）（', text)
        text = re.sub(r'(?<=[\u4e00-\u9fff])\s+\（', '（', text)
        # 删除所有空格（源数据格式不统一，全部去掉让文字连续）
        text = text.replace(' ', '')
        # 数字后的英文句点先转全角（因为_fw只转数字不转符号）
        text = re.sub(r'(\d)\.', r'\1．', text)
        # 半角数字/字母转全角
        text = _fw(text)
        return text

    # ═══════════════════════════════════════════════════════════
    #  封面页
    # ═══════════════════════════════════════════════════════════

    def _add_cover_page(self, story, styles, year_month):
        """封面页：标题居中28pt + 4行项目信息14pt左对齐，整块垂直居中"""

        top_margin = 20*mm
        story.append(Spacer(1, top_margin))

        title_style = ParagraphStyle(
            'CoverTitle',
            parent=styles['Heading1'],
            fontSize=36,
            alignment=1,
            spaceAfter=40,
            fontName='DroidSansFallback'
        )
        title = Paragraph("监控月度维保记录", title_style)
        story.append(title)

        project_info_style = ParagraphStyle(
            'ProjectInfo',
            parent=styles['Normal'],
            fontSize=14,
            alignment=0,
            spaceAfter=20,
            fontName='DroidSansFallback'
        )

        # 日期部分用小字号的样式
        date_value_style = ParagraphStyle(
            'DateValue',
            parent=styles['Normal'],
            fontSize=12,
            alignment=0,
            fontName='DroidSansFallback'
        )

        # 动态计算维保周期
        y, m = map(int, year_month.split('-'))
        last_day = calendar.monthrange(y, m)[1]

        # 4行项目信息（无日期行）
        # 注意：第4行"维保周期："标签用14pt，具体日期用12pt
        info_rows = [
            [Paragraph("项目名称：岭南学院安防维保项目", project_info_style)],
            [Paragraph("委托单位：广东岭南现代技师学院", project_info_style)],
            [Paragraph("外委单位：广州市高科通信技术股份有限公司", project_info_style)],
            [Paragraph(f"维保周期：{_fw(str(y))}年{_fw(str(m))}月{_fw('1')}日－{_fw(str(y))}年{_fw(str(m))}月{_fw(str(last_day))}日", project_info_style)],
        ]
        # 表格左加20mm空列实现偏移，文字在140mm列内左对齐
        # 第4行日期用并排："维保周期："(14pt) + 日期(12pt)
        cover_rows = [[Paragraph("", project_info_style), Paragraph("项目名称：岭南学院安防维保项目", project_info_style)],
                     [Paragraph("", project_info_style), Paragraph("委托单位：广东岭南现代技师学院", project_info_style)],
                     [Paragraph("", project_info_style), Paragraph("外委单位：广州市高科通信技术股份有限公司", project_info_style)],
                     [Paragraph("", project_info_style), Paragraph(
                         '<font size="14">维保周期：</font><font size="12">' +
                         f'{_fw(str(y))}年{_fw(str(m))}月{_fw("1")}日－{_fw(str(y))}年{_fw(str(m))}月{_fw(str(last_day))}日' +
                         '</font>',
                         project_info_style
                     )],
                     ]
        cover_table = Table(cover_rows, colWidths=[40*mm, 140*mm], hAlign='CENTER')
        cover_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))

        # 标题顶部居中 + 底部留边20mm + 信息表格底部居中
        title_h = title.wrap(190*mm, A4[1])[1]
        table_h = cover_table.wrap(160*mm, A4[1])[1]
        avail = A4[1] - 10*mm - 10*mm
        used = 20*mm + title_h + 40 / 2.83 * mm + table_h + 20*mm
        spacer_h = max(0, avail - used)
        story.append(Spacer(1, spacer_h))
        story.append(cover_table)

    # ═══════════════════════════════════════════════════════════
    #  维保情况简述页
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    #  维保情况简述页
    # ═══════════════════════════════════════════════════════════

    def _add_summary_page(self, story, styles, logs, year_month):
        """维保情况简述页：1×2 单行表格，左列30mm“维保情况简述”，右列170mm填充。
        手动按高度分页：用 Paragraph.wrap 精确测量每条日志高度，填满后自动换页。
        当单条日志高度>剩余空间时，用二分法精确截断文本，前半放本页后半下页。
        每个 Paragraph 被放入固定行高 cell，靠 flowables 列表自然填充。"""

        left_w = 40*mm
        right_w = 160*mm

        left_style = ParagraphStyle(
            'LeftCell',
            parent=styles['Heading2'],
            alignment=1,
            fontSize=14,
            fontName='DroidSansFallback',
            leading=int(14*1.2)
        )
        right_style = ParagraphStyle(
            'RightCell',
            parent=styles['Normal'],
            alignment=0,
            fontSize=11,
            fontName='DroidSansFallback',
            leading=int(11*1.3),
            spaceBefore=0,
            spaceAfter=0
        )

        pad_v = 3*mm
        pad_h = 4*mm
        right_inner_w = right_w - 2*pad_h

        row_h_pt = A4[1] - 10*mm - 12
        inner_h_pt = row_h_pt - 2*pad_v

        # 先把所有日志文本预拼成段落
        raw_texts = []
        for log in logs:
            dd = self._format_date_chinese(log['date'])
            wc = self._format_work_log(log['work_log'] or "正常巡查")
            raw_texts.append(f"〔{dd}〕{wc}")

        # 二分法截断文本
        def split_by_height(text, h_limit):
            if not text:
                return "", ""
            p = Paragraph(text, right_style)
            _, h = p.wrap(right_inner_w, h_limit)
            if h <= h_limit:
                return text, ""
            lo, hi = 1, len(text)
            best = 1
            while lo <= hi:
                mid = (lo + hi) // 2
                p2 = Paragraph(text[:mid], right_style)
                _, h2 = p2.wrap(right_inner_w, h_limit)
                if h2 <= h_limit:
                    best = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            return text[:best], text[best:]

        # 填入 story
        remaining_texts = raw_texts[:]
        first_page = True

        while remaining_texts:
            left_content = Paragraph("维保情况简述", left_style)
            used = 0
            page_content = []

            while remaining_texts:
                avail = inner_h_pt - used
                if avail < 10:
                    break
                text = remaining_texts[0]
                first, rest = split_by_height(text, avail)
                if not first:
                    break
                page_content.append(Paragraph(first, right_style))
                if rest:
                    remaining_texts[0] = rest
                    break
                else:
                    remaining_texts.pop(0)
                    # 重新 wrap 获取实际高度
                    w, h = Paragraph(first, right_style).wrap(right_inner_w, inner_h_pt - used)
                    used += h

            if not page_content:
                break

            if first_page:
                first_page = False
            else:
                story.append(PageBreak())

            data = [[left_content, page_content]]
            table = Table(data, colWidths=[left_w, right_w], rowHeights=[row_h_pt])
            table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (0,0), 'CENTER'),
                ('VALIGN', (0,0), (0,0), 'MIDDLE'),
                ('ALIGN', (1,0), (1,0), 'LEFT'),
                ('VALIGN', (1,0), (1,0), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), pad_h),
                ('RIGHTPADDING', (0,0), (-1,-1), pad_h),
                ('TOPPADDING', (0,0), (-1,-1), pad_v),
                ('BOTTOMPADDING', (0,0), (-1,-1), pad_v),
                ('FONTSIZE', (0,0), (0,0), 14),
                ('FONTSIZE', (1,0), (1,0), 11),
            ]))
            story.append(table)

    #  详细维保记录页
    # ═══════════════════════════════════════════════════════════

    def _add_detailed_records_pages(self, story, styles, logs, year_month):
        """详细维保记录页：连续追加，每页尽量填满，让 SimpleDocTemplate 自动分页"""

        col_widths = [44.7*mm, 44.7*mm, 49.5*mm, 61.1*mm]

        for log in logs:
            data = []

            # 第1行：标题行（四列合并）
            header_style = ParagraphStyle(
                'dHdr', parent=styles['Heading3'],
                alignment=1, fontSize=14, fontName='DroidSansFallback'
            )
            data.append([Paragraph("监控排查现场", header_style), "", "", ""])

            # 第2行：时间 + 地点
            date_display = self._format_date_chinese(log['date'])
            locations = _fw(log['locations'] or "未指定")

            cell_style_c = ParagraphStyle(
                'dCellC', parent=styles['Normal'],
                alignment=1, fontSize=11, fontName='DroidSansFallback'
            )
            cell_style_l = ParagraphStyle(
                'dCellL', parent=styles['Normal'],
                alignment=0, fontSize=11, fontName='DroidSansFallback'
            )
            data.append([
                Paragraph(_fw("时间"), cell_style_c),
                Paragraph(date_display, cell_style_c),
                Paragraph(_fw("地点"), cell_style_c),
                Paragraph(locations, cell_style_l),
            ])

            # 第3行：巡查情况 — 11pt→10pt→9pt→8pt自动缩放，顶部左对齐
            work_log = log['work_log'] or "正常巡查"
            formatted_log = self._format_work_log(work_log)

            # 自动缩放：在行高内从小到大试字号
            detail_width = col_widths[1] + col_widths[2] + col_widths[3]
            final_font_size = 8
            for fs in [11, 10, 9, 8, 7, 6]:
                tmp_style = ParagraphStyle(
                    'dRightTmp', parent=styles['Normal'],
                    alignment=0, fontSize=fs, fontName='DroidSansFallback',
                    leading=int(fs * 1.3), wordWrap='CJK'
                )
                w_test, h_test = Paragraph(formatted_log, tmp_style).wrap(detail_width - 8, 200*mm)
                if h_test <= 28*mm:
                    final_font_size = fs
                    break

            left_style = ParagraphStyle(
                'dLeft', parent=styles['Normal'],
                alignment=1, fontSize=11, fontName='DroidSansFallback'
            )
            right_style = ParagraphStyle(
                'dRight', parent=styles['Normal'],
                alignment=0, fontSize=final_font_size, fontName='DroidSansFallback',
                leading=int(final_font_size * 1.3), wordWrap='CJK'
            )
            data.append([
                Paragraph(_fw("巡查情况"), left_style),
                Paragraph(formatted_log, right_style), "", ""
            ])

            # 第4行：现场照片 — 宽度40mm，等比缩放，行高35mm
            images = self.db.get_images_for_date(log['date'])
            images = self._sync_images_fs_with_db(log['date'], images)

            photo_cells = []
            if images:
                date_dir = log['date']
                ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
                img_w = 34*mm
                max_h = 40*mm
                valid_paths = []
                for img_info in images[:4]:
                    thumb_name = img_info.get('thumbnail_name')
                    name = img_info.get('image_name', '')
                    ext = os.path.splitext(thumb_name or name)[1].lower()
                    if ext not in ALLOWED_EXT:
                        continue
                    p = os.path.join(str(config.images_dir), date_dir, thumb_name or name)
                    if os.path.exists(p):
                        valid_paths.append(p)

                for ph_i, p in enumerate(valid_paths):
                    try:
                        ir = ImageReader(p)
                        iw, ih = ir.getSize()
                        if iw > 0:
                            actual_h = min(ih * (img_w / iw), max_h)
                        else:
                            actual_h = max_h
                        photo_cells.append(Image(p, width=img_w, height=actual_h))
                    except Exception:
                        continue
                    if ph_i < len(valid_paths) - 1:
                        photo_cells.append(Spacer(3*mm, 0))

            photo_table = Table([photo_cells], hAlign='LEFT') if photo_cells else Spacer(1, 0)
            if isinstance(photo_table, Table):
                photo_table.setStyle(TableStyle([
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))

            data.append([
                Paragraph(_fw("现场照片"), left_style),
                photo_table, "", ""
            ])

            # 按实际渲染高度计算行高
            w_r, h_r = Paragraph(formatted_log, right_style).wrap(detail_width - 8, 200*mm)
            actual_heights = [10*mm, 12*mm, h_r + 4*mm, 41*mm]
            table = Table(data, colWidths=col_widths, rowHeights=actual_heights)
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('SPAN', (0,0), (3,0)),
                ('SPAN', (1,2), (3,2)),
                ('SPAN', (1,3), (3,3)),
                ('FONTNAME', (0,0), (-1,-1), 'DroidSansFallback'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
                ('VALIGN', (1,2), (3,2), 'TOP'),
                ('ALIGN', (0,0), (3,0), 'CENTER'),
                ('ALIGN', (0,1), (3,2), 'CENTER'),
                ('ALIGN', (0,3), (-1,-1), 'CENTER'),
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ]))
            story.append(table)
    # ═══════════════════════════════════════════════════════════
    #  照片辅助（从原始代码保留）
    # ═══════════════════════════════════════════════════════════

    def _add_photo_section(self, story, images, year_month, date):
        """添加照片展示部分 - 保留兼容（未被调用但保留以备将来）"""
        import os

        date_dir = date
        image_folder = config.images_dir / date_dir

        photo_paths = []
        for img_info in images:
            full_path = image_folder / img_info['image_name']
            if os.path.exists(full_path):
                photo_paths.append(str(full_path))

        if photo_paths:
            if len(photo_paths) <= 4:
                photo_data = [[]]
                for i, photo_path in enumerate(photo_paths):
                    if i < 4:
                        try:
                            ir = ImageReader(photo_path)
                            iw, ih = ir.getSize()
                            target_w = 4*cm
                            target_h = ih * (target_w / float(iw)) if iw else None
                            img = Image(photo_path, width=target_w, height=target_h)
                            photo_data[0].append(img)
                        except:
                            photo_data[0].append("图片加载失败")
                col_widths = [4*cm] * len(photo_data[0])
                photo_table = Table(photo_data, colWidths=col_widths)
            else:
                photo_data = []
                for i in range(0, min(4, len(photo_paths)), 2):
                    row = []
                    for j in range(2):
                        if i + j < min(4, len(photo_paths)):
                            try:
                                ir = ImageReader(photo_paths[i + j])
                                iw, ih = ir.getSize()
                                target_w = 4*cm
                                target_h = ih * (target_w / float(iw)) if iw else None
                                img = Image(photo_paths[i + j], width=target_w, height=target_h)
                                row.append(img)
                            except:
                                row.append("图片加载失败")
                        else:
                            row.append("")
                    photo_data.append(row)
                col_widths = [4*cm, 4*cm]
                photo_table = Table(photo_data, colWidths=col_widths)

            photo_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0, colors.white),
            ]))
            story.append(photo_table)

    def _sync_images_fs_with_db(self, date, images):
        """仅以 original_*.jpg 为准进行对账与限额；不把 thumbnail_* 计入候选或误删。返回最多4张原图及其缩略图映射。"""
        import os, time
        image_folder = config.images_dir / date
        if not os.path.isdir(image_folder):
            return []

        ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

        try:
            folder_originals = []
            for f in os.listdir(image_folder):
                fp = image_folder / f
                if os.path.isfile(fp):
                    ext = os.path.splitext(f)[1].lower()
                    if not (ext in ALLOWED_EXT):
                        continue
                    if not f.startswith("original_"):
                        continue
                    try:
                        mtime = os.path.getmtime(fp)
                    except Exception:
                        mtime = 0
                    folder_originals.append((f, mtime))
        except Exception:
            folder_originals = []

        folder_originals.sort(key=lambda x: x[1])
        folder_original_names_sorted = [name for name, _ in folder_originals]

        db_images = [img for img in (images or []) if img.get("image_name")]
        db_map = {img["image_name"]: img.get("thumbnail_name") for img in db_images}

        def _try_delete_db_record(date, name, img_obj=None):
            for method in ("delete_image_record", "delete_image", "remove_image", "remove_image_by_name", "delete_image_by_name", "delete_image_by_id"):
                if hasattr(self.db, method):
                    try:
                        if method == "delete_image_by_id" and img_obj and "id" in img_obj:
                            getattr(self.db, method)(img_obj["id"])
                        else:
                            getattr(self.db, method)(date, name)
                        return True
                    except Exception:
                        pass
            return False

        for img in list(db_images):
            name = img["image_name"]
            if name not in folder_original_names_sorted:
                _try_delete_db_record(date, name, img_obj=img)
                try:
                    db_images.remove(img)
                except ValueError:
                    pass

        keep_originals = folder_original_names_sorted[:4]

        for extra_name in folder_original_names_sorted[4:]:
            fp = image_folder / extra_name
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass
            thumb_guess = extra_name.replace("original_", "thumbnail_")
            thumb_fp = image_folder / thumb_guess
            if os.path.exists(thumb_fp):
                try:
                    os.remove(thumb_fp)
                except Exception:
                    pass
            _try_delete_db_record(date, extra_name)

        def _try_add_db_record(date, name, thumbnail_name=None):
            for method in ("add_image_record", "add_image", "insert_image", "create_image"):
                if hasattr(self.db, method):
                    try:
                        if method == "add_image_record":
                            getattr(self.db, method)(date, name, thumbnail_name or name.replace("original_", "thumbnail_"))
                        else:
                            getattr(self.db, method)(date, name)
                        return True
                    except Exception:
                        pass
            return False

        db_set = set([img["image_name"] for img in db_images])
        for name in keep_originals:
            if name not in db_set:
                guess_thumb = name.replace("original_", "thumbnail_")
                thumb_fp = image_folder / guess_thumb
                thumb_name = guess_thumb if os.path.exists(thumb_fp) else (db_map.get(name) or guess_thumb)
                _try_add_db_record(date, name, thumbnail_name=thumb_name)

        result = []
        for name in keep_originals:
            guess_thumb = name.replace("original_", "thumbnail_")
            thumb_name = db_map.get(name) or (guess_thumb if os.path.exists(image_folder / guess_thumb) else guess_thumb)
            result.append({"image_name": name, "thumbnail_name": thumb_name})
        return result

    # ═══════════════════════════════════════════════════════════
    #  Web/HTML 报告（保留兼容）
    # ═══════════════════════════════════════════════════════════

    def _generate_web_report(self, year_month):
        logs = self.db.get_monthly_logs(year_month)
        if not logs:
            return False, "该月份没有数据"
        report_path = config.reports_dir / f"维保报告_{year_month}.html"
        html_content = self._create_html_content(year_month, logs)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return True, str(report_path)

    def _create_html_content(self, year_month, logs):
        generate_date = datetime.now().strftime("%Y年%m月%d日")
        last_day = self._get_last_day_of_month(year_month)

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>监控月度维保记录</title>
    <style>
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; margin: 40px; color: #333; }}
        .cover {{ height: 100vh; position: relative; display: flex; align-items: center; justify-content: center; text-align: center; }}
        .cover-info {{ position: absolute; left: 50%; bottom: 40px; transform: translateX(-50%); text-align: left; }}
        .cover h1 {{ font-size: 28px; margin-bottom: 50px; font-weight: bold; }}
        .info-table {{ width: 80%; margin: 0 auto 50px auto; border-collapse: collapse; }}
        .info-table td {{ padding: 12px; border: none; font-size: 16px; }}
        .info-table td:first-child {{ text-align: right; font-weight: bold; width: 25%; }}
        .summary, .details {{ margin: 40px 0; }}
        .summary h2, .details h2 {{ font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
        .log-item {{ margin: 15px 0; padding: 10px; border-left: 3px solid #007acc; background-color: #f9f9f9; }}
        .record-block {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .record-item {{ margin: 10px 0; }}
        .separator {{ height: 1px; background-color: #ccc; margin: 20px 0; }}
        .page-break {{ page-break-before: always; }}
    </style>
</head>
<body>
    <div class="cover">
        <h1>监控月度维保记录</h1>
        <div class="cover-info">
            <table class="info-table">
                <tr><td>项目名称：</td><td>岭南学院安防维保项目</td></tr>
                <tr><td>委托单位：</td><td>广东岭南现代技师学院</td></tr>
                <tr><td>外委单位：</td><td>广州市高科通信技术股份有限公司</td></tr>
                <tr><td>维保周期：</td><td>{year_month}-01 - {last_day}</td></tr>
                <tr><td>生成日期：</td><td>{generate_date}</td></tr>
            </table>
        </div>
    </div>
    <div class="summary page-break">
        <h2>维保情况简述</h2>
        <hr>
"""
        for log in logs:
            date_display = self._format_date_dot(log['date'])
            work_content = self._format_work_log(log['work_log'] or "正常巡查")
            html += f'<div class="log-item">【{date_display}】{work_content}</div>\n'

        html += """
    </div>
    <div class="details page-break">
        <h2>详细维保记录</h2>
"""
        for i, log in enumerate(logs):
            if i > 0 and i % 3 == 0:
                html += '<div class="page-break"><h2>详细维保记录</h2>\n'

            html += '<div class="record-block">\n'
            html += f'    <div class="record-item"><strong>监控排查现场</strong></div>\n'
            html += f'    <div class="record-item"><strong>时间：</strong>{self._format_date_chinese(log["date"])}</div>\n'
            html += f'    <div class="record-item"><strong>地点：</strong>{log["locations"] or "未指定"}</div>\n'

            work_log = self._format_work_log(log['work_log'] or "正常巡查")
            html += f'    <div class="record-item"><strong>巡查情况：</strong><br>{work_log}</div>\n'

            images = self.db.get_images_for_date(log['date'])
            photo_text = f"现场照片：已上传 {len(images)} 张照片" if images else "现场照片：无照片"
            html += f'    <div class="record-item"><strong>{photo_text}</strong></div>\n'
            html += '</div>\n<div class="separator"></div>\n'

            if (i + 1) % 3 == 0 and (i + 1) < len(logs):
                html += '</div>\n'

        html += """
    </div>
</body>
</html>"""
        return html

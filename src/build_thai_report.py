"""Build Thai-language Markdown and DOCX reports from executed project results."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml.ns import qn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
RESULTS_FILE = PROJECT_ROOT / "outputs" / "tables" / "results.json"
PICKUPS_FILE = PROJECT_ROOT / "outputs" / "processed" / "pickups_classified.parquet"
THAI_FONT = "Sathu"

MONTH_NAMES = {
    4: "เมษายน",
    5: "พฤษภาคม",
    6: "มิถุนายน",
    7: "กรกฎาคม",
    8: "สิงหาคม",
    9: "กันยายน",
}
WEEKDAYS = [
    "วันจันทร์",
    "วันอังคาร",
    "วันพุธ",
    "วันพฤหัสบดี",
    "วันศุกร์",
    "วันเสาร์",
    "วันอาทิตย์",
]
BASE_LABELS = {
    "B02512": "Unter",
    "B02598": "Hinter",
    "B02617": "Weiter",
    "B02682": "Schmecken",
    "B02764": "Danach-NY",
    "B02765": "Grun",
    "B02835": "Dreist",
    "B02836": "Drinnen",
}


def percent(value: int | float, denominator: int | float) -> str:
    """Return a percentage with two decimals and an explicit denominator nearby."""
    return f"{100 * value / denominator:.2f}%"


def p_value_label(value: float) -> str:
    """Format very small p-values as a threshold rather than a rounded zero."""
    return "< 0.001" if value < 0.001 else f"{value:.4g}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Convert rows of values into a Markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def build_report_lines(results: dict, pickups: pd.DataFrame) -> list[str]:
    """Compose the Thai report from current result tables and classified rows."""
    total = results["n"]
    nyc_total = results["nyc_n"]
    outside_total = results["outside_n"]
    monthly_totals = {int(m): int(n) for m, n in results["monthly_counts"].items()}
    hourly_totals = {int(h): int(n) for h, n in results["hour_counts"].items()}

    daily_by_month = (
        pickups.groupby(["month", "date"]).size().groupby("month").mean().round()
    )
    daily_by_weekday = (
        pickups.groupby(["day_of_week", "date"])
        .size()
        .groupby("day_of_week")
        .mean()
        .round()
    )
    borough_by_hour = pd.crosstab(
        pickups.loc[pickups["inside_nyc"], "borough"],
        pickups.loc[pickups["inside_nyc"], "hour"],
    )
    base_by_hour = pd.crosstab(pickups["hour"], pickups["Base"])
    base_by_weekday = pd.crosstab(pickups["day_of_week"], pickups["Base"])

    lines: list[str] = []

    def add(*paragraphs: str) -> None:
        lines.extend(paragraphs)
        lines.append("")

    def add_heading(level: int, text: str) -> None:
        add("#" * level + " " + text)

    def add_figure(filename: str, caption: str) -> None:
        add(f"![{caption}](../outputs/figures/{filename})")

    add_heading(1, "รายงานการวิเคราะห์รูปแบบการรับผู้โดยสาร Uber ในนิวยอร์กซิตี")
    add("ช่วงข้อมูล: เมษายน–กันยายน ค.ศ. 2014")
    add("รายวิชา: Data Science ชั้นปีที่ 2 ภาคการศึกษาที่ 1")
    add("ผู้จัดทำ: ______________________________  |  ______________________________")

    add_heading(2, "บทคัดย่อ")
    add(
        f"รายงานนี้วิเคราะห์ข้อมูลจุดรับ Uber จำนวน {total:,} รายการ "
        "จากเดือนเมษายนถึงกันยายน ค.ศ. 2014 โดยตรวจสอบคุณภาพข้อมูล สร้างตัวแปรเวลา "
        "และจำแนกพื้นที่แบบลำดับชั้น เริ่มจากตรวจขอบเขต NYC จากนั้นกำหนด borough "
        "ให้เฉพาะจุดที่อยู่ใน NYC ส่วนจุดนอกเมืองจำแนกระดับรัฐแยกต่างหาก "
        f"พบจุดใน NYC {nyc_total:,} รายการ ({percent(nyc_total, total)} ของข้อมูลทั้งหมด) "
        f"และนอก NYC {outside_total:,} รายการ ({percent(outside_total, total)}). "
        f"Manhattan มีจำนวนสูงสุด {results['boroughs'][0]['pickups']:,} จุด "
        f"หรือ {results['boroughs'][0]['pct_nyc']:.2f}% ของจุดใน NYC "
        f"ชั่วโมงที่มีจำนวนสูงสุดคือ 17:00 ({hourly_totals[17]:,} จุด) "
        "ผลทดสอบทางสถิติพบความสัมพันธ์ในหลายตาราง แต่ขนาดอิทธิพลมีตั้งแต่เล็กถึงปานกลาง "
        "และควรตีความโดยคำนึงถึงการกระจุกตัวของข้อมูลตามเวลาและพื้นที่ "
        "ข้อมูลนี้นับจุดรับที่บันทึกไว้ ไม่ได้วัดจำนวนคนขับ รถที่พร้อมให้บริการ "
        "หรือคำขอเดินทางที่ไม่ได้รับบริการ"
    )

    add_heading(2, "บทที่ 1 บทนำ")
    add_heading(3, "1.1 ที่มาและความสำคัญ")
    add(
        "ข้อมูลพิกัดและเวลาของจุดรับช่วยให้เห็นรูปแบบการใช้บริการในแต่ละพื้นที่และช่วงเวลา "
        "แต่จำนวนจุดรับไม่เท่ากับจำนวนคำขอทั้งหมด จำนวนรถที่พร้อมให้บริการ "
        "หรือจำนวนผู้โดยสารที่เดินทางสำเร็จ"
    )
    add_heading(3, "1.2 ปัญหาและคำถามวิจัย")
    add(
        "ข้อมูลครอบคลุมพื้นที่รอบมหานครนิวยอร์ก การวิเคราะห์ borough "
        "จึงต้องตัดสินก่อนว่าจุดอยู่ใน NYC หรือไม่ เพื่อไม่ให้จุดนอกเมืองถูกจัดเป็น borough "
        "คำถามหลักคือจุดรับหนาแน่นที่สุดเมื่อใดและที่ใด borough ใดมีจำนวนสูงสุด "
        "และรูปแบบเปลี่ยนไปอย่างไรตามชั่วโมง วัน เดือน และ base"
    )
    add_heading(3, "1.3 วัตถุประสงค์")
    add(
        "- ตรวจสอบจำนวนแถว คุณภาพข้อมูล และความสอดคล้องระหว่างเดือนในชื่อไฟล์กับ timestamp",
        "- ศึกษารูปแบบตามเดือน ชั่วโมง และวันในสัปดาห์",
        "- จำแนกข้อมูลจากขอบเขต NYC ไปยัง borough และรัฐตามลำดับ",
        "- เปรียบเทียบรูปแบบของ borough และ Uber base พร้อมรายงานผลทดสอบทางสถิติ",
    )
    add_heading(3, "1.4 ขอบเขต")
    add(
        "ใช้ไฟล์รายเดือน 6 ไฟล์ ตั้งแต่เมษายนถึงกันยายน ค.ศ. 2014 "
        "ขอบเขต borough มาจาก NYC Open Data รุ่นปี 2026 ส่วนขอบเขตรัฐเป็น Census ปี 2014 "
        "การใช้ขอบเขตคนละปีเป็นข้อจำกัดที่ต้องพิจารณาเมื่ออ่านผล"
    )

    add_heading(2, "บทที่ 2 ข้อมูลและคุณภาพข้อมูล")
    add_heading(3, "2.1 แหล่งข้อมูลและตัวแปร")
    add(
        "แต่ละแถวประกอบด้วย Date/Time, Lat, Lon และ Base โดย FiveThirtyEight "
        "ระบุว่าได้รับข้อมูลจาก NYC Taxi & Limousine Commission (TLC) "
        "ผ่านคำขอข้อมูลสาธารณะ FOIL [1] ไฟล์มีข้อมูลเวลาจุดรับ พิกัด และรหัส base "
        "แต่ไม่มีปลายทาง ค่าโดยสาร หรือข้อมูลผู้ขับขี่"
    )
    quality_rows = [
        [
            row["month"],
            f"{row['rows']:,}",
            f"{row['duplicate_rows']:,}",
            str(row["missing_cells"]),
            str(row["invalid_rows"]),
            str(row["wrong_month_rows"]),
        ]
        for row in results["quality"]
    ]
    lines.extend(
        markdown_table(
            [
                "เดือน",
                "แถว",
                "แถวซ้ำ",
                "ค่าว่าง",
                "แถวผิดรูปแบบ",
                "เดือน timestamp ไม่ตรงไฟล์",
            ],
            quality_rows,
        )
    )
    lines.append("")
    add_heading(3, "2.2 ผลตรวจและการจัดการแถวซ้ำ")
    add(
        "ข้อมูลทั้ง 6 ไฟล์รวม 4,534,327 แถว และจำนวนรายเดือนตรงตามค่าที่คาดไว้ "
        "ไม่พบค่าว่างหรือค่าผิดรูปแบบใน timestamp พิกัด และรหัส base "
        "เดือนของ timestamp ตรงกับเดือนของไฟล์ทุกแถว "
        "พบแถวซ้ำแบบตรงกันในทุกเดือน แต่เก็บไว้ทั้งหมดเพราะไม่มีรหัสเหตุการณ์ "
        "ที่จะชี้ได้ว่าแถวซ้ำเกิดจากการรับผู้โดยสารหลายครั้งในจุดและเวลาเดียวกัน "
        "หรือเกิดจากการคัดลอกข้อมูลซ้ำ ไฟล์ดิบไม่ได้ถูกแก้ไข"
    )
    add_heading(3, "2.3 ข้อจำกัดของข้อมูล")
    add(
        "ข้อมูลไม่สามารถใช้สรุปจำนวนคนขับ ขนาดกองรถ ส่วนแบ่งตลาด "
        "จำนวนคำขอที่ไม่ได้รับบริการ หรือสาเหตุของความต้องการเดินทางได้"
    )

    add_heading(2, "บทที่ 3 วิธีดำเนินการ")
    add_heading(3, "3.1 ขั้นตอนเตรียมข้อมูล")
    add(
        "1. อ่าน CSV แยกตามเดือน ตรวจจำนวนแถว ค่าว่าง รูปแบบพิกัด base code "
        "และความสอดคล้องของเดือนใน timestamp\n"
        "2. นับแถวซ้ำแบบตรงกันแต่ไม่ลบ และคงไฟล์ดิบไว้\n"
        "3. แยก year, month, day, hour, date และ day_of_week "
        "(วันจันทร์มีค่า 0)\n"
        "4. บันทึกข้อมูลที่ผ่านการจำแนกเป็น Parquet "
        "และสร้างตารางสรุปกับภาพจากข้อมูลชุดเดียวกัน"
    )
    add_heading(3, "3.2 วิธีจำแนกภูมิศาสตร์แบบลำดับชั้น")
    add(
        "พิกัดและ polygon ถูกใช้ในระบบ EPSG:4326 โดยใช้ contains_xy "
        "ตรวจจุดภายใน polygon และ intersects_xy ตรวจกรณีที่จุดอยู่บนเส้นขอบ [4] "
        "ขั้นตอนจำแนกคือ:\n"
        "1. ตรวจทุกจุดกับ polygon รวมของ borough ทั้งห้า เพื่อกำหนดว่าอยู่ใน NYC หรืออยู่นอก NYC\n"
        "2. ส่งเฉพาะจุดใน NYC ไปจำแนกเป็น Manhattan, Brooklyn, Queens, Bronx หรือ Staten Island\n"
        "3. แยกจุดนอก NYC ไปตรวจ polygon รัฐ โดยเก็บ New York, New Jersey, Connecticut, "
        "รัฐอื่น และ unmatched\n"
        "4. ตรวจจุด NYC กับ polygon รัฐอีกครั้งเพื่อการกระทบยอดเท่านั้น "
        "หากไม่ตรง polygon รัฐ จุดนั้นยังคงเป็นจุด NYC และยังอยู่ในการวิเคราะห์ borough"
    )
    add(
        "NYC Open Data ระบุว่าชุด borough boundaries ไม่รวมพื้นที่น้ำ [2] "
        "ส่วน polygon รัฐมาจาก Census ปี 2014 [3] "
        "จึงรักษาความแตกต่างของขอบเขตทั้งสองไว้ ไม่บังคับให้จำนวนตรงกัน"
    )
    add_heading(3, "3.3 การวิเคราะห์เวลา พื้นที่ และ base")
    add(
        "คำนวณยอดรายเดือน ชั่วโมง และวันในสัปดาห์ พร้อมใช้ค่าเฉลี่ยต่อวันเมื่อจำนวนวันไม่เท่ากัน "
        "แสดงรูปแบบร่วมของชั่วโมงกับวัน/เดือนด้วย heatmap ใช้ hexbin แบบสเกลลอการิทึม "
        "แสดงความหนาแน่นของจุด และใช้สัดส่วนภายใน borough/base "
        "เพื่อเปรียบเทียบรูปทรงของรูปแบบเวลา"
    )
    add_heading(3, "3.4 วิธีทดสอบทางสถิติ")
    add(
        "ใช้ Pearson chi-square กับตารางความถี่ และรายงาน Cramér’s V หรือ Cohen’s w "
        "เป็นขนาดอิทธิพล กำหนด alpha เท่ากับ 0.05 "
        "การทดสอบวันในสัปดาห์ปรับจำนวนคาดหมายตามจำนวนวันจริงในแต่ละ weekday "
        "(มีวันอังคาร 27 วัน และวันอื่นอย่างละ 26 วัน)"
    )

    add_heading(2, "บทที่ 4 ผลการสำรวจข้อมูล")
    add_heading(3, "4.1 ภาพรวม")
    add(
        f"มีจุดใน NYC {nyc_total:,} รายการ ({percent(nyc_total, total)} "
        f"ของข้อมูลทั้งหมด) และนอก NYC {outside_total:,} รายการ "
        f"({percent(outside_total, total)})"
    )
    add_figure("usa_pickup_hexbin.png", "จุดรับทั้งหมดในพื้นที่ที่ข้อมูลครอบคลุม")
    add_figure(
        "nyc_boundary_classification.png",
        "สีส้มคือจุดใน NYC และสีเขียวคือจุดนอก NYC",
    )
    add_figure(
        "outside_nyc_states.png",
        "จำนวนจุดนอก NYC จำแนกตามรัฐและ unmatched",
    )
    add_heading(3, "4.2 รูปแบบตามเวลา")
    add(
        f"กันยายนมีจำนวนรวมสูงสุด {monthly_totals[9]:,} รายการ และเมษายนต่ำสุด "
        f"{monthly_totals[4]:,} รายการ เมื่อเฉลี่ยต่อวัน กันยายนยังสูงสุดที่ "
        f"{int(daily_by_month[9]):,} จุดต่อวัน และเมษายนต่ำสุดที่ "
        f"{int(daily_by_month[4]):,} จุดต่อวัน ชั่วโมง 17:00 มี "
        f"{hourly_totals[17]:,} รายการ สูงสุด ส่วน 02:00 มี {hourly_totals[2]:,} "
        f"รายการ ต่ำสุด ค่าเฉลี่ยรายวันสูงสุดใน{WEEKDAYS[int(daily_by_weekday.idxmax())]} "
        f"({int(daily_by_weekday.max()):,}) และต่ำสุดใน"
        f"{WEEKDAYS[int(daily_by_weekday.idxmin())]} "
        f"({int(daily_by_weekday.min()):,})"
    )
    add_figure("monthly_demand.png", "ค่าเฉลี่ยจำนวนจุดรับต่อวันแยกตามเดือน")
    add_figure("hourly_demand.png", "จำนวนจุดรับตามชั่วโมง")
    add_figure("weekday_demand.png", "ค่าเฉลี่ยจำนวนจุดรับต่อวันแยกตาม weekday")
    add_figure("day_hour_heatmap.png", "จำนวนจุดรับตามวันและชั่วโมง")
    add_figure("month_hour_heatmap.png", "จำนวนจุดรับตามเดือนและชั่วโมง")
    add_figure(
        "weekday_weekend.png",
        "ค่าเฉลี่ยจำนวนจุดรับรายชั่วโมงต่อวัน: วันทำงานและวันหยุด",
    )
    add(
        "ข้อมูลแสดงว่าจำนวนจุดรับเพิ่มในช่วงบ่ายและสูงสุดช่วง 17:00 "
        "แต่ไม่ได้ระบุว่าสาเหตุเกิดจากตารางงาน กิจกรรม สภาพจราจร "
        "หรือจำนวนรถที่พร้อมให้บริการ"
    )

    add_heading(3, "4.3 การเปรียบเทียบ borough")
    borough_rows = [
        [
            row["borough"],
            f"{row['pickups']:,}",
            f"{row['pct_nyc']:.2f}%",
            f"{row['pct_all']:.2f}%",
        ]
        for row in results["boroughs"]
    ]
    lines.extend(
        markdown_table(
            ["borough", "จำนวนจุดรับ", "% ของจุดรับใน NYC", "% ของข้อมูลทั้งหมด"],
            borough_rows,
        )
    )
    lines.append("")
    borough_peak_details = " ".join(
        f"{borough} สูงสุดที่ {int(hour):02d}:00;"
        for borough, hour in borough_by_hour.idxmax(axis=1).items()
    )
    add(
        "Manhattan มี 3,443,457 จุด หรือ 78.05% ของจุดใน NYC "
        "และ 75.94% ของข้อมูลทั้งหมด Brooklyn มี 593,595 จุด และ Queens 342,224 จุด "
        f"ชั่วโมงสูงสุดราย borough คือ {borough_peak_details} "
        "จำนวนดิบใช้ดูปริมาณรวม ส่วนกราฟ normalized ใช้เปรียบเทียบรูปแบบเวลา"
    )
    add_figure("nyc_borough_choropleth.png", "แผนที่จำนวนจุดรับราย borough")
    add_figure("borough_pickup_counts.png", "กราฟเปรียบเทียบจำนวนจุดรับห้า borough")
    add_figure(
        "borough_hourly_profiles.png",
        "สัดส่วนจุดรับรายชั่วโมงภายในแต่ละ borough",
    )

    add_heading(3, "4.4 การเปรียบเทียบ Uber base")
    base_rows = []
    for base_code, base_name in BASE_LABELS.items():
        count = int(results["bases"].get(base_code, 0))
        if count:
            peak_hour = int(base_by_hour[base_code].idxmax())
            peak_day = WEEKDAYS[int(base_by_weekday[base_code].idxmax())]
        else:
            peak_hour = "—"
            peak_day = "ไม่มีรายการ"
        base_rows.append(
            [
                base_code,
                base_name,
                f"{count:,}",
                percent(count, total),
                str(peak_hour),
                peak_day,
            ]
        )
    lines.extend(
        markdown_table(
            [
                "รหัส",
                "ชื่อ base",
                "จำนวน",
                "% ของข้อมูลทั้งหมด",
                "ชั่วโมงสูงสุด",
                "weekday สูงสุด",
            ],
            base_rows,
        )
    )
    lines.append("")
    add(
        "B02617 มีจำนวนสูงสุด 1,458,853 รายการ ตามด้วย B02598 จำนวน 1,393,113 "
        "และ B02682 จำนวน 1,212,789 รหัส B02765, B02835 และ B02836 ไม่มีรายการ "
        "จำนวน record ของ base ไม่ใช่จำนวนคนขับ ขนาดกองรถ หรือส่วนแบ่งตลาด"
    )
    add_figure("base_hourly_profiles.png", "สัดส่วนรูปแบบรายชั่วโมงของแต่ละ base")

    add_heading(2, "บทที่ 5 ผลการทดสอบทางสถิติ")
    test_rows = []
    for test in results["tests"]:
        if "cramers_v" in test:
            effect = f"Cramér’s V = {test['cramers_v']:.3f}"
        else:
            effect = f"Cohen’s w = {test['effect_size_cohens_w']:.3f}"
        test_rows.append(
            [
                test["question"],
                f"χ² = {test['statistic']:,.2f}",
                str(test["df"]),
                p_value_label(test["p_value"]),
                effect,
            ]
        )
    lines.extend(
        markdown_table(
            ["คำถามที่ทดสอบ", "ค่าสถิติ", "df", "p-value", "ขนาดอิทธิพล"],
            test_rows,
        )
    )
    lines.append("")
    add(
        "สมมติฐานศูนย์ของการทดสอบความเป็นอิสระระบุว่าตัวแปรจัดหมวดหมู่ไม่มีความสัมพันธ์กัน "
        "ส่วนการทดสอบ weekday เปรียบเทียบจำนวนจริงกับค่าคาดหมายที่ปรับตามจำนวนวัน "
        "ผลทั้งห้าการทดสอบมี p-value ต่ำกว่า 0.001 "
        "แต่ค่า V อยู่ในช่วง 0.023–0.106 และ w เท่ากับ 0.142 "
        "แสดงว่าความแตกต่างบางรายการมีขนาดเล็ก แม้จะมีนัยสำคัญทางสถิติ"
    )
    add(
        "จุดรับจำนวนมากไม่ได้เป็นตัวอย่างสุ่มอิสระอย่างสมบูรณ์ เพราะอาจกระจุกตามวัน "
        "ชั่วโมง และพื้นที่ และมีแถวซ้ำอยู่ด้วย จึงรายงานขนาดอิทธิพลควบคู่กับ p-value "
        "และไม่สรุปเหตุและผล"
    )

    add_heading(2, "บทที่ 6 การกระทบยอดภูมิศาสตร์และอภิปราย")
    state_rows = [
        [
            state,
            f"{int(count):,}",
            percent(int(count), total),
        ]
        for state, count in results["states"].items()
    ]
    state_rows.append(["รวม", f"{total:,}", "100.00%"])
    lines.extend(
        markdown_table(
            ["ผลจำแนกระดับรัฐ", "จำนวน", "% ของข้อมูลทั้งหมด"],
            state_rows,
        )
    )
    lines.append("")
    add(
        "ยอดรัฐรวมได้ 4,534,327 รายการ: New York 4,441,067; New Jersey 92,649; "
        "Connecticut 546; Massachusetts 1; unmatched 64; และรัฐอื่น 0 "
        "กลุ่ม unmatched 64 จุดประกอบด้วย 49 จุดนอก NYC ที่ไม่ตรง polygon รัฐ "
        "และ 15 จุดใน NYC ที่ไม่ตรง polygon รัฐ จุด 15 รายการยังอยู่ในการวิเคราะห์ borough "
        "ส่วนจุด Massachusetts นับเพียงครั้งเดียว"
    )
    add(
        "ผลที่ใช้วางแผนต่อได้คือการตรวจพื้นที่ Manhattan และช่วงปลายบ่ายเป็นพิเศษ "
        "แต่ข้อมูลนี้ไม่มีจำนวนรถที่พร้อมให้บริการ เวลารอ หรือคำขอที่ไม่ได้รับบริการ "
        "จึงยังใช้กำหนดจำนวนรถที่ควรจัดสรรไม่ได้"
    )

    add_heading(2, "บทที่ 7 สรุป ข้อจำกัด และข้อเสนอแนะ")
    add(
        "ข้อมูลส่วนใหญ่อยู่ใน NYC โดย Manhattan มีจำนวนจุดรับสูงสุด "
        "รูปแบบตามเวลาสูงสุดที่ 17:00 และค่าเฉลี่ยต่อวันเพิ่มจากเมษายนถึงกันยายน "
        "การจำแนกแบบลำดับชั้นทำให้จุดนอกเมืองไม่ถูกนำไปนับใน borough"
    )
    add(
        "- ก่อนวิเคราะห์ borough ให้ตรวจขอบเขต NYC ก่อนทุกครั้ง และเก็บ unmatched ไว้ตรวจสอบ",
        "- เชื่อมข้อมูลจำนวนรถพร้อมให้บริการ เวลารอ การจราจร และคำขอที่ไม่ได้รับบริการก่อนตัดสินใจด้านปฏิบัติการ",
        "- ทำซ้ำกับข้อมูลหลายปีและ boundary รุ่นที่ตรงกับช่วงข้อมูล",
        "- ตรวจที่มาของแถวซ้ำก่อนลบ เพราะไฟล์นี้แยกการซ้ำจากระบบกับเหตุการณ์จริงไม่ได้",
    )
    add(
        "ข้อจำกัดหลักคือข้อมูลมีเพียงหกเดือนของปี 2014; boundary borough เป็นรุ่น 2026 "
        "และไม่รวมพื้นที่น้ำ; boundary รัฐเป็นรุ่น 2014; ไม่มีข้อมูลปลายทางหรือจำนวนรถพร้อมให้บริการ; "
        "และเก็บแถวซ้ำไว้ ผลจึงไม่ควรถูกขยายไปยังปีอื่นโดยไม่มีข้อมูลเพิ่มเติม"
    )

    add_heading(2, "แหล่งข้อมูลและเอกสารอ้างอิง")
    add(
        "[1] FiveThirtyEight. Uber TLC FOIL Response. ที่มา คำอธิบายข้อมูลรายเดือน "
        "ตัวแปร และรหัส base: https://github.com/fivethirtyeight/uber-tlc-foil-response",
        "[2] NYC Department of City Planning. Borough Boundaries, NYC Open Data "
        "(อัปเดต 26 พฤษภาคม 2026; ไม่รวมพื้นที่น้ำ): "
        "https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne",
        "[3] U.S. Census Bureau. 2014 Cartographic Boundary Shapefiles: States, 1:500,000: "
        "https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.2014.html",
        "[4] Shapely documentation: contains_xy และ intersects_xy สำหรับตรวจความสัมพันธ์ระหว่างพิกัดกับ geometry: "
        "https://shapely.readthedocs.io/en/2.2.0/reference/shapely.contains_xy.html",
        "[5] Pearson, K. (1900). On the criterion that a given system of deviations from the probable "
        "in the case of a correlated system of variables is such that it can be reasonably supposed "
        "to have arisen from random sampling. Philosophical Magazine, 50(302), 157–175.",
        "[6] Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). "
        "Lawrence Erlbaum Associates.",
    )
    add_heading(2, "ภาคผนวก: วิธีทำซ้ำ")
    add(
        "ข้อมูลดิบอยู่ในโฟลเดอร์ data; ตารางและกราฟอยู่ใน outputs; "
        "โค้ดวิเคราะห์อยู่ใน src/analysis.py "
        "ติดตั้งแพ็กเกจจาก requirements.txt แล้วรัน python src/analysis.py "
        "จากนั้นรัน python src/build_thai_report.py เพื่อสร้างรายงาน Markdown และ DOCX "
        "และใช้ LibreOffice แปลง DOCX เป็น PDF"
    )
    return lines


def markdown_to_docx(markdown_lines: list[str], output_path: Path) -> None:
    """Render the report's headings, paragraphs, tables, bullets, and figures in Word."""
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    def set_run_font(run, size: int | None = None) -> None:
        run.font.name = THAI_FONT
        if size is not None:
            run.font.size = Pt(size)
        run_properties = run._element.get_or_add_rPr()
        fonts = run_properties.rFonts
        for script in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn(f"w:{script}"), THAI_FONT)
        language = run_properties.find(qn("w:lang"))
        if language is None:
            from docx.oxml import OxmlElement

            language = OxmlElement("w:lang")
            run_properties.append(language)
        language.set(qn("w:val"), "th-TH")
        language.set(qn("w:eastAsia"), "th-TH")
        language.set(qn("w:bidi"), "th-TH")

    for style_name, size in [
        ("Normal", 11),
        ("Title", 22),
        ("Heading 1", 16),
        ("Heading 2", 13),
    ]:
        style = document.styles[style_name]
        style.font.name = THAI_FONT
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(31, 78, 121)
        for script in ("ascii", "hAnsi", "eastAsia", "cs"):
            style._element.rPr.rFonts.set(qn(f"w:{script}"), THAI_FONT)

    index = 0
    while index < len(markdown_lines):
        line = markdown_lines[index]

        if not line.strip():
            index += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while index < len(markdown_lines) and markdown_lines[index].startswith("|"):
                cells = [
                    cell.strip() for cell in markdown_lines[index].strip("|").split("|")
                ]
                if not all(set(cell) <= set("-: ") for cell in cells):
                    table_lines.append(cells)
                index += 1
            if table_lines:
                word_table = document.add_table(
                    rows=1,
                    cols=len(table_lines[0]),
                )
                word_table.style = "Light Shading Accent 1"
                for cell, value in zip(word_table.rows[0].cells, table_lines[0]):
                    cell.text = value
                for row in table_lines[1:]:
                    cells = word_table.add_row().cells
                    for cell, value in zip(cells, row):
                        cell.text = value
                for row in word_table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                set_run_font(run, 8)
            continue

        if line.startswith("# "):
            title = document.add_paragraph(style="Title")
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.add_run(line[2:])
        elif line.startswith("## "):
            document.add_heading(line[3:], level=1)
        elif line.startswith("### "):
            document.add_heading(line[4:], level=2)
        elif line.startswith("- "):
            document.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("!["):
            match = re.search(r"\]\((.*?)\)", line)
            if match:
                image_path = (PROJECT_ROOT / "reports" / match.group(1)).resolve()
                if image_path.exists():
                    image_paragraph = document.add_paragraph()
                    image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    image_paragraph.add_run().add_picture(
                        str(image_path),
                        width=Inches(6.2),
                    )
            caption = line[2 : line.find("]")]
            caption_paragraph = document.add_paragraph(caption)
            caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            document.add_paragraph(line)
        for paragraph in document.paragraphs[-1:]:
            for run in paragraph.runs:
                set_run_font(run)
        index += 1

    document.save(output_path)


def main() -> None:
    """Build the Thai Markdown and DOCX reports from the executed analysis."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    pickups = pd.read_parquet(PICKUPS_FILE)
    report_lines = build_report_lines(results, pickups)

    markdown_path = REPORT_DIR / "final_report_th.md"
    docx_path = REPORT_DIR / "final_report_th.docx"
    markdown_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    markdown_to_docx(report_lines, docx_path)
    print(f"สร้างรายงานแล้ว: {markdown_path.name}, {docx_path.name}")


if __name__ == "__main__":
    main()

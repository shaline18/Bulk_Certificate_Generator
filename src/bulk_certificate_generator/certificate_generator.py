from pathlib import Path
import re
import math

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth


# Output folder
OUTPUT_DIR = Path("generated_certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

# Reusable company logo and signature images
TEMPLATE_DIR = Path(__file__).parent / "templates"
LOGO_PATH = TEMPLATE_DIR / "company_logo.png"
SIGNATURE_PATH = TEMPLATE_DIR / "signature.png"


# Certificate color palette
CREAM = colors.HexColor("#FFFCF5")
NAVY = colors.HexColor("#102E55")
GOLD = colors.HexColor("#D2A037")
DARK_GOLD = colors.HexColor("#A8791E")
PALE_GOLD = colors.HexColor("#F5EACF")
TEXT = colors.HexColor("#303030")
WHITE = colors.white


def create_filename(recipient_name):
    safe_name = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "",
        str(recipient_name)
    )
    safe_name = "_".join(safe_name.strip().split())

    return f"{safe_name or 'Recipient'}.pdf"


def get_unique_filepath(recipient_name):
    filename = create_filename(recipient_name)
    file_path = OUTPUT_DIR / filename
    counter = 2

    while file_path.exists():
        file_path = OUTPUT_DIR / (
            f"{Path(filename).stem}_{counter}.pdf"
        )
        counter += 1

    return file_path


def fitted_text(
    pdf, text, x, y, font, size, max_width, color
):
    """Draw centered text and shrink it if it is too long."""

    text = str(text)

    while size > 8 and stringWidth(text, font, size) > max_width:
        size -= 0.5

    pdf.setFillColor(color)
    pdf.setFont(font, size)
    pdf.drawCentredString(x, y, text)


def draw_star(pdf, cx, cy, outer_radius, inner_radius, color):
    points = []

    for i in range(10):
        angle = math.radians(90 + i * 36)
        radius = (
            outer_radius if i % 2 == 0 else inner_radius
        )

        points.append((
            cx + radius * math.cos(angle),
            cy + radius * math.sin(angle)
        ))

    path = pdf.beginPath()
    path.moveTo(*points[0])

    for point in points[1:]:
        path.lineTo(*point)

    path.close()
    pdf.setFillColor(color)
    pdf.drawPath(path, fill=1, stroke=0)


def draw_corner_flourish(pdf, x, y, sx, sy):
    """Decorative gold corner curls."""

    pdf.saveState()
    pdf.translate(x, y)
    pdf.scale(sx, sy)

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.4)

    pdf.line(0, 0, 24, 0)
    pdf.line(0, 0, 0, 24)

    path = pdf.beginPath()
    path.moveTo(4, 4)
    path.curveTo(8, 20, 22, 20, 20, 8)
    path.curveTo(19, 2, 12, 4, 13, 9)
    pdf.drawPath(path, fill=0, stroke=1)

    path = pdf.beginPath()
    path.moveTo(5, 5)
    path.curveTo(17, 9, 18, 19, 26, 20)
    pdf.drawPath(path, fill=0, stroke=1)

    draw_star(pdf, 13, 13, 3.5, 1.5, GOLD)

    pdf.restoreState()


def draw_border(pdf, w, h):
    # Cream background
    pdf.setFillColor(CREAM)
    pdf.rect(0, 0, w, h, fill=1, stroke=0)

    # Double navy and gold frame
    borders = [
        (8, 2.8, NAVY),
        (16, 1.8, GOLD),
        (23, 0.8, DARK_GOLD),
        (29, 0.6, GOLD),
    ]

    for inset, thickness, color in borders:
        pdf.setStrokeColor(color)
        pdf.setLineWidth(thickness)
        pdf.rect(
            inset, inset,
            w - 2 * inset,
            h - 2 * inset,
            fill=0, stroke=1
        )

    # Four decorative corners
    draw_corner_flourish(pdf, 29, 29, 1, 1)
    draw_corner_flourish(pdf, w - 29, 29, -1, 1)
    draw_corner_flourish(pdf, 29, h - 29, 1, -1)
    draw_corner_flourish(pdf, w - 29, h - 29, -1, -1)

    # Navy and gold ribbon in upper-left corner
    path = pdf.beginPath()
    path.moveTo(10, h - 10)
    path.lineTo(112, h - 10)
    path.curveTo(82, h - 18, 40, h - 42, 10, h - 82)
    path.close()

    pdf.setFillColor(NAVY)
    pdf.drawPath(path, fill=1, stroke=0)

    path = pdf.beginPath()
    path.moveTo(10, h - 18)
    path.curveTo(45, h - 23, 77, h - 35, 135, h - 16)
    path.curveTo(83, h - 38, 48, h - 58, 10, h - 106)
    path.close()

    pdf.setFillColor(GOLD)
    pdf.drawPath(path, fill=1, stroke=0)

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.2)
    pdf.line(10, h - 82, 135, h - 16)

    # Matching ribbon in lower-right corner
    path = pdf.beginPath()
    path.moveTo(w - 10, 10)
    path.lineTo(w - 112, 10)
    path.curveTo(
        w - 82, 18,
        w - 40, 42,
        w - 10, 82
    )
    path.close()

    pdf.setFillColor(NAVY)
    pdf.drawPath(path, fill=1, stroke=0)

    path = pdf.beginPath()
    path.moveTo(w - 10, 18)
    path.curveTo(
        w - 45, 23,
        w - 77, 35,
        w - 135, 16
    )
    path.curveTo(
        w - 83, 38,
        w - 48, 58,
        w - 10, 106
    )
    path.close()

    pdf.setFillColor(GOLD)
    pdf.drawPath(path, fill=1, stroke=0)


def draw_top_emblem(pdf, cx, cy):
    """Gold star enclosed by a laurel-inspired medallion."""

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.4)
    pdf.circle(cx, cy, 25, fill=0, stroke=1)
    pdf.circle(cx, cy, 21, fill=0, stroke=1)

    draw_star(pdf, cx, cy, 14, 6, GOLD)

    # Small laurel branches
    for direction in (-1, 1):
        path = pdf.beginPath()
        path.moveTo(cx + direction * 14, cy - 18)
        path.curveTo(
            cx + direction * 31, cy - 6,
            cx + direction * 28, cy + 15,
            cx + direction * 17, cy + 20
        )

        pdf.setStrokeColor(DARK_GOLD)
        pdf.setLineWidth(1.2)
        pdf.drawPath(path, fill=0, stroke=1)

        for i in range(5):
            lx = cx + direction * (17 + i * 1.3)
            ly = cy - 12 + i * 6

            pdf.setFillColor(GOLD)
            pdf.ellipse(
                min(lx, lx + direction * 6),
                ly,
                max(lx, lx + direction * 6),
                ly + 3,
                fill=1,
                stroke=0
            )


def draw_laurel_wreath(pdf, cx, cy):
    """Large, pale-gold laurel wreath behind the central text."""

    pdf.saveState()

    pdf.setStrokeColor(PALE_GOLD)
    pdf.setFillColor(PALE_GOLD)
    pdf.setLineWidth(1.0)

    for direction in (-1, 1):
        path = pdf.beginPath()
        path.moveTo(cx + direction * 10, cy - 64)
        path.curveTo(
            cx + direction * 105, cy - 47,
            cx + direction * 105, cy + 50,
            cx + direction * 13, cy + 76
        )
        pdf.drawPath(path, fill=0, stroke=1)

        # Individual leaves along each branch
        for i in range(8):
            t = i / 7

            lx = cx + direction * (
                20 + 58 * math.sin(t * math.pi / 2)
            )
            ly = cy - 48 + i * 16

            pdf.saveState()
            pdf.translate(lx, ly)
            pdf.rotate(direction * (35 + i * 3))
            pdf.ellipse(
                -13, -4, 13, 4,
                fill=1, stroke=0
            )
            pdf.restoreState()

    pdf.restoreState()


def draw_award_medal(pdf, cx, cy):
    """Gold award seal with navy ribbon tails."""

    # Navy ribbons
    pdf.setFillColor(NAVY)

    for direction in (-1, 1):
        path = pdf.beginPath()
        path.moveTo(cx + direction * 5, cy - 9)
        path.lineTo(cx + direction * 17, cy - 39)
        path.lineTo(cx + direction * 12, cy - 30)
        path.lineTo(cx + direction * 3, cy - 35)
        path.close()

        pdf.drawPath(path, fill=1, stroke=0)

    # Gold seal
    pdf.setFillColor(GOLD)
    pdf.setStrokeColor(DARK_GOLD)
    pdf.setLineWidth(1.2)
    pdf.circle(cx, cy, 22, fill=1, stroke=1)

    pdf.setStrokeColor(CREAM)
    pdf.setLineWidth(1)
    pdf.circle(cx, cy, 17, fill=0, stroke=1)
    pdf.circle(cx, cy, 13, fill=0, stroke=1)

    draw_star(pdf, cx, cy, 12, 5, CREAM)


def draw_bottom_flourish(pdf, cx, cy):
    """Small gold curls on either side of the medal."""

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.2)

    for direction in (-1, 1):
        path = pdf.beginPath()
        path.moveTo(cx + direction * 28, cy)
        path.curveTo(
            cx + direction * 48, cy + 16,
            cx + direction * 65, cy + 16,
            cx + direction * 76, cy + 4
        )
        path.curveTo(
            cx + direction * 82, cy - 2,
            cx + direction * 69, cy - 6,
            cx + direction * 68, cy + 1
        )
        pdf.drawPath(path, fill=0, stroke=1)


def generate_certificate(
    recipient_name,
    event_name,
    event_date,
    issuer,
    certificate_id
):
    file_path = get_unique_filepath(recipient_name)

    pdf = canvas.Canvas(
        str(file_path),
        pagesize=landscape(A4)
    )

    w, h = landscape(A4)
    cx = w / 2

    # 1. Background and decorative border
    draw_border(pdf, w, h)

    # 2. Pale laurel wreath behind the central content
    draw_laurel_wreath(pdf, cx, 205)

    # 3. Top award emblem
    draw_top_emblem(pdf, cx, h - 47)

    # 4. Main title
    fitted_text(
        pdf, "CERTIFICATE",
        cx, h - 112,
        "Times-Bold", 43, w - 130, NAVY
    )

    # Title dividers
    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.2)
    pdf.line(cx - 205, h - 124, cx - 105, h - 124)
    pdf.line(cx + 105, h - 124, cx + 205, h - 124)

    fitted_text(
        pdf, "OF ACHIEVEMENT",
        cx, h - 145,
        "Times-Bold", 22, w - 140, DARK_GOLD
    )

    # 5. Presentation sentence
    fitted_text(
        pdf,
        "This certificate is proudly presented to",
        cx, h - 184,
        "Times-Italic", 16, w - 150, NAVY
    )

    # 6. Recipient name
    fitted_text(
        pdf, recipient_name,
        cx, h - 230,
        "Times-BoldItalic", 34, w - 150, NAVY
    )

    # Gold divider with star
    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.2)
    pdf.line(cx - 165, h - 242, cx - 10, h - 242)
    pdf.line(cx + 10, h - 242, cx + 165, h - 242)

    draw_star(pdf, cx, h - 242, 6, 2.5, GOLD)

    # 7. Appreciation sentences
    fitted_text(
        pdf,
        "In recognition of your dedication, enthusiasm, and active participation.",
        cx, h - 276,
        "Times-Italic", 13, w - 180, NAVY
    )

    fitted_text(
        pdf,
        "Your commitment to learning and growth is truly appreciated.",
        cx, h - 297,
        "Times-Italic", 13, w - 180, NAVY
    )

    fitted_text(
        pdf,
        "May this achievement inspire you to continue pursuing excellence",
        cx, h - 318,
        "Times-Italic", 13, w - 180, NAVY
    )

    fitted_text(
        pdf,
        "and reaching new heights.",
        cx, h - 337,
        "Times-Italic", 13, w - 180, NAVY
    )

    # 8. Event details
    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(0.8)
    pdf.line(cx - 58, h - 351, cx + 58, h - 351)

    fitted_text(
        pdf,
        f"For participating in {event_name}",
        cx, h - 374,
        "Times-Bold", 16, w - 150, NAVY
    )

    # Date appears only once
    fitted_text(
        pdf,
        f"Date: {event_date}",
        cx, h - 399,
        "Times-Italic", 14, w - 150, NAVY
    )

    # 9. Bottom decoration and medal
    draw_bottom_flourish(pdf, cx, 70)
    draw_award_medal(pdf, cx, 76)

    
    # 10. Footer: logo + issuer on the left, medal in the centre,
    #     signature on the right. Both side blocks share one baseline
    #     and are mirrored around the page centre.
    line_y = 72                 # gold line both blocks sit on
    block_offset = 215          # distance of each block's centre from the page centre
    line_half = 62              # half-length of the gold line
    left_x = cx - block_offset
    right_x = cx + block_offset

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1)

    # Left block: company logo above a line, "Issued by <issuer>" below it
    if LOGO_PATH.exists():
        pdf.drawImage(
            ImageReader(str(LOGO_PATH)),
            left_x - 32, line_y + 4,
            width=64,
            height=62,
            preserveAspectRatio=True,
            anchor="s",
            mask="auto",
        )

    pdf.line(left_x - line_half, line_y, left_x + line_half, line_y)

    pdf.setFillColor(NAVY)
    pdf.setFont("Times-Italic", 10)
    pdf.drawCentredString(left_x, line_y - 13, "Issued by")

    fitted_text(
        pdf, issuer,
        left_x, line_y - 27,
        "Times-Bold", 12, line_half * 2 + 40, NAVY
    )

    # Right block: signature resting on its own line, with a caption below
    if SIGNATURE_PATH.exists():
        pdf.drawImage(
            ImageReader(str(SIGNATURE_PATH)),
            right_x - 55, line_y + 2,
            width=110,
            height=50,
            preserveAspectRatio=True,
            anchor="s",
            mask="auto",
        )

    pdf.line(right_x - line_half, line_y, right_x + line_half, line_y)

    pdf.setFillColor(NAVY)
    pdf.setFont("Times-Italic", 10)
    pdf.drawCentredString(right_x, line_y - 13, "Authorized Signature")

    pdf.save()

    return str(file_path)
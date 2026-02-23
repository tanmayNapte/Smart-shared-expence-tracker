# services/report_service.py

from io import BytesIO
from datetime import datetime
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from zoneinfo import ZoneInfo
from models import db, GroupMember, User, Settlement


# ------------------------------------------------
# Settlement Simplification Algorithm
# ------------------------------------------------
def simplify_settlements(balances):
    creditors = []
    debtors = []

    for user_id, balance in balances.items():
        if balance > 0:
            creditors.append([user_id, balance])
        elif balance < 0:
            debtors.append([user_id, -balance])

    settlements = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]

        amount = min(debt, credit)

        settlements.append((debtor_id, creditor_id, amount))

        debt -= amount
        credit -= amount

        debtors[i][1] = debt
        creditors[j][1] = credit

        if debt == 0:
            i += 1
        if credit == 0:
            j += 1

    return settlements


# ------------------------------------------------
# PDF Generator
# ------------------------------------------------
def generate_group_pdf(group):
    buffer = BytesIO()

    font_path = os.path.join("static", "fonts", "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesizes.A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()

    # Section title style (minimal, no visual change to structure)
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="DejaVuSans",
        fontSize=12,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8
    )

    # --------------------------
    # HEADER STRIP (UNCHANGED)
    # --------------------------
    header_data = [[f"{group.name.upper()} - REPORT"]]

    header_table = Table(header_data, colWidths=[6.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # Metadata
    meta_style = ParagraphStyle(
        "MetaStyle",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=10,
        textColor=colors.grey
    )

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata"))

    elements.append(
        Paragraph(
            f"Generated on {ist_time.strftime('%d %b %Y, %H:%M IST')}",
            meta_style
        )
)
    elements.append(Spacer(1, 20))

    # --------------------------
    # FETCH MEMBERS
    # --------------------------
    members = (
        db.session.query(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group.id)
        .all()
    )

    # --------------------------
    # CALCULATE BALANCES (FINANCIALLY CORRECT)
    # --------------------------
    total_spent = 0
    balances = {member.id: 0 for member in members}

    # Step 1: From expenses
    for expense in group.expenses:
        if not expense.is_active:
            continue

        total_spent += expense.amount

        balances[expense.paid_by] += expense.amount

        for split in expense.splits:
            balances[split.user_id] -= split.amount

    # Step 2: Subtract recorded settlements
    settlements_done = Settlement.query.filter_by(group_id=group.id).all()

    for s in settlements_done:
        # payer reduces debt
        balances[s.payer_id] += s.amount

        # receiver reduces credit
        balances[s.receiver_id] -= s.amount

    # Step 3: Recalculate outstanding AFTER settlements
    total_outstanding = sum(abs(v) for v in balances.values()) / 2

    # --------------------------
    # FINANCIAL SNAPSHOT
    # --------------------------
    elements.append(Paragraph("FINANCIAL SNAPSHOT", section_style))

    snapshot_data = [
        ["Total Spent", f"₹ {total_spent:.2f}"],
        ["Net Outstanding", f"₹ {total_outstanding:.2f}"],
        ["Total Members", str(len(members))]
    ]

    snapshot_table = Table(snapshot_data, colWidths=[3.5*inch, 2.5*inch])
    snapshot_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    elements.append(snapshot_table)
    elements.append(Spacer(1, 30))

    # --------------------------
    # MEMBER BALANCE
    # --------------------------
    elements.append(Paragraph("MEMBER BALANCE", section_style))

    balance_data = [["Member", "Net Balance"]]

    for member in members:
        balance = balances.get(member.id, 0)
        balance_data.append([
            member.name,
            f"₹ {balance:.2f}"
        ])

    balance_table = Table(balance_data, colWidths=[3.5*inch, 2.5*inch])
    balance_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ]))

    elements.append(balance_table)
    elements.append(Spacer(1, 30))

    # --------------------------
    # REMAINING SETTLEMENTS
    # --------------------------
    elements.append(Paragraph("REMAINING SETTLEMENTS", section_style))

    settlements = simplify_settlements(balances)

    if not settlements:
        elements.append(Spacer(1, 10))
        elements.append(
            Paragraph(
                "All dues are settled. No pending settlements.",
                styles["Normal"]
            )
        )
    else:
        settlement_data = [["From", "To", "Amount"]]

        for debtor_id, creditor_id, amount in settlements:
            debtor = next(m for m in members if m.id == debtor_id)
            creditor = next(m for m in members if m.id == creditor_id)

            settlement_data.append([
                debtor.name,
                creditor.name,
                f"₹ {amount:.2f}"
            ])

        settlement_table = Table(
            settlement_data,
            colWidths=[2.5*inch, 2.5*inch, 1.5*inch]
        )

        settlement_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ]))

        elements.append(settlement_table)

    # --------------------------
    # SETTLEMENT HISTORY (NEW SECTION)
    # --------------------------
    elements.append(Paragraph("SETTLEMENT HISTORY", section_style))

    settlements_done = Settlement.query.filter_by(group_id=group.id).all()

    history_data = [["Paid By", "Received By", "Amount", "Date"]]

    for s in settlements_done:
        payer = next(m for m in members if m.id == s.payer_id)
        receiver = next(m for m in members if m.id == s.receiver_id)

        history_data.append([
            payer.name,
            receiver.name,
            f"₹ {s.amount:.2f}",
            s.created_at.strftime("%d %b %Y")
        ])

    history_table = Table(history_data, colWidths=[2*inch, 2*inch, 1.2*inch, 1.3*inch])
    history_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))

    elements.append(history_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
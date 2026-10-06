import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.services.insight_service import generate_insights
from app.models.report import Report
from app.extensions import db

def generate_pdf_report(user, start_date, end_date, include_text, entries):
    """
    Generates an in-memory PDF report using ReportLab.
    Saves metadata to the Report table.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    h1_style = styles['Heading1']
    h2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    custom_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    story = []
    
    # 1. HEADER
    story.append(Paragraph("MINDTRACK", title_style))
    story.append(Paragraph("Personal Reflection Report", h2_style))
    story.append(Spacer(1, 12))
    
    sd_str = start_date.strftime('%d %b %Y') if start_date else "Beginning"
    ed_str = end_date.strftime('%d %b %Y') if end_date else "Present"
    story.append(Paragraph(f"<b>Period:</b> {sd_str} - {ed_str}", normal_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%d %b %Y')}", normal_style))
    story.append(Spacer(1, 24))
    
    if not entries:
        story.append(Paragraph("No journal entries found for this period.", normal_style))
        story.append(Spacer(1, 12))
    else:
        # 2. OVERVIEW STATS
        story.append(Paragraph("OVERVIEW", h1_style))
        
        total_entries = len(entries)
        avg_mood = sum(e.mood_score for e in entries) / total_entries
        reflections_completed = sum(1 for e in entries if e.reflections)
        
        stat_data = [
            ["Journal entries", str(total_entries)],
            ["Average recorded mood", f"{avg_mood:.1f} / 5"],
            ["Reflections completed", str(reflections_completed)]
        ]
        
        t = Table(stat_data, colWidths=[200, 100])
        t.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 24))
        
        # 3. THEMES
        theme_counts = {}
        for entry in entries:
            for dt in entry.detected_themes:
                theme_counts[dt.theme_name] = theme_counts.get(dt.theme_name, 0) + 1
                
        if theme_counts:
            story.append(Paragraph("THEMES", h1_style))
            theme_data = []
            for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True):
                theme_data.append([theme, f"{count} entries"])
                
            t_themes = Table(theme_data, colWidths=[200, 100])
            t_themes.setStyle(TableStyle([
                ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t_themes)
            story.append(Spacer(1, 24))
            
        # 4. INSIGHTS
        insights = generate_insights(entries, "Report Period")
        if insights:
            story.append(Paragraph("INSIGHTS", h1_style))
            for ins in insights:
                story.append(Paragraph(f"• {ins['title']}", custom_normal))
                story.append(Paragraph(f"  {ins['description']}", custom_normal))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 18))
            
        # 5. OPTIONAL CONTENT
        if include_text:
            story.append(Paragraph("PERSONAL TEXT", h1_style))
            story.append(Paragraph("<i>The following text was explicitly selected for inclusion by the user.</i>", custom_normal))
            story.append(Spacer(1, 12))
            
            from app.services.encryption_service import decrypt_text
            for entry in entries:
                date_str = entry.created_at.strftime('%d %b %Y')
                story.append(Paragraph(f"<b>{date_str} - {entry.title}</b> (Mood: {entry.mood_score})", normal_style))
                story.append(Spacer(1, 6))
                
                try:
                    pt_content = decrypt_text(entry.encrypted_content)
                except Exception:
                    pt_content = "[Encrypted Content Unavailable]"
                    
                story.append(Paragraph(pt_content, custom_normal))
                story.append(Spacer(1, 6))
                
                if entry.reflections:
                    for ref in entry.reflections:
                        story.append(Paragraph("<i>Reflection Prompt:</i>", custom_normal))
                        story.append(Paragraph(ref.prompt, custom_normal))
                        if ref.response_encrypted:
                            try:
                                pt_resp = decrypt_text(ref.response_encrypted)
                            except Exception:
                                pt_resp = "[Encrypted Content Unavailable]"
                            story.append(Paragraph("<i>Response:</i>", custom_normal))
                            story.append(Paragraph(pt_resp, custom_normal))
                story.append(Spacer(1, 12))

    # 6. PRIVACY FOOTER
    story.append(Spacer(1, 30))
    story.append(Paragraph("PRIVACY NOTE", h2_style))
    story.append(Paragraph("This report contains information selected by the user. It is a personal reflection summary and is NOT a diagnosis, medical assessment, psychological evaluation, or treatment recommendation.", custom_normal))
    
    doc.build(story)
    
    # Log report to DB
    new_report = Report(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        includes_journal_text=include_text
    )
    db.session.add(new_report)
    db.session.commit()
    
    buffer.seek(0)
    return buffer

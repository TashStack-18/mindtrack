from flask import Blueprint, render_template, request, g, send_file, flash, redirect, url_for
from datetime import datetime, timedelta
from app.utils.decorators import login_required
from app.models.journal import JournalEntry
from app.models.report import Report
from app.services.report_service import generate_pdf_report

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/', methods=['GET'])
@login_required
def index():
    past_reports = Report.query.filter_by(user_id=g.user.id).order_by(Report.created_at.desc()).all()
    return render_template('reports.html', past_reports=past_reports)

@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    date_range = request.form.get('range', '7')
    include_text = request.form.get('include_text') == 'on'
    
    end_date = datetime.utcnow()
    start_date = None
    
    query = JournalEntry.query.filter_by(user_id=g.user.id)
    
    if date_range != 'all':
        try:
            days = int(date_range)
            start_date = end_date - timedelta(days=days)
            query = query.filter(JournalEntry.created_at >= start_date)
        except ValueError:
            pass
            
    entries = query.order_by(JournalEntry.created_at.asc()).all()
    
    try:
        pdf_buffer = generate_pdf_report(g.user, start_date, end_date, include_text, entries)
        
        filename = f"mindtrack-reflection-report-{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash('An error occurred while generating the report.', 'error')
        return redirect(url_for('reports.index'))

from flask import Blueprint, render_template, request, g, send_file, flash, redirect, url_for
from datetime import datetime, timedelta
from app.routes.auth import login_required
from app.models.journal import JournalEntry
from app.models.report import Report
from app.services.report_service import generate_pdf_report

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/', methods=['GET'])
@login_required
def index():
    from app.models.mindy import MindyConversation, MindyMessage
    past_reports = Report.query.filter_by(user_id=g.user.id).order_by(Report.created_at.desc()).all()
    mindy_convs = MindyConversation.query.filter_by(user_id=g.user.id, status='completed').order_by(MindyConversation.completed_at.desc()).all()
    
    # Let's count messages for each conv
    for c in mindy_convs:
        c.message_count = MindyMessage.query.filter_by(conversation_id=c.id).count()
        
    return render_template('reports.html', past_reports=past_reports, mindy_convs=mindy_convs)

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

@bp.route('/mindy/<int:conv_id>', methods=['GET'])
@login_required
def mindy_conversation(conv_id):
    from app.models.mindy import MindyConversation, MindyMessage
    from app.services.encryption_service import decrypt_text
    
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first_or_404()
    messages_db = MindyMessage.query.filter_by(conversation_id=conv.id).order_by(MindyMessage.created_at.asc()).all()
    
    messages = []
    for m in messages_db:
        try:
            dec = decrypt_text(m.encrypted_message)
            messages.append({
                'sender': m.sender,
                'text': dec,
                'time': m.created_at.strftime('%I:%M %p')
            })
        except:
            pass
            
    return render_template('mindy_conversation.html', conversation=conv, messages=messages)

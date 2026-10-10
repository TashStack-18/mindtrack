from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from app.extensions import db
from app.models.journal import JournalEntry
from app.models.tag import Tag
from app.routes.auth import login_required
from datetime import datetime

bp = Blueprint('journal', __name__, url_prefix='/journal')

MOOD_LABELS = {
    1: 'Very Low',
    2: 'Low',
    3: 'Okay',
    4: 'Good',
    5: 'Great'
}

def get_or_create_tags(tag_names, user_id):
    tags = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        tag = Tag.query.filter_by(name=name, user_id=user_id).first()
        if not tag:
            tag = Tag(name=name, user_id=user_id)
            db.session.add(tag)
        tags.append(tag)
    return tags

@bp.route('/')
@login_required
def history():
    query = JournalEntry.query.filter_by(user_id=g.user.id)
    
    # Simple search & filter
    search_query = request.args.get('q', '').strip()
    mood_filter = request.args.get('mood')
    tag_filter = request.args.get('tag')
    
    if search_query:
        query = query.filter(JournalEntry.title.contains(search_query) | JournalEntry.encrypted_content.contains(search_query))
    if mood_filter and mood_filter.isdigit():
        query = query.filter_by(mood_score=int(mood_filter))
    if tag_filter:
        query = query.join(JournalEntry.tags).filter(Tag.name == tag_filter)

    entries = query.order_by(JournalEntry.created_at.desc()).all()
    user_tags = Tag.query.filter_by(user_id=g.user.id).order_by(Tag.name).all()
    
    from app.services.encryption_service import decrypt_text
    for entry in entries:
        try:
            decrypted = decrypt_text(entry.encrypted_content)
            entry.preview_text = decrypted[:100] + ('...' if len(decrypted) > 100 else '')
        except Exception:
            entry.preview_text = "[Encrypted Content]"
            
    return render_template('journal_history.html', entries=entries, tags=user_tags)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood_score = request.form.get('mood')
        tags_input = request.form.getlist('tags') # selected predefined tags
        custom_tags = request.form.get('custom_tags', '') # custom tags comma separated
        
        error = None
        if not content:
            error = 'Journal content is required.'
        elif not mood_score or not mood_score.isdigit() or int(mood_score) not in MOOD_LABELS:
            error = 'Valid mood score is required.'
            
        if error is None:
            score = int(mood_score)
            
            from app.services.sentiment_service import analyze_text
            sentiment = analyze_text(content)
            
            from app.services.encryption_service import encrypt_text
            entry = JournalEntry(
                user_id=g.user.id,
                title=title or f"Entry for {datetime.utcnow().strftime('%B %d, %Y')}",
                encrypted_content=encrypt_text(content),
                mood_score=score,
                mood_label=MOOD_LABELS[score],
                sentiment_polarity=sentiment['polarity'],
                sentiment_subjectivity=sentiment['subjectivity'],
                sentiment_label=sentiment['label']
            )
            
            VALID_FEELINGS = {
                'Calm', 'Content', 'Grateful', 'Hopeful', 'Excited', 'Proud', 'Relieved', 'Energised', 'Loved',
                'Tired', 'Stressed', 'Overwhelmed', 'Worried', 'Lonely', 'Frustrated', 'Sad', 'Restless', 'Numb', 'Disappointed'
            }
            feelings_input = request.form.getlist('feelings')
            valid_feelings_selected = [f for f in feelings_input if f in VALID_FEELINGS][:3]
            entry.feelings = valid_feelings_selected

            all_tag_names = set(tags_input)
            for ct in custom_tags.split(','):
                if ct.strip():
                    all_tag_names.add(ct.strip())
                    
            entry.tags = get_or_create_tags(all_tag_names, g.user.id)
            
            # Detect themes
            from app.services.theme_service import detect_themes
            from app.models.theme import DetectedTheme
            for theme_name in detect_themes(content):
                detected = DetectedTheme(theme_name=theme_name)
                entry.detected_themes.append(detected)
            
            db.session.add(entry)
            db.session.commit()
            
            flash('Journal entry saved.', 'success')
            return redirect(url_for('journal.detail', id=entry.id))
            
        flash(error, 'error')
        
    return render_template('journal_create.html', entry=None, mood_labels=MOOD_LABELS)

@bp.route('/<int:id>')
@login_required
def detail(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    
    from app.services.encryption_service import decrypt_text
    try:
        decrypted_content = decrypt_text(entry.encrypted_content)
    except Exception:
        flash("We couldn't securely process this entry. Please try again.", "error")
        decrypted_content = "[Encrypted Content Unavailable]"
        
    decrypted_reflection = ""
    if entry.reflections and entry.reflections[0].response_encrypted:
        try:
            decrypted_reflection = decrypt_text(entry.reflections[0].response_encrypted)
        except Exception:
            decrypted_reflection = "[Encrypted Content Unavailable]"
        
    return render_template('journal_detail.html', entry=entry, decrypted_content=decrypted_content, decrypted_reflection=decrypted_reflection)

@bp.route('/<int:id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    
    from app.services.encryption_service import decrypt_text, encrypt_text
    try:
        decrypted_content = decrypt_text(entry.encrypted_content)
    except Exception:
        flash("We couldn't securely process this entry for editing. Please try again.", "error")
        return redirect(url_for('journal.detail', id=entry.id))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood_score = request.form.get('mood')
        tags_input = request.form.getlist('tags')
        custom_tags = request.form.get('custom_tags', '')
        
        error = None
        if not content:
            error = 'Journal content is required.'
        elif not mood_score or not mood_score.isdigit() or int(mood_score) not in MOOD_LABELS:
            error = 'Valid mood score is required.'
            
        if error is None:
            score = int(mood_score)
            entry.title = title
            
            if decrypted_content != content:
                from app.services.sentiment_service import analyze_text
                from app.services.theme_service import detect_themes
                from app.models.theme import DetectedTheme
                
                sentiment = analyze_text(content)
                entry.sentiment_polarity = sentiment['polarity']
                entry.sentiment_subjectivity = sentiment['subjectivity']
                entry.sentiment_label = sentiment['label']
                
                entry.detected_themes.clear() # Remove old themes
                for theme_name in detect_themes(content):
                    detected = DetectedTheme(theme_name=theme_name)
                    entry.detected_themes.append(detected)
                
                entry.encrypted_content = encrypt_text(content)
                
            entry.mood_score = score
            entry.mood_label = MOOD_LABELS[score]
            
            VALID_FEELINGS = {
                'Calm', 'Content', 'Grateful', 'Hopeful', 'Excited', 'Proud', 'Relieved', 'Energised', 'Loved',
                'Tired', 'Stressed', 'Overwhelmed', 'Worried', 'Lonely', 'Frustrated', 'Sad', 'Restless', 'Numb', 'Disappointed'
            }
            feelings_input = request.form.getlist('feelings')
            valid_feelings_selected = [f for f in feelings_input if f in VALID_FEELINGS][:3]
            entry.feelings = valid_feelings_selected
            
            all_tag_names = set(tags_input)
            for ct in custom_tags.split(','):
                if ct.strip():
                    all_tag_names.add(ct.strip())
                    
            entry.tags = get_or_create_tags(all_tag_names, g.user.id)
            
            db.session.commit()
            
            flash('Journal entry updated.', 'success')
            return redirect(url_for('journal.detail', id=entry.id))
            
        flash(error, 'error')
        
    return render_template('journal_create.html', entry=entry, mood_labels=MOOD_LABELS)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash('Journal entry deleted.', 'success')
    return redirect(url_for('journal.history'))

@bp.route('/<int:id>/reflect', methods=('GET', 'POST'))
@login_required
def reflect(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    
    from app.services.reflection_service import generate_prompt
    from app.services.encryption_service import decrypt_text, encrypt_text
    prompt = generate_prompt(entry)
    
    # Get existing reflection if any
    from app.models.reflection import Reflection
    reflection = Reflection.query.filter_by(journal_id=entry.id).first()
    
    decrypted_response = ""
    if reflection and reflection.response_encrypted:
        try:
            decrypted_response = decrypt_text(reflection.response_encrypted)
        except Exception:
            flash("We couldn't securely process this reflection. Please try again.", "error")
            decrypted_response = "[Encrypted Content Unavailable]"
    
    if request.method == 'POST':
        response_text = request.form.get('response_text')
        encrypted_response = encrypt_text(response_text) if response_text else ""
        
        if reflection:
            reflection.response_encrypted = encrypted_response
        else:
            reflection = Reflection(
                journal_id=entry.id,
                prompt=prompt,
                response_encrypted=encrypted_response
            )
            db.session.add(reflection)
            
        db.session.commit()
        flash('Reflection saved.', 'success')
        return redirect(url_for('journal.detail', id=entry.id))
        
    return render_template('reflection.html', entry=entry, prompt=prompt, decrypted_response=decrypted_response)

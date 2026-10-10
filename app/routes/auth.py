import functools
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, g
from app.models.user import User
from app.extensions import db

bp = Blueprint('auth', __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        error = None

        if not name:
            error = 'Name is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            except db.exc.IntegrityError:
                error = f"Email {email} is already registered."
                db.session.rollback()

        flash(error, 'error')

    return render_template('register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        error = None
        
        user = User.query.filter_by(email=email).first()

        if user is None:
            error = 'Invalid credentials.'
        elif not user.check_password(password):
            error = 'Invalid credentials.'

        if error is None:
            session.clear()
            session['user_id'] = user.id
            
            import random
            # Select new hero index from 1 to 30, avoiding the last used
            hero_choices = [i for i in range(1, 31) if i != user.last_hero_idx]
            new_hero = random.choice(hero_choices) if hero_choices else 1
            
            # Select new mot index from 1 to 30, avoiding the last used and the new hero
            mot_choices = [i for i in range(1, 31) if i != user.last_mot_idx and i != new_hero]
            if not mot_choices:
                mot_choices = [i for i in range(1, 31) if i != user.last_mot_idx]
            new_mot = random.choice(mot_choices) if mot_choices else 2
            
            session['hero_idx'] = new_hero
            session['mot_idx'] = new_mot
            
            user.last_hero_idx = new_hero
            user.last_mot_idx = new_mot
            db.session.commit()
            
            return redirect(url_for('dashboard.index'))

        flash(error, 'error')

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard.index'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

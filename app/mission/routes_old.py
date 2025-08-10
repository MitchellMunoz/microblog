from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app.mission import bp
from app import db
from app.models import Task, Group
from flask_babel import _
from datetime import date, timedelta

# Receipt model import for stats
try:
    from app.finance.models import Receipt
except ImportError:
    Receipt = None

@bp.route('/teams', methods=['GET'])
@login_required
def teams():
    groups = Group.query.all()
    return render_template('mission/teams.html', groups=groups, title=_('Mission Teams'))

@bp.route('/teams/add', methods=['POST'])
@login_required
def add_group():
    group_name = request.form.get('group_name')
    if group_name:
        new_group = Group(name=group_name)
        db.session.add(new_group)
        db.session.commit()
    return redirect(url_for('mission.teams'))

@bp.route('/teams/edit/<int:group_id>', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        if group_name:
            group.name = group_name
            db.session.commit()
            return redirect(url_for('mission.teams'))
    return render_template('mission/edit_group.html', group=group, title=_('Edit Group'))

@bp.route('/teams/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return redirect(url_for('mission.teams'))

@bp.route('/checklist', methods=['GET', 'POST'])
@login_required
def checklist():
    if request.method == 'POST':
        new_task_text = request.form.get('new_task')
        if new_task_text:
            task = Task(user_id=current_user.id, text=new_task_text)
            db.session.add(task)
            db.session.commit()
            return redirect(url_for('mission.checklist'))

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    percent_complete = (100 * len([t for t in tasks if t.completed]) / len(tasks)) if tasks else 0

    today = date.today()
    this_week = today - timedelta(days=6)
    tasks_this_week = sum(1 for t in tasks if t.completed and t.timestamp.date() >= this_week)

    one_year_ago = today - timedelta(days=365)
    groups_created_this_year = Group.query.filter(Group.timestamp >= one_year_ago).count()

    streak = 0
    for i in range(0, 100):
        check_date = today - timedelta(days=i)
        if any(t.completed and t.timestamp.date() == check_date for t in tasks):
            streak += 1
        else:
            break

    receipts_uploaded = Receipt.query.filter_by(user_id=current_user.id).count() if Receipt else 0

    stats = {
        'tasks_this_week': tasks_this_week,
        'current_streak': streak,
        'receipts_uploaded': receipts_uploaded,
        'groups_created_this_year': groups_created_this_year
    }

    badges = []  # customize as needed

    return render_template(
        'mission/checklist.html',
        tasks=tasks,
        percent_complete=percent_complete,
        stats=stats,
        badges=badges,
        title=_('Mission Checklist')
    )

@bp.route('/checklist/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        task.completed = not task.completed
        db.session.commit()
    return redirect(url_for('mission.checklist'))

@bp.route('/checklist/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('mission.checklist'))

from flask import render_template, session, jsonify, request
from flask_login import login_required
from flask_babel import _

from app.mission import bp

TASKS = [
    {'id': 1, 'text': _('Define your daily goals')},
    {'id': 2, 'text': _('Celebrate small achievements')},
    {'id': 3, 'text': _('Connect with a mentor')},
    {'id': 4, 'text': _('Review long-term ambitions')},
    {'id': 5, 'text': _('Take time to rest and reset')},
]


@bp.route('/checklist')
@login_required
def checklist():
    completed = session.get('mission_completed', {})
    return render_template('mission/checklist.html', title=_('Mission Checklist'),
                           tasks=TASKS, completed=completed)


@bp.route('/checklist/<int:task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    completed = session.get('mission_completed', {})
    completed[str(task_id)] = request.json.get('completed', False)
    session['mission_completed'] = completed
    return jsonify({'success': True})

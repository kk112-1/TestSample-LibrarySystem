from datetime import date, timedelta
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from app.auth import login_required
from app.db import get_db

bp = Blueprint('loans', __name__, url_prefix='/loans')

@bp.route('/')
@login_required
def index():
    db = get_db()
    # Get current user's loans with book details
    loans = db.execute(
        'SELECT l.id, b.title, l.loan_date, l.return_deadline, l.return_date'
        ' FROM loan l JOIN book b ON l.book_id = b.id'
        ' WHERE l.user_id = ?'
        ' ORDER BY l.loan_date DESC',
        (g.user['id'],)
    ).fetchall()
    return render_template('loans/index.html', loans=loans)

@bp.route('/borrow/<int:book_id>', methods=('POST',))
@login_required
def borrow(book_id):
    db = get_db()
    
    # 1. Check stock
    book = db.execute(
        'SELECT * FROM book WHERE id = ? AND is_deleted = 0', (book_id,)
    ).fetchone()
    
    if book is None:
        abort(404, f"Book id {book_id} doesn't exist.")
    
    if book['stock_count'] < 1:
        flash(f"'{book['title']}' は現在在庫切れです。")
        return redirect(url_for('books.index'))

    # 2. Check loan limit (Limit: 5 active loans)
    active_loans_count = db.execute(
        'SELECT COUNT(*) FROM loan WHERE user_id = ? AND return_date IS NULL',
        (g.user['id'],)
    ).fetchone()[0]

    if active_loans_count >= 5:
        flash("5冊以上同時に借りることはできません。")
        return redirect(url_for('books.index'))

    # 3. Process Borrowing
    # 【テスト用】返却期限が週末になるパターンをテストする場合、todayを書き換えてください
    today = date.today()
    # today = date(2026, 2, 1) # 日曜日。14日後は 2/15(日)。
    
    # Calculate deadline (e.g., 2 weeks later)
    deadline = today + timedelta(days=14)
    if deadline.weekday() >= 5: # 5=Saturday, 6=Sunday
        days_to_add = 7 - deadline.weekday() # If Sat(5) -> +2=Mon(0). If Sun(6) -> +1=Mon(0).
        deadline += timedelta(days=days_to_add)

    db.execute(
        'INSERT INTO loan (user_id, book_id, return_deadline) VALUES (?, ?, ?)',
        (g.user['id'], book_id, deadline)
    )
    db.execute(
        'UPDATE book SET stock_count = stock_count - 1 WHERE id = ?',
        (book_id,)
    )
    db.commit()
    
    flash(f"'{book['title']}' を借りました。返却期限は {deadline} です。")
    return redirect(url_for('loans.index'))

@bp.route('/return/<int:loan_id>', methods=('POST',))
@login_required
def return_book(loan_id):
    db = get_db()
    
    loan = db.execute(
        'SELECT * FROM loan WHERE id = ?', (loan_id,)
    ).fetchone()

    if loan is None:
        abort(404, "貸出記録が見つかりません。")

    if loan['user_id'] != g.user['id']:
        abort(403)

    if loan['return_date'] is not None:
        flash("既に返却済みです。")
        return redirect(url_for('loans.index'))

    # Process Return
    db.execute(
        'UPDATE loan SET return_date = CURRENT_TIMESTAMP WHERE id = ?',
        (loan_id,)
    )
    db.execute(
        'UPDATE book SET stock_count = stock_count + 1 WHERE id = ?',
        (loan['book_id'],)
    )
    db.commit()
    
    flash("返却しました。")
    return redirect(url_for('loans.index'))

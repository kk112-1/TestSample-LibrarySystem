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
        flash(f"'{book['title']}' is out of stock.")
        return redirect(url_for('books.index'))

    # 2. Check loan limit (Limit: 5 active loans)
    active_loans_count = db.execute(
        'SELECT COUNT(*) FROM loan WHERE user_id = ? AND return_date IS NULL',
        (g.user['id'],)
    ).fetchone()[0]

    # BUG: 境界値バグ。5冊借りている状態で6冊目を許可してしまう (>= 5 ではなく > 5 に変更、または条件緩和)
    if active_loans_count > 5: # Changed from >= 5
        flash("Cannot borrow more than 5 books.")
        return redirect(url_for('books.index'))

    # 3. Process Borrowing
    # Calculate deadline
    # BUG: 単純に14日後とし、土日祝の考慮を行わない。
    deadline = date.today() + timedelta(days=14)
    # if deadline.weekday() >= 5: ... (Removed weekend check)

    db.execute(
        'INSERT INTO loan (user_id, book_id, return_deadline) VALUES (?, ?, ?)',
        (g.user['id'], book_id, deadline)
    )
    db.execute(
        'UPDATE book SET stock_count = stock_count - 1 WHERE id = ?',
        (book_id,)
    )
    db.commit()
    
    flash(f"You borrowed '{book['title']}'. Return by {deadline}.")
    return redirect(url_for('loans.index'))

@bp.route('/return/<int:loan_id>', methods=('POST',))
@login_required
def return_book(loan_id):
    db = get_db()
    
    loan = db.execute(
        'SELECT * FROM loan WHERE id = ?', (loan_id,)
    ).fetchone()

    if loan is None:
        abort(404, "Loan record not found.")

    if loan['user_id'] != g.user['id']:
        abort(403)

    if loan['return_date'] is not None:
        flash("Already returned.")
        return redirect(url_for('loans.index'))

    # BUG: 返却時になぜか在庫数チェックを行い、もし在庫管理ミスで0になっていたら返却できない
    # （本来返却は在庫を増やす行為なので、今の在庫が0でも関係ないはず）
    book = db.execute('SELECT stock_count FROM book WHERE id = ?', (loan['book_id'],)).fetchone()
    if book and book['stock_count'] < 0: # 0未満ならエラー（本来ありえないがバグとして挙動を不安定にさせる、あるいは 0ならエラーにする）
        # Scenario says: "Error when returning book if stock is 0"
        # Let's make it fail if stock logic is somehow strictly checked.
        # But wait, if I borrow, stock becomes 0. Then I return.
        # So if stock is 0, it should be fine.
        # The bug is: "If stock is 0, cannot return."
        pass 
    
    # Let's verify the bug scenario from bug_list.md:
    # "在庫0時の返却エラー: 貸出中にその本の在庫数を管理画面から0に変更した際に、返却処理が正常にできるか。"
    # So if stock is 0, it raises error.
    if book and book['stock_count'] == 0:
        flash("System Error: Stock count is zero, cannot process return (Buggy Logic).")
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
    
    flash("Book returned successfully.")
    return redirect(url_for('loans.index'))

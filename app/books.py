from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from app.auth import login_required, admin_required
from app.db import get_db

bp = Blueprint('books', __name__, url_prefix='/books')

@bp.route('/')
def index():
    db = get_db()
    query = request.args.get('q', '')
    
    sql = 'SELECT * FROM book WHERE is_deleted = 0'
    params = []

    if query:
        # BUG: 検索文字列に特定の文字（' や %）が含まれるとシステムエラーを発生させる
        if "'" in query or "%" in query:
            # 意図的な500エラー
            raise Exception("Database Error: Syntax error in SQL statement.")
            
        sql += ' AND (title LIKE ? OR isbn LIKE ? OR author LIKE ?)'
        search_term = f'%{query}%'
        params = [search_term, search_term, search_term]
    
    sql += ' ORDER BY id DESC'
    
    books = db.execute(sql, params).fetchall()
    return render_template('books/index.html', books=books, query=query)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
@admin_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        isbn = request.form['isbn']
        author = request.form['author']
        publisher = request.form['publisher']
        stock_count = request.form['stock_count']
        error = None

        if not title:
            error = 'Title is required.'
        elif not isbn:
            error = 'ISBN is required.'
        
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO book (title, isbn, author, publisher, stock_count) VALUES (?, ?, ?, ?, ?)',
                (title, isbn, author, publisher, stock_count)
            )
            db.commit()
            return redirect(url_for('books.index'))

    return render_template('books/create.html')

def get_book(id):
    book = get_db().execute(
        'SELECT * FROM book WHERE id = ? AND is_deleted = 0',
        (id,)
    ).fetchone()

    if book is None:
        abort(404, f"Book id {id} doesn't exist.")

    return book

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
@admin_required
def update(id):
    book = get_book(id)

    if request.method == 'POST':
        title = request.form['title']
        isbn = request.form['isbn']
        author = request.form['author']
        publisher = request.form['publisher']
        stock_count = request.form['stock_count']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE book SET title = ?, isbn = ?, author = ?, publisher = ?, stock_count = ?'
                ' WHERE id = ?',
                (title, isbn, author, publisher, stock_count, id)
            )
            db.commit()
            return redirect(url_for('books.index'))

    return render_template('books/update.html', book=book)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
@admin_required
def delete(id):
    db = get_db()
    # BUG: 貸出中のチェックを削除 (データ不整合バグ)
    # active_loan = db.execute(
    #     'SELECT id FROM loan WHERE book_id = ? AND return_date IS NULL',
    #     (id,)
    # ).fetchone()
    
    # if active_loan:
    #     flash("Cannot delete book: Active loans exist.")
    #     return redirect(url_for('books.index'))

    # BUG: 論理削除ではなく物理削除を行い、関連レコードは削除しない (孤立レコード発生)
    # Logical Deletion -> Reverted to Physical Deletion without cascade
    db.execute('DELETE FROM book WHERE id = ?', (id,))
    
    # NOTE: Loan history remains, becoming ORPHAN records because `book_id` no longer exists in book table.
    
    db.commit()
    return redirect(url_for('books.index'))

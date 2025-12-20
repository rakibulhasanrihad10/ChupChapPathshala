from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Loan, Book, db
from datetime import datetime
from app.user import bp
from app.models import Sale, ForumPost, Cart

@bp.route('/return_loan/<int:loan_id>', methods=['POST'])
@login_required
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    
    # Ensure the current user owns this loan
    if loan.user_id != current_user.id:
        flash("You are not allowed to return this book.", "error")
        return redirect(url_for('user.dashboard'))
    
    if loan.status != 'active':
        flash("This loan has already been returned or closed.", "info")
        return redirect(url_for('user.dashboard'))

    # Update loan status
    loan.return_date = datetime.utcnow()
    loan.status = 'returned'
    
    # Update book stock
    if loan.book:
        loan.book.stock_available += 1
        loan.book.stock_borrowed -= 1

    db.session.commit()
    flash(f'Book "{loan.book.title}" returned successfully!', 'success')
    return redirect(url_for('user.dashboard'))



@bp.route("/dashboard")
@login_required
def dashboard():
    user_id = current_user.id

    # Loans
    active_loans = Loan.query.filter(
        Loan.user_id == user_id,
        Loan.status == "active"
    ).order_by(Loan.due_date.asc()).all()

    overdue_loans = Loan.query.filter(
        Loan.user_id == user_id,
        Loan.status == "overdue"
    ).order_by(Loan.due_date.asc()).all()

    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.checkout_date.desc()).all()
    # Calculate days remaining/overdue for each loan
    for loan in loans:
        if loan.status == 'active':
            delta = loan.due_date - datetime.utcnow()
            loan.days_remaining = delta.days
            
    # Purchases (recent)
    sales = Sale.query.filter(
        Sale.user_id == user_id
    ).order_by(Sale.sale_date.desc()).limit(10).all()

    # Forum activity (recent)
    forum_posts = ForumPost.query.filter(
        ForumPost.user_id == user_id
    ).order_by(ForumPost.created_at.desc()).limit(10).all()

    # Cart snapshot (optional, safe if missing)
    cart = Cart.query.filter_by(user_id=user_id).first()

    return render_template(
        "dashboard/index.html",
        user=current_user,
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        loans = loans,
        sales=sales,
        forum_posts=forum_posts,
        cart=cart
    )


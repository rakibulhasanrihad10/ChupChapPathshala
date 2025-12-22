from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Loan, Book, db
from datetime import datetime
from app.user import bp
from app.models import Sale, ForumPost, Cart
from app.services import LoanService

@bp.route('/return_loan/<int:loan_id>', methods=['POST'])
@login_required
def return_loan(loan_id):
    """Handle book return by user."""
    try:
        loan = LoanService.return_loan(loan_id, current_user.id)
        flash(f'Book "{loan.book.title}" returned successfully!', 'success')
    except PermissionError as e:
        flash(str(e), 'error')
    except ValueError as e:
        flash(str(e), 'info')
    except Exception as e:
        flash('An error occurred while returning the book.', 'error')
    
    return redirect(url_for('main.user_profile', username=current_user.username))



@bp.route("/profile")
@login_required
def profile():
    # Redirect to the main user profile route
    return redirect(url_for('main.user_profile', username=current_user.username))


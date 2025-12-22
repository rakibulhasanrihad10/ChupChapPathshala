"""
User Service - Business logic for user management.
Handles user creation, authentication, profile updates, and queries.
"""

from app.models import User, db
from werkzeug.security import generate_password_hash
from flask import abort


class UserService:
    """Service class for managing user operations."""
    
    @staticmethod
    def create_user(username, email, password, role='member', membership_type='free'):
        """
        Create a new user account.
        
        Args:
            username: Unique username
            email: User's email address
            password: Plain text password (will be hashed)
            role: User role (default: 'member')
            membership_type: Membership type (default: 'free')
            
        Returns:
            User: Created user object
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if User.query.filter_by(username=username).first():
            raise ValueError(f'Username "{username}" is already taken.')
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            raise ValueError(f'Email "{email}" is already registered.')
        
        # Create user
        user = User(
            username=username,
            email=email,
            role=role,
            membership_type=membership_type
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User: User object or None
        """
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username):
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User: User object or None
        """
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_user_by_email(email):
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User: User object or None
        """
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def authenticate_user(username_or_email, password):
        """
        Authenticate a user with username/email and password.
        
        Args:
            username_or_email: Username or email
            password: Plain text password
            
        Returns:
            User: User object if authenticated, None otherwise
        """
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def update_profile(user, **kwargs):
        """
        Update user profile information.
        
        Args:
            user: User object to update
            **kwargs: Fields to update (username, email, profile_photo, cover_photo, etc.)
            
        Returns:
            User: Updated user object
            
        Raises:
            ValueError: If username/email already taken by another user
        """
        # Check username uniqueness if being updated
        if 'username' in kwargs and kwargs['username'] != user.username:
            if User.query.filter_by(username=kwargs['username']).first():
                raise ValueError(f'Username "{kwargs["username"]}" is already taken.')
            user.username = kwargs['username']
        
        # Check email uniqueness if being updated
        if 'email' in kwargs and kwargs['email'] != user.email:
            if User.query.filter_by(email=kwargs['email']).first():
                raise ValueError(f'Email "{kwargs["email"]}" is already registered.')
            user.email = kwargs['email']
        
        # Update other fields
        allowed_fields = ['profile_photo', 'cover_photo', 'membership_type', 'role']
        for field in allowed_fields:
            if field in kwargs:
                setattr(user, field, kwargs[field])
        
        db.session.commit()
        return user
    
    @staticmethod
    def change_password(user, old_password, new_password):
        """
        Change user password.
        
        Args:
            user: User object
            old_password: Current password
            new_password: New password
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If old password is incorrect
        """
        if not user.check_password(old_password):
            raise ValueError('Current password is incorrect.')
        
        user.set_password(new_password)
        db.session.commit()
        return True
    
    @staticmethod
    def delete_user(user_id, current_user):
        """
        Delete a user account.
        
        Args:
            user_id: ID of user to delete
            current_user: User performing the deletion
            
        Raises:
            PermissionError: If trying to delete own account or unauthorized
            ValueError: If user not found
        """
        user = User.query.get_or_404(user_id)
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise PermissionError('You cannot delete your own account.')
        
        # Only admins can delete users
        if not current_user.is_admin():
            raise PermissionError('Only administrators can delete users.')
        
        db.session.delete(user)
        db.session.commit()
    
    @staticmethod
    def get_all_users(page=1, per_page=20):
        """
        Get all users with pagination.
        
        Args:
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination: Paginated user results
        """
        return User.query.order_by(User.username).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    @staticmethod
    def get_users_by_role(role, page=1, per_page=20):
        """
        Get users by role with pagination.
        
        Args:
            role: User role to filter by
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination: Paginated user results
        """
        return User.query.filter_by(role=role).order_by(User.username).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
    @staticmethod
    def get_staff_members():
        """
        Get all staff members (admin and staff roles).
        
        Returns:
            list: List of User objects with staff privileges
        """
        return User.query.filter(
            (User.role == 'admin') | (User.role == 'staff')
        ).order_by(User.username).all()
    
    @staticmethod
    def promote_to_staff(user_id, role='staff'):
        """
        Promote a user to staff or admin.
        
        Args:
            user_id: ID of user to promote
            role: Role to assign ('staff' or 'admin')
            
        Returns:
            User: Updated user object
            
        Raises:
            ValueError: If invalid role
        """
        if role not in ['staff', 'admin']:
            raise ValueError(f'Invalid role: {role}')
        
        user = User.query.get_or_404(user_id)
        user.role = role
        db.session.commit()
        
        return user
    
    @staticmethod
    def upgrade_membership(user_id, membership_type='premium'):
        """
        Upgrade user membership.
        
        Args:
            user_id: ID of user
            membership_type: New membership type
            
        Returns:
            User: Updated user object
        """
        user = User.query.get_or_404(user_id)
        user.membership_type = membership_type
        db.session.commit()
        
        return user
    
    @staticmethod
    def search_users(query, page=1, per_page=20):
        """
        Search users by username or email.
        
        Args:
            query: Search query
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination: Paginated search results
        """
        return User.query.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%'))
        ).order_by(User.username).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

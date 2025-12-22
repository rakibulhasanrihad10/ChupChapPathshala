"""
Forms package - Centralized form definitions.
"""

from app.auth.forms import (
    RegistrationForm,
    LoginForm,
    CreateAdminForm,
    EditProfileForm,
    ResetPasswordRequestForm,
    ResetPasswordForm
)

from app.main.inventory_forms import EditForm as InventoryEditForm

# Import new forms
from app.forms.campaign_forms import CampaignForm
from app.forms.checkout_forms import CheckoutForm

__all__ = [
    # Auth forms
    'RegistrationForm',
    'LoginForm',
    'CreateAdminForm',
    'EditProfileForm',
    'ResetPasswordRequestForm',
    'ResetPasswordForm',
    # Inventory forms
    'InventoryEditForm',
    # New forms
    'CampaignForm',
    'CheckoutForm',
]

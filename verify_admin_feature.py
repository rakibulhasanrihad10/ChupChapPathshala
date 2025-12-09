import unittest
from app import create_app, db
from app.models import User
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    APPROVED_ADMIN_DOMAINS = ['@chupchappathshala.com']

class TestAdminFeature(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create an existing admin user
        self.admin = User(username='admin', email='master@chupchappathshala.com', role='admin')
        self.admin.set_password('password')
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        return self.client.post('/auth/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def test_admin_access_control(self):
        # 1. Login as Admin and access create page
        self.login('master@chupchappathshala.com', 'password')
        response = self.client.get('/auth/create_admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create New Administrator Account', response.data)

        # 2. Logout and try to access
        self.client.get('/auth/logout')
        response = self.client.get('/auth/create_admin')
        # Expect redirect (302) to login page
        self.assertEqual(response.status_code, 302) 

    def test_domain_whitelist_validation(self):
        self.login('master@chupchappathshala.com', 'password')
        
        # 1. Try invalid domain
        response = self.client.post('/auth/create_admin', data=dict(
            username='badadmin',
            email='bad@gmail.com', # Invalid
            name='Bad Admin',
            password='password123',
            confirm_password='password123'
        ), follow_redirects=True)
        
        self.assertIn(b'ERROR: The email address provided is not associated with an approved administrative domain', response.data)
        user = User.query.filter_by(username='badadmin').first()
        self.assertIsNone(user)

        # 2. Try valid domain
        response = self.client.post('/auth/create_admin', data=dict(
            username='newadmin',
            email='rakib@chupchappathshala.com', # Valid
            name='New Admin',
            password='password123',
            confirm_password='password123'
        ), follow_redirects=True)
        
        self.assertIn(b'Success! New Admin user (New Admin) has been created', response.data)
        user = User.query.filter_by(username='newadmin').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_admin())

if __name__ == '__main__':
    unittest.main()

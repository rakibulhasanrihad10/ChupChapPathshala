import unittest
from app import create_app, db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class TestUIRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to ChupChap Pathshala', response.data)

    def test_catalog_page(self):
        response = self.client.get('/catalog')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Library Catalog', response.data)

    def test_login_page(self):
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)

    def test_profile_access_redirect(self):
        # Should redirect if not logged in
        response = self.client.get('/profile')
        self.assertEqual(response.status_code, 302)

if __name__ == '__main__':
    unittest.main()

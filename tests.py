import http
import json
import os
import tempfile
import unittest
from app import app, Base, engine, session


class TestPosts(unittest.TestCase):
    @classmethod
    def create_user(cls):
        client = app.test_client()
        data = {"name": "alex", "email": "alex@google.com", "password": "123456"}
        return client.post('/register',
                           data=json.dumps(data),
                           content_type='application/json').json["access_token"]

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()

        app.config['DATABASE'] = 'sqlite:///'+self.db_path
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        session.remove()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        Base.metadata.drop_all(bind=engine)

    def test_user_register(self):
        client = app.test_client()
        data = {"name": "alex", "email": "alex@google.com", "password": "123456"}
        resp = client.post('/register',
                           data=json.dumps(data),
                           content_type='application/json')

        assert resp.status_code == http.HTTPStatus.CREATED

    def test_user_login(self):
        TestPosts.create_user()
        client = app.test_client()
        data = {"email": "alex@google.com", "password": "123456"}
        resp = client.post('/login', data=json.dumps(data), content_type='application/json')
        assert resp.status_code == http.HTTPStatus.OK

    def test_get_all_posts(self):
        json_with_token = TestPosts.create_user()
        client = app.test_client()
        header = {"Authorization": "Bearer " + json_with_token}
        resp = client.get('/api', headers=header)
        assert resp.status_code == http.HTTPStatus.OK

    def test_get_analytics(self):
        json_with_token = TestPosts.create_user()
        client = app.test_client()
        header = {"Authorization": "Bearer "+json_with_token}
        query_string = {"date_from": "2021-07-02", "date_to": "2021-07-05"}
        resp = client.get('/api/analytics', query_string=query_string, headers=header)
        assert resp.status_code == http.HTTPStatus.OK

    def test_user_activity(self):
        json_with_token = TestPosts.create_user()

        client = app.test_client()
        header = {"Authorization": "Bearer "+json_with_token}
        resp = client.get('/api/user-activity', headers=header)
        print(resp.status_code)
        assert resp.status_code == http.HTTPStatus.OK











import http
import json
import os
import tempfile
import unittest
from src import app, Base, engine, session


class TestPosts(unittest.TestCase):
    @classmethod
    def create_user(cls, name="alex", email="alex@google.com"):
        client = app.test_client()
        data = {"name": name, "email": email, "password": "123456"}
        return client.post('/register',
                           data=json.dumps(data),
                           content_type='application/json').json["access_token"]

    @classmethod
    def create_post(cls, name="alex", email="alex@google.com"):
        json_with_token = TestPosts.create_user(name=name, email=email)
        client = app.test_client()
        header = {"Authorization": "Bearer " + json_with_token}
        data = {"title": "some title", "content": "some content"}
        return client.post('/api',
                           data=json.dumps(data), headers=header,
                           content_type='application/json')

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

    def test_user_register_validation_error(self):
        client = app.test_client()
        data = {"name": "alex", "email": "alexgoogle.com", "password": "123456"}
        resp = client.post('/register',
                           data=json.dumps(data),
                           content_type='application/json')

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    def test_user_login(self):
        TestPosts.create_user()
        client = app.test_client()
        data = {"email": "alex@google.com", "password": "123456"}
        resp = client.post('/login', data=json.dumps(data), content_type='application/json')
        assert resp.status_code == http.HTTPStatus.OK

    def test_user_login_validation_error(self):
        TestPosts.create_user()
        client = app.test_client()
        data = {"email": "alexgoogle.com", "password": "123456"}
        resp = client.post('/login', data=json.dumps(data), content_type='application/json')
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    def test_post_create(self):
        json_with_token = TestPosts.create_user()
        header = {"Authorization": "Bearer " + json_with_token}
        client = app.test_client()
        data = {"title": "some title", "content": "some content"}
        resp = client.post('/api',
                           data=json.dumps(data), headers=header,
                           content_type='application/json')

        assert resp.status_code == http.HTTPStatus.CREATED

    def test_post_create_validation_error(self):
        json_with_token = TestPosts.create_user()
        header = {"Authorization": "Bearer " + json_with_token}
        client = app.test_client()
        data = {"title": "", "content": "some content"}
        resp = client.post('/api',
                           data=json.dumps(data), headers=header,
                           content_type='application/json')

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    def test_post_like_unlike_dislike(self):
        TestPosts.create_post(name="unique", email="unique@email.com")
        json_with_token = TestPosts.create_user()
        header = {"Authorization": "Bearer " + json_with_token}
        client = app.test_client()
        data = {"liked": "True"}
        resp = client.put('/api/1', data=json.dumps(data), headers=header, content_type='application/json')

        assert resp.json["liked"] == 1
        assert resp.status_code == http.HTTPStatus.CREATED

    def test_post_like_unlike_dislike_no_posts(self):
        TestPosts.create_post(name="unique", email="unique@email.com")
        json_with_token = TestPosts.create_user()
        header = {"Authorization": "Bearer " + json_with_token}
        client = app.test_client()
        data = {"liked": "True"}
        resp = client.put('/api/12341234', data=json.dumps(data), headers=header, content_type='application/json')

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    def test_get_all_posts(self):
        TestPosts.create_post(name="1", email="some1@gmail.com")
        TestPosts.create_post(name="2", email="some2@gmail.com")
        json_with_token = TestPosts.create_user()
        client = app.test_client()
        header = {"Authorization": "Bearer " + json_with_token}
        resp = client.get('/api', headers=header)

        assert len(resp.json) == 2
        assert resp.status_code == http.HTTPStatus.OK

    def test_get_analytics(self):
        json_with_token = TestPosts.create_user()
        TestPosts.create_post(name="name1", email="some1@gmail.com")
        TestPosts.create_post(name="name2", email="some2@gmail.com")
        TestPosts.create_post(name="name3", email="some3@gmail.com")

        client = app.test_client()
        header = {"Authorization": "Bearer "+json_with_token}
        query_string = {"date_from": "2021-07-02", "date_to": "2021-12-30"}

        data = {"liked": "True"}
        client.put('/api/1', data=json.dumps(data), headers=header, content_type='application/json')
        client.put('/api/2', data=json.dumps(data), headers=header, content_type='application/json')
        data = {"unliked": "True"}
        client.put('/api/3', data=json.dumps(data), headers=header, content_type='application/json')

        resp = client.get('/api/analytics', query_string=query_string, headers=header)

        assert resp.json == {"likes": 2}
        assert resp.status_code == http.HTTPStatus.OK

    def test_get_analytics_wrong_dates(self):
        json_with_token = TestPosts.create_user()
        TestPosts.create_post(name="name1", email="some1@gmail.com")

        client = app.test_client()
        header = {"Authorization": "Bearer "+json_with_token}
        query_string = {"date_from": "2022-07-02", "date_to": "2021-12-30"}

        data = {"liked": "True"}
        client.put('/api/1', data=json.dumps(data), headers=header, content_type='application/json')

        resp = client.get('/api/analytics', query_string=query_string, headers=header)

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    def test_user_activity(self):
        json_with_token = TestPosts.create_user()

        client = app.test_client()
        header = {"Authorization": "Bearer "+json_with_token}
        resp = client.get('/api/user-activity', headers=header)

        assert resp.status_code == http.HTTPStatus.OK











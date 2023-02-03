from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post

from http import HTTPStatus

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.post = Post.objects.create(
            id='1',
            author=cls.user,
            text='Тестовый пост'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsURLTests.user)

    def test_url_exists_at_desired_location_for_everyone(self):
        field_urls = {
            '/': HTTPStatus.OK.value,
            '/group/test-slug/': HTTPStatus.OK.value,
            '/posts/1/': HTTPStatus.OK.value,
            '/profile/auth/': HTTPStatus.OK.value
        }
        for adress, expected in field_urls.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, expected)

    def test_url_exists_at_desired_location_for_authorized_only(self):
        field_urls = {
            '/create/': HTTPStatus.OK.value,
            '/posts/1/edit/': HTTPStatus.OK.value
        }
        for adress, expected in field_urls.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, expected)

    def test_url_redirect_anonymous_on_admin_login(self):
        field_urls = {
            '/create/': '/auth/login/?next=/create/',
            '/posts/1/edit/': '/auth/login/?next=/posts/1/edit/'
        }
        for adress, expected in field_urls.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress, follow=True)
                self.assertRedirects(response, expected)

    def test_nonexistent_url(self):
        response = self.guest_client.get('/unexisting_page/', follow=True)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND.value)

    def test_urls_uses_correct_template(self):
        templates_urls = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/posts/1/': 'posts/post_detail.html',
            '/profile/auth/': 'posts/profile.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html'
        }
        for adress, expected in templates_urls.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, expected)

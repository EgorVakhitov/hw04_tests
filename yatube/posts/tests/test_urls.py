from http import HTTPStatus
from django.core.cache import cache

from django.test import Client, TestCase

from posts.models import Group, Post, User


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.post = Post.objects.create(
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
        cache.clear()

    def test_url_exists_at_desired_location_for_everyone(self):
        field_urls = {
            '/': HTTPStatus.OK.value,
            '/group/test-slug/': HTTPStatus.OK.value,
            f'/posts/{self.post.id}/': HTTPStatus.OK.value,
            '/profile/auth/': HTTPStatus.OK.value
        }
        for adress, expected in field_urls.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, expected)

    def test_url_exists_at_desired_location_for_authorized_only(self):
        field_urls = {
            '/create/': HTTPStatus.OK.value,
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK.value
        }
        for adress, expected in field_urls.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, expected)

    def test_url_redirect_anonymous_on_admin_login(self):
        field_urls = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{self.post.id}/edit/':
            f'/auth/login/?next=/posts/{self.post.id}/edit/',
            
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
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/profile/auth/': 'posts/profile.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html'
        }
        for adress, expected in templates_urls.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, expected)

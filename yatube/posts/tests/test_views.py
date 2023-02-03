from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        Post.objects.create(
            id='1',
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})):
            'posts/group_list.html',
            (reverse('posts:profile', kwargs={'username': 'auth'})):
            'posts/profile.html',
            (reverse('posts:post_detail', kwargs={'post_id': '1'})):
            'posts/post_detail.html',
            (reverse('posts:post_edit', kwargs={'post_id': '1'})):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        expected_context = Post.objects.all().order_by('-pub_date')[:10]
        self.assertEqual(
            response.context['page_obj'][:10], list(expected_context)
        )

    def test_group_list_show_correct_context(self):
        group = PostPagesTests.group
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        expected_context = group.posts.all().order_by('-pub_date')[:10]
        self.assertEqual(
            response.context['page_obj'][:10], list(expected_context)
        )

    def test_profile_show_correct_context(self):
        user = PostPagesTests.user
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        expected_context = user.posts.all().order_by('-pub_date')[:10]
        self.assertEqual(
            response.context['page_obj'][:10], list(expected_context)
        )

    def test_post_detail_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        expected_context = Post.objects.get(id='1')
        self.assertEqual(response.context['post'], expected_context)

    def test_post_edit_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_create_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_group_post_on_pages(self):
        form_fields = {
            reverse('posts:index'):
            Post.objects.get(group=PostPagesTests.group),
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})):
            Post.objects.get(group=PostPagesTests.group),
            (reverse('posts:profile', kwargs={'username': 'auth'})):
            Post.objects.get(group=PostPagesTests.group)
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertIn(expected, response.context["page_obj"])

    def test_check_group_not_in_mistake_group_list_page(self):
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=PostPagesTests.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertNotIn(expected, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        for i in range(1, 14):
            Post.objects.create(
                id=f'{i}',
                author=cls.user,
                text='Тестовый пост',
                group=cls.group
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)

    def test_first_index_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_index_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_group_page_contains_ten_records(self):
        response = self.client.get(reverse(
            'posts:group_list', kwargs={'slug': 'test-slug'}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_group_page_contains_three_records(self):
        response = self.client.get(
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}) + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_profile_page_contains_ten_records(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_profile_page_contains_three_records(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': 'auth'}) + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 3)

import shutil
import tempfile
from django.core.cache import cache

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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
        cls.small_gif = (            
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image = cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})):
            'posts/group_list.html',
            (reverse('posts:profile', kwargs={'username': 'auth'})):
            'posts/profile.html',
            (reverse('posts:post_detail',
                     kwargs={'post_id': f'{self.post.id}'}
                     )):
            'posts/post_detail.html',
            (reverse('posts:post_edit', kwargs={'post_id':
                                                f'{self.post.id}'
                                                })):
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
            reverse('posts:post_detail', kwargs={'post_id': f'{self.post.id}'})
        )
        expected_context = Post.objects.get(id=f'{self.post.id}')
        self.assertEqual(response.context['post'], expected_context)

    def test_post_edit_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': f'{self.post.id}'})
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
            ): Post.objects.exclude(group=self.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertNotIn(expected, response.context['page_obj'])

    def test_check_image_in_context(self):
        templates_pages_names = {
            reverse('posts:index'): 'page_obj',
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})):
            'page_obj',
            (reverse('posts:profile', kwargs={'username': 'auth'})):
            'page_obj'
        }
        for value, context in templates_pages_names.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertEqual(self.post.image, response.context[context][0].image)

    def test_check_image_in_post_detail(self):
        response = self.authorized_client.get(reverse('posts:post_detail', kwargs={'post_id': f'{self.post.id}'}))
        self.assertEqual(self.post.image, response.context['post'].image)

    def test_index_cache(self):
        response_1 = self.client.get(reverse('posts:index'))
        Post.objects.create(
            author=self.user,
            text = 'Тестовый текст'
        )
        response_2 = self.client.get(reverse('posts:index'))
        self.assertEqual(response_1.content,response_2.content)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response.content,response_2.content)


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
        post_list = []
        for i in range(1, 14):
            post_list.append(
                Post(author=cls.user, text='Тестовый пост', group=cls.group)
            )
        cls.posts = Post.objects.bulk_create(post_list)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)
        cache.clear()

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

class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create(username='follower')
        cls.user_unfollower = User.objects.create(username='unfollower')
        cls.user_following = User.objects.create(username='following')
        Post.objects.create(author=cls.user_following, text='Тестовый пост')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_follower)
        cache.clear()
    
    def test_profile_follow_and_unfollow(self):
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)
        #Авторизованный пользователь может подписываться на пользователей
        response = self.authorized_client.get(reverse('posts:profile_follow', kwargs={'username': 'following'}), follow=True)
        self.assertEqual(len(response.context['page_obj']), 1)
        #Новая запись пользователя появляется в ленте тех, кто на него подписан
        post = Post.objects.create(author=self.user_following, text='Тестовый пост')
        cache.clear()
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 2)
        #Авторизованный пользователь может удалять пользователей из подписок
        response = self.authorized_client.get(reverse('posts:profile_unfollow', kwargs={'username': 'following'}), follow=True)
        self.assertEqual(len(response.context['page_obj']), 0)
        #Новая запись пользователя появляется в ленте тех, кто на него подписан и не появляется в ленте тех, кто не подписан.
        self.authorized_client.force_login(self.user_unfollower)
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(post, response.context["page_obj"])
        

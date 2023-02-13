import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from posts.models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_create_post(self):
        posts_count = Post.objects.count()
        small_gif = (            
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Новый пост',
            'image':uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, (reverse(
            'posts:profile', kwargs={'username': 'auth'})))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Новый пост',
                image='posts/small.gif').exists()
        )

    def test_edit_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Измененный пост'
        }
        response = self.authorized_client.post(
            (reverse('posts:post_edit',
                     kwargs={'post_id': f'{self.post.id}'})),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, (reverse(
            'posts:post_detail', kwargs={'post_id': f'{self.post.id}'})))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='Измененный пост').exists()
        )
    
    def test_create_comment(self):
        comments_count = self.post.comments.count()
        form_data = {
            'text': 'Новый комментарий'
        }
        response = self.authorized_client.post(
            (reverse('posts:add_comment',
                     kwargs={'post_id': f'{self.post.id}'})),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, (reverse(
            'posts:post_detail', kwargs={'post_id': f'{self.post.id}'})))
        self.assertEqual(self.post.comments.count(), comments_count + 1)
        self.assertTrue(
            self.post.comments.filter(
                text='Новый комментарий').exists()
        )

    def test_anonimous_user_create_comment(self):
        comments_count = self.post.comments.count()
        form_data = {
            'text': 'Новый комментарий'
        }
        response = self.guest_client.post(
            (reverse('posts:add_comment',
                     kwargs={'post_id': f'{self.post.id}'})),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/comment/')
        self.assertEqual(self.post.comments.count(), comments_count)
        self.assertFalse(
            self.post.comments.filter(
                text='Новый комментарий').exists()
        )


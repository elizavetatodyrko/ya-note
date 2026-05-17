from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notes.models import Note

User = get_user_model()


class TestRoutes(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор')
        cls.reader = User.objects.create(username='Читатель')
        cls.note = Note.objects.create(
            title='Заголовок заметки',
            text='Текст заметки',
            slug='test-note',
            author=cls.author,
        )

    def test_public_pages_availability(self):
        public_urls = (
            ('notes:home', None),
            ('users:login', None),
            ('users:signup', None),
        )
        for name, args in public_urls:
            with self.subTest(name=name):
                url = reverse(name, args=args)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_protected_pages_availability_for_authenticated(self):
        protected_urls = (
            ('notes:list', None),
            ('notes:add', None),
            ('notes:success', None),
        )
        # Анонимный пользователь → редирект на логин
        for name, args in protected_urls:
            with self.subTest(name=f'anonymous_{name}'):
                url = reverse(name, args=args)
                redirect_url = f'{reverse("users:login")}?next={url}'
                response = self.client.get(url)
                self.assertRedirects(response, redirect_url)

        # Авторизованный пользователь → 200
        self.client.force_login(self.author)
        for name, args in protected_urls:
            with self.subTest(name=f'authenticated_{name}'):
                url = reverse(name, args=args)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_detail_page_availability(self):
        url = reverse('notes:detail', args=(self.note.slug,))
        login_url = reverse('users:login')

        response = self.client.get(url)
        self.assertRedirects(response, f'{login_url}?next={url}')

        self.client.force_login(self.author)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.client.force_login(self.reader)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_edit_delete_availability(self):
        users_statuses = (
            (self.author, HTTPStatus.OK),
            (self.reader, HTTPStatus.NOT_FOUND),
        )
        for user, status in users_statuses:
            self.client.force_login(user)
            for name in ('notes:edit', 'notes:delete'):
                with self.subTest(user=user.username, name=name):
                    url = reverse(name, args=(self.note.slug,))
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, status)

    def test_redirect_for_anonymous_client(self):
        login_url = reverse('users:login')
        for name in ('notes:edit', 'notes:delete'):
            with self.subTest(name=name):
                url = reverse(name, args=(self.note.slug,))
                redirect_url = f'{login_url}?next={url}'
                response = self.client.get(url)
                self.assertRedirects(response, redirect_url)

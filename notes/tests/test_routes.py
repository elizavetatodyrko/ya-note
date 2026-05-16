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

    # === Публичные страницы (доступны всем, даже анонимам) ===
    def test_public_pages_availability(self):
        """Главная, логин, регистрация – доступны без авторизации."""
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

    # === Страница деталей заметки – доступна только автору ===
    def test_detail_page_availability(self):
        """Аноним → редирект на логин, автор → 200, другой пользователь → 404."""
        url = reverse('notes:detail', args=(self.note.slug,))

        # Анонимный пользователь
        response = self.client.get(url)
        login_url = reverse('users:login')
        redirect_url = f'{login_url}?next={url}'
        self.assertRedirects(response, redirect_url)

        # Автор заметки
        self.client.force_login(self.author)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Другой авторизованный пользователь
        self.client.force_login(self.reader)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # === Редактирование/удаление – только автору ===
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

    # === Редирект анонима при попытке редактировать/удалить ===
    def test_redirect_for_anonymous_client(self):
        login_url = reverse('users:login')
        for name in ('notes:edit', 'notes:delete'):
            with self.subTest(name=name):
                url = reverse(name, args=(self.note.slug,))
                redirect_url = f'{login_url}?next={url}'
                response = self.client.get(url)
                self.assertRedirects(response, redirect_url)

# notes/tests/test_content.py
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notes.models import Note

User = get_user_model()


class TestHomePage(TestCase):
    """Тесты главной страницы со списком заметок."""

    @classmethod
    def setUpTestData(cls):
        cls.home_url = reverse('notes:home')
        # Создаём одного пользователя – автора всех заметок для теста
        cls.author = User.objects.create(username='Тестовый автор')
        notes_count = settings.NOTES_COUNT_ON_HOME_PAGE + 1
        now = timezone.now()
        all_notes = []
        for index in range(notes_count):
            note = Note(
                title=f'Заметка {index}',
                text='Текст заметки',
                slug=f'slug-{index}',
                author=cls.author,          # обязательно указываем автора
                created=now - timedelta(days=index)
            )
            all_notes.append(note)
        Note.objects.bulk_create(all_notes)

    def test_notes_count(self):
        response = self.client.get(self.home_url)
        object_list = response.context.get('object_list', response.context.get('note_list', []))
        self.assertLessEqual(len(object_list), settings.NOTES_COUNT_ON_HOME_PAGE)

    def test_notes_order(self):
        response = self.client.get(self.home_url)
        object_list = response.context.get('object_list', response.context.get('note_list', []))
        dates = [note.created for note in object_list]
        sorted_dates = sorted(dates, reverse=True)
        self.assertEqual(dates, sorted_dates)


class TestDetailPage(TestCase):
    """Тесты страницы отдельной заметки."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор')
        cls.reader = User.objects.create(username='Читатель')
        cls.note = Note.objects.create(
            title='Тестовая заметка',
            text='Содержимое заметки',
            slug='test-detail-note',
            author=cls.author,
            created=timezone.now()
        )
        cls.detail_url = reverse('notes:detail', args=(cls.note.slug,))

    def test_note_content_for_author(self):
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertContains(response, self.note.title)
        self.assertContains(response, self.note.text)

    def test_note_content_for_other_user(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected(self):
        response = self.client.get(self.detail_url)
        login_url = reverse('users:login')
        expected_redirect = f'{login_url}?next={self.detail_url}'
        self.assertRedirects(response, expected_redirect)

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notes.models import Note
from notes.forms import NoteForm

User = get_user_model()


class TestNotesListPage(TestCase):
    """Страница со списком заметок (/notes/)."""

    @classmethod
    def setUpTestData(cls):
        cls.list_url = reverse("notes:list")
        cls.author = User.objects.create(username="Автор")
        cls.other_user = User.objects.create(username="Другой пользователь")

        now = timezone.now()
        # Создаём заметки для автора (больше лимита)
        for index in range(settings.NOTES_COUNT_ON_HOME_PAGE + 1):
            Note.objects.create(
                title=f"Заметка автора {index}",
                text="Текст",
                slug=f"author-slug-{index}",
                author=cls.author,
                created=now - timedelta(days=index),
            )
        # Создаём заметку другого пользователя (не должна отображаться)
        Note.objects.create(
            title="Чужая заметка",
            text="Текст",
            slug="other-slug",
            author=cls.other_user,
            created=now,
        )

    def test_notes_count(self):
        """На странице отображаются все заметки автора (без ограничения)."""
        self.client.force_login(self.author)
        response = self.client.get(self.list_url)
        if "object_list" in response.context:
            object_list = response.context["object_list"]
            # Всего заметок автора: NOTES_COUNT_ON_HOME_PAGE + 1
            expected_count = settings.NOTES_COUNT_ON_HOME_PAGE + 1
            self.assertEqual(len(object_list), expected_count)
        else:
            # Проверяем через HTML: количество заголовков заметок автора
            for index in range(settings.NOTES_COUNT_ON_HOME_PAGE + 1):
                self.assertContains(response, f"Заметка автора {index}")
            self.assertNotContains(response, "Чужая заметка")
            import re

            count = len(re.findall(r"Заметка автора \d+", response.content.decode()))
            self.assertEqual(count, settings.NOTES_COUNT_ON_HOME_PAGE + 1)

    def test_notes_order(self):
        """Заметки отсортированы по убыванию даты (свежие сверху)."""
        self.client.force_login(self.author)
        response = self.client.get(self.list_url)
        if "object_list" in response.context:
            object_list = response.context["object_list"]
            dates = [note.created for note in object_list]
            sorted_dates = sorted(dates, reverse=True)
            self.assertEqual(dates, sorted_dates)
        else:
            content = response.content.decode()
            positions = {}
            total = settings.NOTES_COUNT_ON_HOME_PAGE + 1
            for index in range(total):
                title = f"Заметка автора {index}"
                pos = content.find(title)
                if pos != -1:
                    positions[index] = pos
            sorted_indices = sorted(positions.keys())
            for i in range(len(sorted_indices) - 1):
                self.assertLess(
                    positions[sorted_indices[i]],
                    positions[sorted_indices[i + 1]]
                )

    def test_notes_filtering_by_author(self):
        """В список попадают только заметки текущего пользователя."""
        self.client.force_login(self.author)
        response = self.client.get(self.list_url)
        self.assertNotContains(response, "Чужая заметка")
        if "object_list" in response.context:
            object_list = response.context["object_list"]
            for note in object_list:
                self.assertEqual(note.author, self.author)


class TestDetailPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username="Автор")
        cls.reader = User.objects.create(username="Читатель")
        cls.note = Note.objects.create(
            title="Тестовая заметка",
            text="Содержимое заметки",
            slug="test-detail-note",
            author=cls.author,
            created=timezone.now(),
        )
        cls.detail_url = reverse("notes:detail", args=(cls.note.slug,))

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
        login_url = reverse("users:login")
        expected_redirect = f"{login_url}?next={self.detail_url}"
        self.assertRedirects(response, expected_redirect)


class TestCreateAndEditPages(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username="Автор")
        cls.note = Note.objects.create(
            title="Заметка для редактирования",
            text="Текст",
            slug="edit-note",
            author=cls.author,
        )

    def test_create_page_has_form(self):
        self.client.force_login(self.author)
        url = reverse("notes:add")
        response = self.client.get(url)
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], NoteForm)

    def test_edit_page_has_form(self):
        self.client.force_login(self.author)
        url = reverse("notes:edit", args=(self.note.slug,))
        response = self.client.get(url)
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], NoteForm)
        self.assertEqual(response.context["form"].instance, self.note)

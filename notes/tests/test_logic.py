from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from notes.models import Note

User = get_user_model()


class TestNoteCreation(TestCase):
    NOTE_TITLE = 'Заголовок заметки'
    NOTE_TEXT = 'Текст заметки'
    NOTE_SLUG = 'test-slug'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='Автор заметки')
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        cls.url = reverse('notes:add')
        cls.form_data = {
            'title': cls.NOTE_TITLE,
            'text': cls.NOTE_TEXT,
            'slug': cls.NOTE_SLUG,
        }

    def test_anonymous_user_cant_create_note(self):
        self.client.post(self.url, data=self.form_data)
        self.assertEqual(Note.objects.count(), 0)

    def test_authorized_user_can_create_note(self):
        response = self.auth_client.post(self.url, data=self.form_data)
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 1)
        note = Note.objects.get()
        self.assertEqual(note.title, self.NOTE_TITLE)
        self.assertEqual(note.text, self.NOTE_TEXT)
        self.assertEqual(note.slug, self.NOTE_SLUG)
        self.assertEqual(note.author, self.user)

    def test_cannot_create_note_with_duplicate_slug(self):
        self.auth_client.post(self.url, data=self.form_data)
        self.assertEqual(Note.objects.count(), 1)
        response = self.auth_client.post(self.url, data=self.form_data)
        self.assertEqual(Note.objects.count(), 1)
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertIn('slug', form.errors)


    def test_slug_auto_generation(self):
        """Если slug не указан, генерируется автоматически из заголовка."""
        data = {
            'title': 'Заголовок для авто slug',
            'text': 'Текст заметки',
        }
        response = self.auth_client.post(self.url, data=data)
        self.assertRedirects(response, reverse('notes:success'))
        
        note = Note.objects.get()
        # Ожидаем именно тот slug, который сгенерировало ваше приложение
        self.assertEqual(note.slug, 'zagolovok-dlya-avto-slug')
        self.assertEqual(note.title, 'Заголовок для авто slug')


class TestNoteEditDelete(TestCase):
    OLD_TEXT = 'Старый текст заметки'
    NEW_TEXT = 'Новый текст заметки'
    NEW_TITLE = 'Новый заголовок'

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор')
        cls.reader = User.objects.create(username='Читатель')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

        cls.note = Note.objects.create(
            title='Исходный заголовок',
            text=cls.OLD_TEXT,
            slug='test-slug-edit',
            author=cls.author
        )
        cls.edit_url = reverse('notes:edit', args=(cls.note.slug,))
        cls.delete_url = reverse('notes:delete', args=(cls.note.slug,))
        cls.form_data = {
            'title': cls.NEW_TITLE,
            'text': cls.NEW_TEXT,
            'slug': cls.note.slug,
        }

    def test_author_can_edit_note(self):
        response = self.author_client.post(self.edit_url, data=self.form_data)
        self.assertRedirects(response, reverse('notes:success'))
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, self.NEW_TITLE)
        self.assertEqual(self.note.text, self.NEW_TEXT)

    def test_author_can_delete_note(self):
        response = self.author_client.delete(self.delete_url)
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 0)

    def test_user_cant_edit_others_note(self):
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.note.refresh_from_db()
        self.assertEqual(self.note.text, self.OLD_TEXT)

    def test_user_cant_delete_others_note(self):
        response = self.reader_client.delete(self.delete_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Note.objects.count(), 1)

    def test_cannot_edit_slug_to_existing_duplicate(self):
        Note.objects.create(
            title='Другая заметка',
            text='Текст',
            slug='occupied-slug',
            author=self.author,
        )
        self.form_data['slug'] = 'occupied-slug'
        response = self.author_client.post(self.edit_url, data=self.form_data)
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertIn('slug', form.errors)
        self.note.refresh_from_db()
        self.assertNotEqual(self.note.slug, 'occupied-slug')

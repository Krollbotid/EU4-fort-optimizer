import json
import os
import sys

class I18n:
    def __init__(self, lang_dir="localization"):
        self.lang_dir = lang_dir
        self._lang = None
        self._translations = {}
        # Пытаемся загрузить русский по умолчанию
        self.set_language('en')
    
    def _load_language(self, lang):
        filepath = os.path.join(self.lang_dir, f"{lang}.json")
        if not os.path.exists(filepath):
            print(f"Ошибка: файл локализации {filepath} не найден. Программа завершает работу.")
            sys.exit(1)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке файла локализации {filepath}: {e}")
            sys.exit(1)
    
    def set_language(self, lang):
        if lang not in ['ru', 'en']:
            lang = 'ru'
        self._lang = lang
        self._load_language(lang)
    
    def get(self, key, **kwargs):
        text = self._translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                # если форматирование не удалось, возвращаем как есть
                pass
        return text

i18n = I18n()
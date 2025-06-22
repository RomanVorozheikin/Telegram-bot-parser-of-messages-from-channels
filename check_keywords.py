import re
import asyncio
from database import Database

async def check_keywords_in_message(message_text, keywords, stopwords):
    """Проверяет наличие ключевых слов в сообщении и отсутствие стоп-слов"""
    if not message_text:
        return False
        
    # Если сообщение содержит только тип медиа в квадратных скобках (например, [фото]),
    # то пропускаем проверку на ключевые слова
    if re.match(r'^\[\w+\]$', message_text):
        print(f"Пропускаем проверку ключевых слов для медиа без текста: {message_text}")
        return False
    
    # Если сообщение содержит медиа и текст, удаляем префикс типа медиа для проверки
    if re.match(r'^\[\w+\]\s+.+', message_text):
        # Извлекаем только текстовую часть для проверки ключевых слов
        clean_text = re.sub(r'^\[\w+\]\s+', '', message_text)
        print(f"Проверяем только текстовую часть сообщения: {clean_text}")
        message_lower = clean_text.lower()
    else:
        message_lower = message_text.lower()
    
    print(f"Текст для проверки (в нижнем регистре): {message_lower}")
    
    # Проверка на стоп-слова
    for stopword in stopwords:
        if stopword.lower() in message_lower:
            print(f"Найдено стоп-слово: {stopword}")
            return False
    
    # Проверка на ключевые слова
    for keyword in keywords:
        # Проверяем составные ключевые слова (с символом +)
        if "+" in keyword:
            parts = keyword.lower().split("+")
            all_parts_found = True
            for part in parts:
                if part.strip() not in message_lower:
                    all_parts_found = False
                    break
            if all_parts_found:
                print(f"Найдено составное ключевое слово: {keyword}")
                return True
        elif keyword.lower() in message_lower:
            print(f"Найдено ключевое слово: {keyword}")
            return True
    
    print("Ключевые слова не найдены")
    return False

async def main():
    # Пример текста из логов
    message_text = """🇺🇸🇷🇺🇮🇷❗️Если США ударят по Ирану, в Москве сочтут этот шаг неверным, потому что он приведёт к существенной эскаллации ситуации, заявил RT Дмитрий Песков.

Пресс-секретарь президента РФ добавил, что такого развития событий не хотелось бы."""
    
    # Подключаемся к базе данных
    db = Database()
    await db.connect()
    
    # Получаем ключевые слова и стоп-слова из базы данных
    keywords = await db.get_keywords()
    stopwords = await db.get_stopwords()
    
    print(f"Ключевые слова: {keywords}")
    print(f"Стоп-слова: {stopwords}")
    
    # Проверяем наличие ключевых слов в сообщении
    result = await check_keywords_in_message(message_text, keywords, stopwords)
    print(f"Результат проверки: {result}")
    
    # Проверяем отдельно для слова 'США'
    if 'сша' in message_text.lower():
        print("Слово 'США' найдено в тексте напрямую")
    else:
        print("Слово 'США' НЕ найдено в тексте напрямую")
    
    # Проверяем наличие эмодзи и спецсимволов
    clean_text = re.sub(r'[^\w\s]', '', message_text)
    print(f"Текст без спецсимволов: {clean_text}")
    
    # Закрываем соединение с базой данных
    await db.close()

if __name__ == "__main__":
    asyncio.run(main()) 
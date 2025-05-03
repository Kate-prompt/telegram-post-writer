import os
import openai
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Инициализация приложения FastAPI
app = FastAPI()

# Получение ключей из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
currentsapi_key = os.getenv("CURRENTS_API_KEY")

# Проверка наличия ключей
if not openai.api_key or not currentsapi_key:
    raise ValueError("Требуются переменные окружения: OPENAI_API_KEY и CURRENTS_API_KEY")

# Pydantic-модель для тела POST-запроса
class Topic(BaseModel):
    topic: str

# Функция получения новостей по теме с Currents API
def get_recent_news(topic: str):
    url = "https://api.currentsapi.services/v1/latest-news"
    params = {
        "language": "en",
        "keywords": topic,
        "apiKey": currentsapi_key
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении новостей: {response.text}")

    news_data = response.json().get("news", [])
    if not news_data:
        return "Свежих новостей не найдено."
    
    return "\n".join([article["title"] for article in news_data[:5]])

# Основная функция генерации контента
def generate_content(topic: str):
    news_context = get_recent_news(topic)

    try:
        # Генерация заголовка
        title_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"Придумай привлекательный и точный заголовок для статьи на тему '{topic}', учитывая эти новости:\n{news_context}"
            }],
            max_tokens=60,
            temperature=0.5,
            stop=["\n"]
        )
        title = title_response.choices[0].message.content.strip()

        # Генерация мета-описания
        meta_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"Напиши мета-описание для статьи с заголовком '{title}'. Оно должно быть информативным и содержать ключевые слова."
            }],
            max_tokens=100,
            temperature=0.5,
            stop=["."]
        )
        meta_description = meta_response.choices[0].message.content.strip()

        # Генерация основного поста
        post_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": (
                    f"Напиши развёрнутый пост на тему '{topic}', используя последние новости:\n{news_context}\n"
                    "Статья должна быть логично структурирована, содержать не менее 1500 символов, включать подзаголовки, "
                    "анализ трендов, примеры, и быть написана понятным языком."
                )
            }],
            max_tokens=1500,
            temperature=0.5,
            presence_penalty=0.6,
            frequency_penalty=0.6
        )
        post_content = post_response.choices[0].message.content.strip()

        return {
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации поста: {str(e)}")

# Эндпоинт генерации поста
@app.post("/generate-post")
async def generate_post_api(topic: Topic):
    return generate_content(topic.topic)

# Эндпоинт проверки работоспособности
@app.get("/")
async def root():
    return {"message": "Сервис работает"}

# Эндпоинт "пульс сервиса"
@app.get("/heartbeat")
async def heartbeat():
    return {"status": "OK"}

# Локальный запуск (если не через Koyeb)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

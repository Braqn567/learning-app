import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()  # чете ключа от файла .env

# Името на AI модела. Ако някога излезе грешка "not found", сменяме само този ред.
MODEL = "gemini-3.5-flash-lite"


# Така изглежда един въпрос. AI е длъжен да върне точно тази форма.
class Question(BaseModel):
    topic: str          # кратка тема на въпроса (за да знаем върху какво да наблегнеш)
    question: str       # текстът на въпроса
    options: list[str]  # 4 възможни отговора
    correct_index: int  # кой е верният: 0, 1, 2 или 3
    explanation: str    # кратко обяснение защо е верен


def make_test(data: bytes, mime_type: str, count: int = 5) -> list[Question]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = (
        f"Ти си учител. Направи тест с {count} въпроса върху приложения материал. "
        "Използвай САМО информацията от материала, без външни знания. "
        "Всеки въпрос има точно 4 възможни отговора и само един верен. "
        "Групирай въпросите в 3-5 общи теми и за всеки въпрос посочи темата му (1-3 думи). "
        "Една и съща тема винаги се пише с едно и също име. За всеки въпрос дай и кратко обяснение. "
        "Пиши на езика на материала. "
        "Ако материалът не съдържа учебно съдържание, върни празен списък."
    )

    # Текстовите файлове ги пращаме като текст, а PDF и снимките - като файл
    if mime_type == "text/plain":
        material = data.decode("utf-8", errors="ignore")
    else:
        material = types.Part.from_bytes(data=data, mime_type=mime_type)

    response = client.models.generate_content(
        model=MODEL,
        contents=[material, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[Question],
        ),
    )
    return response.parsed
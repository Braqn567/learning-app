import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()  # чете ключа от файла .env

# Името на AI модела. Ако някога излезе грешка "not found", сменяме само този ред.
MODEL = "gemini-3.5-flash-lite"

# Какво казваме на AI за всяка трудност
LEVELS = {
    "Лесен": "Въпросите да са лесни: основни факти и определения, директно от текста.",
    "Среден": "Въпросите да са със средна трудност: проверяват разбиране, а не само наизустяване.",
    "Труден": "Въпросите да са трудни: изискват анализ и връзки между идеи, а грешните отговори да са правдоподобни.",
}


# Така изглежда един въпрос. AI е длъжен да върне точно тази форма.
class Question(BaseModel):
    topic: str                 # кратка тема на въпроса
    question: str              # текстът на въпроса
    options: list[str]         # възможните отговори
    correct_indices: list[int] # индексите (от 0) на ВСИЧКИ верни отговори
    explanation: str           # кратко обяснение защо са верни


def make_test(
    data: bytes,
    mime_type: str,
    count: int = 5,
    difficulty: str = "Среден",
    multi: bool = False,
) -> list[Question]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    if multi:
        answers_rule = (
            "Всеки въпрос има точно 5 възможни отговора, а верните са от 1 до 4 "
            "(различен брой за различните въпроси). В correct_indices изброй "
            "индексите на ВСИЧКИ верни отговори, като броенето започва от 0. "
        )
    else:
        answers_rule = (
            "Всеки въпрос има точно 4 възможни отговора и само един верен. "
            "В correct_indices сложи само индекса му, като броенето започва от 0. "
        )

    prompt = (
        f"Ти си учител. Направи тест с {count} въпроса върху приложения материал. "
        "Използвай САМО информацията от материала, без външни знания. "
        f"{LEVELS[difficulty]} "
        f"{answers_rule}"
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

    # Проверка: махаме невалидни индекси и въпроси без верен отговор,
    # за да не се счупи приложението, ако AI сгреши
    questions = response.parsed or []
    cleaned = []
    for q in questions:
        q.correct_indices = sorted({j for j in q.correct_indices if 0 <= j < len(q.options)})
        if q.correct_indices:
            cleaned.append(q)
    return cleaned
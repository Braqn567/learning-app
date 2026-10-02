import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from ai import make_test
from database import count_results, create_user, init_db, list_results, save_result, verify_user
from ui import (
    apply_style,
    fmt,
    grade_for,
    highlights_html,
    page_title,
    question_head,
    show_result,
    step_title,
)

ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.png"

st.set_page_config(
    page_title="Quizify",
    page_icon=str(ICON_PATH) if ICON_PATH.exists() else "📚",
    layout="wide",
)
apply_style()
init_db()  # създава базата и таблиците, ако ги няма

# Начини за даване на точки
RULE_STRICT = "Като на изпит: всичко или нищо"
RULE_PARTIAL = "Частично (минус за грешни)"

# Колко точки носи един въпрос
VALUE_ONE = "1 точка за въпрос"
VALUE_BY_CORRECT = "Колкото са верните отговори (напр. 3 верни = 3 точки)"


def score_question(selected, correct, rule):
    """Връща число от 0 до 1: каква част от въпроса е спечелена.
    selected = множество от отбелязаните отговори, correct = множество от верните."""
    if rule == RULE_STRICT:
        return 1.0 if selected == correct else 0.0
    right = len(selected & correct)  # колко верни е отбелязал
    wrong = len(selected - correct)  # колко грешни е отбелязал
    return max(0.0, (right - wrong) / len(correct))


def page_new_test():
    page_title(
        "Нов тест",
        "Качи снимка или документ от учебния си материал. AI прави въпроси само от него.",
    )

    # ---------- Стъпка 1: материал ----------
    step_title(1, "Добави материал")
    режим = st.radio(
        "Как искаш да го добавиш?",
        ["Качи файл", "Снимай с камерата"],
        horizontal=True,
        label_visibility="collapsed",
    )

    файл = None
    if режим == "Качи файл":
        файл = st.file_uploader(
            "Избери PDF, текст или снимка",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
        )
    else:
        файл = st.camera_input("Снимай страницата")

    # ---------- Стъпка 2: настройки ----------
    if файл is not None:
        if файл.type.startswith("image"):
            st.image(файл, caption="Твоят материал")
        else:
            st.success("Документът е получен.")

        step_title(2, "Настрой теста")

        вид = st.radio(
            "Вид на въпросите",
            ["Един верен отговор", "Няколко верни отговора (като на изпит)"],
        )
        multi = вид.startswith("Няколко")

        правило = RULE_STRICT
        стойност = VALUE_ONE
        if multi:
            правило = st.radio("Как се дават точките?", [RULE_STRICT, RULE_PARTIAL])
            if правило == RULE_STRICT:
                st.caption(
                    "Ако сгрешиш каквото и да е в един въпрос (отбележиш грешен отговор "
                    "или пропуснеш верен), губиш всичките му точки."
                )
            else:
                st.caption(
                    "Частично: (верни избрани − грешни избрани) ÷ брой верни отговори, "
                    "не по-малко от 0. Пример: 4 верни, избираш 3 верни = 0,75 от точките."
                )
            стойност = st.radio("Колко точки носи един въпрос?", [VALUE_ONE, VALUE_BY_CORRECT])

        col1, col2 = st.columns(2)
        with col1:
            брой = st.slider("Брой въпроси", 5, 15, 10)
        with col2:
            трудност = st.select_slider(
                "Трудност", options=["Лесен", "Среден", "Труден"], value="Среден"
            )

        if st.button("Направи тест", type="primary"):
            with st.spinner("AI чете материала и прави въпроси..."):
                try:
                    test = make_test(файл.getvalue(), файл.type, брой, трудност, multi)
                    # Изтриваме отговорите от стария тест, за да започнем начисто
                    for key in list(st.session_state.keys()):
                        if key.startswith("answer_"):
                            del st.session_state[key]
                    st.session_state["test"] = test
                    st.session_state["settings"] = {
                        "multi": multi,
                        "rule": правило,
                        "value": стойност,
                    }
                    st.session_state["started_at"] = datetime.now()  # от тук тръгва таймерът
                    st.session_state.pop("result", None)  # махаме стария резултат
                except Exception as e:
                    if "429" in str(e):
                        st.error("Достигнат е лимитът на безплатните заявки. Изчакай 1-2 минути и опитай пак.")
                    else:
                        st.error(f"Тестът не се създаде. Причина: {e}")

    # ---------- Стъпка 3: решаване ----------
    if "test" in st.session_state:
        test = st.session_state["test"]
        settings = st.session_state["settings"]
        test_multi = settings["multi"]
        test_rule = settings.get("rule", RULE_STRICT)
        test_value = settings.get("value", VALUE_ONE)

        if not test:
            st.warning("От този материал не се получи тест. Опитай с друг, в който има учебен текст.")
            return

        step_title(3, "Реши теста")

        with st.form("quiz"):
            for i, q in enumerate(test):
                with st.container(key=f"qcard_{i}"):  # всеки въпрос е в собствена карта
                    question_head(
                        i + 1,
                        q.question,
                        q.topic,
                        "Избери всички верни отговори" if test_multi else "Избери един отговор",
                    )
                    if test_multi:
                        for j, option in enumerate(q.options):
                            st.checkbox(option, key=f"answer_{i}_{j}")
                    else:
                        st.radio(
                            "Отговор",
                            options=list(range(len(q.options))),
                            format_func=lambda j, q=q: q.options[j],
                            index=None,
                            key=f"answer_{i}",
                            label_visibility="collapsed",
                        )
            submitted = st.form_submit_button("Провери отговорите", type="primary")

        if submitted:
            finished_at = datetime.now()
            started_at = st.session_state.get("started_at", finished_at)

            total_points = 0.0  # колко точки е спечелил
            total_max = 0.0     # колко точки е можел да спечели
            topic_stats = {}    # за всяка тема: [спечелени точки, възможни точки]
            feedback = []       # съобщенията за всеки въпрос

            for i, q in enumerate(test):
                correct = set(q.correct_indices)

                # Колко точки носи този въпрос
                if test_multi and test_value == VALUE_BY_CORRECT:
                    max_points = len(correct)
                else:
                    max_points = 1

                # Събираме какво е отбелязал потребителят
                if test_multi:
                    selected = {
                        j for j in range(len(q.options))
                        if st.session_state.get(f"answer_{i}_{j}")
                    }
                else:
                    chosen = st.session_state.get(f"answer_{i}")
                    selected = set() if chosen is None else {chosen}

                points = score_question(selected, correct, test_rule) * max_points
                total_points += points
                total_max += max_points

                topic = q.topic.strip().capitalize()
                stats = topic_stats.setdefault(topic, [0.0, 0.0])
                stats[0] += points
                stats[1] += max_points

                correct_text = "; ".join(q.options[j] for j in sorted(correct))
                chosen_text = "; ".join(q.options[j] for j in sorted(selected))

                if not selected:
                    feedback.append(("warning", f"{i + 1}. Няма отговор (0 от {fmt(max_points)} т.). Верни: {correct_text}. {q.explanation}"))
                elif points == max_points:
                    feedback.append(("success", f"{i + 1}. Напълно вярно! ({fmt(max_points)} от {fmt(max_points)} т.) {q.explanation}"))
                elif points > 0:
                    feedback.append(("info", f"{i + 1}. Частично ({fmt(points)} от {fmt(max_points)} т.). Ти избра: {chosen_text}. Верни: {correct_text}. {q.explanation}"))
                else:
                    feedback.append(("error", f"{i + 1}. Грешно (0 от {fmt(max_points)} т.). Ти избра: {chosen_text}. Верни: {correct_text}. {q.explanation}"))

            percent = round(total_points / total_max * 100)

            # Всичко за един решен тест е в един речник
            result = {
                "percent": percent,
                "points": total_points,
                "max_points": total_max,
                "questions": len(test),
                "topics": topic_stats,
                "feedback": feedback,
                "started": started_at.strftime("%H:%M"),
                "finished": finished_at.strftime("%H:%M"),
                "duration_sec": int((finished_at - started_at).total_seconds()),
                "date": finished_at.strftime("%d.%m.%Y %H:%M"),
            }
            st.session_state["result"] = result

            # Ако е влязъл в профила си, запазваме резултата в базата
            user = st.session_state.get("user")
            if user:
                save_result(user["id"], result)
                st.toast("Резултатът е запазен в профила ти")

            if percent >= 90:
                st.balloons()

        if "result" in st.session_state:
            show_result(st.session_state["result"])
            if not st.session_state.get("user"):
                st.info("Влез в профила си (меню → Профил), за да се запазват резултатите ти.")


def page_history():
    page_title("История", "Всички решени тестове и как се променя успеваемостта ти.")
    user = st.session_state.get("user")

    if not user:
        st.info("Влез в профила си (меню → Профил), за да виждаш историята на тестовете си.")
        return

    results = list_results(user["id"])  # най-новите първи
    if not results:
        st.info("Още нямаш запазени тестове. Реши един в „Нов тест“ и резултатът ще се появи тук.")
        return

    percents = [r["percent"] for r in results]

    # ----- Обобщение -----
    c1, c2, c3 = st.columns(3)
    c1.metric("Тестове", len(results))
    c2.metric("Средна успеваемост", f"{round(sum(percents) / len(percents))}%")
    c3.metric("Най-добър резултат", f"{max(percents)}%")

    # ----- Графика на прогреса (от най-стария към най-новия) -----
    if len(results) >= 2:
        step_title(1, "Прогрес")
        oldest_first = list(reversed(percents))
        chart_data = pd.DataFrame(
            {
                "Тест №": list(range(1, len(oldest_first) + 1)),
                "Успеваемост %": oldest_first,
            }
        ).set_index("Тест №")
        st.line_chart(chart_data, color="#087F6C")

    # ----- Най-слаби теми от всички тестове -----
    topic_totals = {}  # за всяка тема: [точки, възможни точки]
    for r in results:
        for topic, (pts, mx) in r["data"]["topics"].items():
            totals = topic_totals.setdefault(topic, [0.0, 0.0])
            totals[0] += pts
            totals[1] += mx
    ranked = sorted(
        (round(pts / mx * 100), topic)
        for topic, (pts, mx) in topic_totals.items()
        if mx > 0
    )
    weak = [(pct, topic) for pct, topic in ranked if pct < 70][:5]
    st.subheader("Най-слаби теми досега")
    if weak:
        st.markdown(highlights_html(weak), unsafe_allow_html=True)
    else:
        st.success("Всички теми са над 70%. Продължавай така.")

    # ----- Списък с тестовете -----
    st.subheader("Твоите тестове")
    labels = [
        f"{r['data'].get('date', r['created_at'])}, {r['percent']}%, {grade_for(r['percent'])[0]}"
        for r in results
    ]
    choice = st.selectbox(
        "Отвори тест",
        list(range(len(results))),
        format_func=lambda i: labels[i],
    )
    show_result(results[choice]["data"])


def page_profile():
    user = st.session_state.get("user")

    # Ако вече е влязъл - показваме профила
    if user:
        page_title("Профил")
        with st.container(key="card_profile"):
            st.markdown(f"### Здравей, {user['username']}")
            st.write(f"Запазени тестове: **{count_results(user['id'])}**")
            if st.button("Изход"):
                for key in ("user", "test", "result", "settings"):
                    st.session_state.pop(key, None)
                st.rerun()
        return

    # Иначе - вход или регистрация
    page_title("Влез в Quizify", "Профилът запазва резултатите ти и показва как напредваш.")
    with st.container(key="card_auth"):
        tab_login, tab_register = st.tabs(["Вход", "Регистрация"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Потребителско име")
                password = st.text_input("Парола", type="password")
                login_clicked = st.form_submit_button("Влез", type="primary")
            if login_clicked:
                found = verify_user(username, password)
                if found:
                    st.session_state["user"] = found
                    st.rerun()
                else:
                    st.error("Грешно потребителско име или парола.")

        with tab_register:
            with st.form("register_form"):
                new_name = st.text_input("Избери потребителско име")
                new_pass = st.text_input("Парола (поне 8 символа)", type="password")
                new_pass2 = st.text_input("Повтори паролата", type="password")
                register_clicked = st.form_submit_button("Създай профил", type="primary")
            if register_clicked:
                if not re.fullmatch(r"\w{3,30}", new_name.strip()):
                    st.error("Името е от 3 до 30 символа: букви, цифри или _ (без интервали).")
                elif len(new_pass) < 8:
                    st.error("Паролата трябва да е поне 8 символа.")
                elif new_pass != new_pass2:
                    st.error("Двете пароли не съвпадат.")
                elif create_user(new_name, new_pass):
                    st.session_state["user"] = verify_user(new_name, new_pass)
                    st.rerun()
                else:
                    st.error("Това име вече е заето. Избери друго.")


# ---------- Меню отляво ----------
with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=84)
    st.markdown(
        '<div class="brand">Quizify</div><div class="brand-sub">Тест от твоите записки</div>',
        unsafe_allow_html=True,
    )
    страница = st.radio(
        "Меню",
        ["Нов тест", "История", "Профил"],
        label_visibility="collapsed",
    )
    st.divider()
    current_user = st.session_state.get("user")
    if current_user:
        st.caption(f"Влязъл като **{current_user['username']}**")
    else:
        st.caption("Гост. Резултатите не се запазват.")

if страница == "Нов тест":
    page_new_test()
elif страница == "История":
    page_history()
else:
    page_profile()
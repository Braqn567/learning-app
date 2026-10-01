import streamlit as st
from ai import make_test

st.set_page_config(page_title="Помощник за учене", page_icon="📚")

# Малко CSS за по-красив вид
st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #6C63FF 0%, #8E7CFF 100%);
        color: white;
        padding: 1.6rem 1.2rem;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 1.2rem;
    }
    .hero h1 { color: white; margin: 0; font-size: 1.9rem; padding: 0; }
    .hero p { margin: 0.4rem 0 0 0; opacity: 0.92; }
    button { border-radius: 12px !important; }
    div[data-testid="stMetric"] {
        background: #F3F1FF;
        padding: 0.8rem 1rem;
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Начини за даване на точки
RULE_STRICT = "Като на изпит: всичко или нищо"
RULE_PARTIAL = "Частично (минус за грешни)"

# Колко точки носи един въпрос
VALUE_ONE = "1 точка за въпрос"
VALUE_BY_CORRECT = "Колкото са верните отговори (напр. 3 верни = 3 точки)"


def fmt(x):
    """Красиво число: 3.0 става 3, а 0.75 си остава 0.75."""
    return f"{round(x, 2):g}"


def topic_icon(percent):
    """Цветно кръгче според успеха по темата."""
    if percent >= 70:
        return "🟢"
    if percent >= 40:
        return "🟡"
    return "🔴"


def score_question(selected, correct, rule):
    """Връща число от 0 до 1: каква част от въпроса е спечелена.
    selected = множество от отбелязаните отговори, correct = множество от верните."""
    if rule == RULE_STRICT:
        return 1.0 if selected == correct else 0.0
    right = len(selected & correct)  # колко верни е отбелязал
    wrong = len(selected - correct)  # колко грешни е отбелязал
    return max(0.0, (right - wrong) / len(correct))


# ---------- Горна част ----------
st.markdown(
    '<div class="hero"><h1>📚 Помощник за учене</h1>'
    "<p>Качи материал, AI прави тест, а ти разбираш какво да научиш.</p></div>",
    unsafe_allow_html=True,
)

# ---------- Стъпка 1: материал ----------
st.subheader("1️⃣ Добави материал")
режим = st.radio(
    "Как искаш да го добавиш?",
    ["📁 Качи файл", "📷 Снимай с камерата"],
    horizontal=True,
)

файл = None
if режим == "📁 Качи файл":
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
        st.success("✅ Документът е получен.")

    st.subheader("2️⃣ Настрой теста")

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

    if st.button("✨ Направи тест", type="primary"):
        with st.spinner("AI чете материала и прави въпроси..."):
            try:
                test = make_test(файл.getvalue(), файл.type, брой, трудност, multi)
                # Изтриваме отговорите от стария тест, за да започнем начисто
                for key in list(st.session_state.keys()):
                    if key.startswith("answer_"):
                        del st.session_state[key]
                st.session_state["test"] = test
                # Запомняме настройките, с които е направен този тест
                st.session_state["settings"] = {
                    "multi": multi,
                    "rule": правило,
                    "value": стойност,
                }
            except Exception as e:
                if "429" in str(e):
                    st.error("Достигнат е лимитът на безплатните заявки. Изчакай 1-2 минути и опитай пак.")
                else:
                    st.error(f"Нещо се обърка: {e}")

# ---------- Стъпка 3: решаване ----------
if "test" in st.session_state:
    test = st.session_state["test"]
    settings = st.session_state["settings"]
    test_multi = settings["multi"]
    test_rule = settings.get("rule", RULE_STRICT)
    test_value = settings.get("value", VALUE_ONE)

    if not test:
        st.warning("От този материал не се получи тест. Опитай с друг.")
    else:
        st.subheader("3️⃣ Решавай")

        with st.form("quiz"):
            for i, q in enumerate(test):
                with st.container(border=True):  # всеки въпрос е в собствена карта
                    st.markdown(f"**{i + 1}. {q.question}**")
                    if test_multi:
                        st.caption(f"Тема: {q.topic} · Може да има повече от един верен отговор")
                        for j, option in enumerate(q.options):
                            st.checkbox(option, key=f"answer_{i}_{j}")
                    else:
                        st.caption(f"Тема: {q.topic}")
                        st.radio(
                            "Отговор",
                            options=list(range(len(q.options))),
                            format_func=lambda j, q=q: q.options[j],
                            index=None,
                            key=f"answer_{i}",
                            label_visibility="collapsed",
                        )
            submitted = st.form_submit_button("✅ Провери отговорите", type="primary")

        if submitted:
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

            # ----- Резултат -----
            percent = round(total_points / total_max * 100)
            st.divider()
            st.header("📊 Резултат")

            c1, c2, c3 = st.columns(3)
            c1.metric("Успеваемост", f"{percent}%")
            c2.metric("Точки", f"{fmt(total_points)} от {fmt(total_max)}")
            c3.metric("Въпроси", len(test))
            st.progress(percent / 100)

            if percent >= 90:
                st.balloons()

            # ----- По теми -----
            st.subheader("По теми")
            weak_topics = []
            for topic, (pts_sum, pts_max) in topic_stats.items():
                topic_percent = round(pts_sum / pts_max * 100)
                st.write(f"{topic_icon(topic_percent)} **{topic}**: {topic_percent}% ({fmt(pts_sum)} от {fmt(pts_max)} т.)")
                st.progress(topic_percent / 100)
                if topic_percent < 70:
                    weak_topics.append((topic_percent, topic))

            # ----- На какво да наблегнеш -----
            st.subheader("🎯 На какво да наблегнеш")
            if weak_topics:
                weak_topics.sort()  # най-слабите първи
                for topic_percent, topic in weak_topics:
                    st.write(f"- **{topic}** ({topic_percent}%)")
            else:
                st.success("Браво! Всички теми са над 70%. Можеш да качиш нов материал.")

            # ----- Подробно по въпроси -----
            with st.expander("🔍 Прегледай всички отговори"):
                for kind, text in feedback:
                    if kind == "success":
                        st.success(text)
                    elif kind == "info":
                        st.info(text)
                    elif kind == "warning":
                        st.warning(text)
                    else:
                        st.error(text)
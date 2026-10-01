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


def topic_icon(percent):
    """Цветно кръгче според успеха по темата."""
    if percent >= 70:
        return "🟢"
    if percent >= 40:
        return "🟡"
    return "🔴"


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
                test = make_test(файл.getvalue(), файл.type, брой, трудност)
                # Изтриваме отговорите от стария тест, за да започнем начисто
                for key in list(st.session_state.keys()):
                    if key.startswith("answer_"):
                        del st.session_state[key]
                st.session_state["test"] = test
            except Exception as e:
                if "429" in str(e):
                    st.error("Достигнат е лимитът на безплатните заявки. Изчакай 1-2 минути и опитай пак.")
                else:
                    st.error(f"Нещо се обърка: {e}")

# ---------- Стъпка 3: решаване ----------
if "test" in st.session_state:
    test = st.session_state["test"]

    if not test:
        st.warning("От този материал не се получи тест. Опитай с друг.")
    else:
        st.subheader("3️⃣ Решавай")

        with st.form("quiz"):
            for i, q in enumerate(test):
                with st.container(border=True):  # всеки въпрос е в собствена карта
                    st.markdown(f"**{i + 1}. {q.question}**")
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
            correct_count = 0
            topic_stats = {}  # за всяка тема: [колко са верни, колко са общо]
            feedback = []     # съобщенията за всеки въпрос

            for i, q in enumerate(test):
                chosen = st.session_state.get(f"answer_{i}")
                right_text = q.options[q.correct_index]

                topic = q.topic.strip().capitalize()
                stats = topic_stats.setdefault(topic, [0, 0])
                stats[1] += 1

                if chosen == q.correct_index:
                    correct_count += 1
                    stats[0] += 1
                    feedback.append(("success", f"{i + 1}. Верно! {q.explanation}"))
                elif chosen is None:
                    feedback.append(("warning", f"{i + 1}. Няма отговор. Верният е: {right_text}. {q.explanation}"))
                else:
                    feedback.append(("error", f"{i + 1}. Грешно. Верният е: {right_text}. {q.explanation}"))

            # ----- Резултат -----
            percent = round(correct_count / len(test) * 100)
            st.divider()
            st.header("📊 Резултат")

            c1, c2, c3 = st.columns(3)
            c1.metric("Успеваемост", f"{percent}%")
            c2.metric("Верни", correct_count)
            c3.metric("Въпроси", len(test))
            st.progress(percent / 100)

            if percent >= 90:
                st.balloons()

            # ----- По теми -----
            st.subheader("По теми")
            weak_topics = []
            for topic, (ok, total) in topic_stats.items():
                topic_percent = round(ok / total * 100)
                st.write(f"{topic_icon(topic_percent)} **{topic}**: {topic_percent}% ({ok} от {total})")
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
                    elif kind == "warning":
                        st.warning(text)
                    else:
                        st.error(text)
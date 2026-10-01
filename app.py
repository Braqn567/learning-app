import streamlit as st
from ai import make_test
st.set_page_config(page_title="Помощник за учене", page_icon="📚")

st.title("📚 Помощник за учене")
st.write("Качи документ или снимка от учебния си материал и ще получиш тест.")

режим = st.radio("Как искаш да добавиш материала?", ["Качи файл", "Снимай с камерата"])

файл = None
if режим == "Качи файл":
    файл = st.file_uploader(
        "Избери документ или снимка",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
    )
else:
    файл = st.camera_input("Снимай страницата")

if файл is not None:
    if файл.type.startswith("image"):
        st.image(файл, caption="Твоят материал")
    else:
        st.success("Документът е получен.")

    брой = st.slider("Колко въпроса да има в теста?", 5, 15, 10)

    if st.button("✨ Направи тест"):
        with st.spinner("AI чете материала и прави въпроси..."):
            try:
                test = make_test(файл.getvalue(), файл.type, брой)
                for key in list(st.session_state.keys()):
                    if key.startswith("answer_"):
                        del st.session_state[key]
                st.session_state["test"] = test
            except Exception as e:
                if "429" in str(e):
                    st.error("Достигнат е лимитът на безплатните заявки. Изчакай 1-2 минути и опитай пак.")
                else:
                    st.error(f"Нещо се обърка: {e}")

# Показваме теста за решаване
if "test" in st.session_state:
    test = st.session_state["test"]

    if not test:
        st.warning("От този материал не се получи тест. Опитай с друг.")
    else:
        st.header("📝 Тестът")

        with st.form("quiz"):
            for i, q in enumerate(test):
                st.radio(
                    f"{i + 1}. {q.question}",
                    options=list(range(len(q.options))),
                    format_func=lambda j, q=q: q.options[j],
                    index=None,
                    key=f"answer_{i}",
                )
            submitted = st.form_submit_button("✅ Провери отговорите")

        if submitted:
            correct_count = 0
            topic_stats = {}

            for i, q in enumerate(test):
                chosen = st.session_state.get(f"answer_{i}")
                right_text = q.options[q.correct_index]

                # Записваме въпроса към неговата тема
                topic = q.topic.strip().capitalize()
                stats = topic_stats.setdefault(topic, [0, 0])
                stats[1] += 1

                if chosen == q.correct_index:
                    correct_count += 1
                    stats[0] += 1
                    st.success(f"{i + 1}. Верно! {q.explanation}")
                elif chosen is None:
                    st.warning(f"{i + 1}. Няма отговор. Верният е: {right_text}. {q.explanation}")
                else:
                    st.error(f"{i + 1}. Грешно. Верният е: {right_text}. {q.explanation}")

            # Общ процент
            st.divider()
            st.header("📊 Резултат")
            percent = round(correct_count / len(test) * 100)
            st.metric("Успеваемост", f"{percent}%")
            st.write(f"{correct_count} от {len(test)} верни отговора")
            st.progress(percent / 100)

            # Процент по теми
            st.subheader("По теми")
            weak_topics = []
            for topic, (ok, total) in topic_stats.items():
                topic_percent = round(ok / total * 100)
                st.write(f"**{topic}**: {topic_percent}% ({ok} от {total})")
                st.progress(topic_percent / 100)
                if topic_percent < 70:
                    weak_topics.append((topic_percent, topic))

            # На какво да наблегнеш
            st.subheader("🎯 На какво да наблегнеш")
            if weak_topics:
                weak_topics.sort()  # най-слабите теми първи
                for topic_percent, topic in weak_topics:
                    st.write(f"- **{topic}** ({topic_percent}%)")
            else:
                st.success("Браво! Всички теми са над 70%. Можеш да качиш нов материал.")
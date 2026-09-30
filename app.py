import streamlit as st
from ai import make_test

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

    if st.button("✨ Направи тест"):
        with st.spinner("AI чете материала и прави въпроси..."):
            try:
                test = make_test(файл.getvalue(), файл.type)
                # Изтриваме отговорите от стария тест, за да започнем начисто
                for key in list(st.session_state.keys()):
                    if key.startswith("answer_"):
                        del st.session_state[key]
                st.session_state["test"] = test
            except Exception as e:
                st.error(f"Нещо се обърка: {e}")

# Показваме теста за решаване
if "test" in st.session_state:
    test = st.session_state["test"]

    if not test:
        st.warning("От този материал не се получи тест. Опитай с друг.")
    else:
        st.header("📝 Тестът")

        # Във form отговорите се изпращат всички наведнъж, когато натиснеш бутона
        with st.form("quiz"):
            for i, q in enumerate(test):
                st.radio(
                    f"{i + 1}. {q.question}",
                    options=list(range(len(q.options))),
                    format_func=lambda j, q=q: q.options[j],
                    index=None,  # нищо не е избрано предварително
                    key=f"answer_{i}",
                )
            submitted = st.form_submit_button("✅ Провери отговорите")

        if submitted:
            correct_count = 0
            for i, q in enumerate(test):
                chosen = st.session_state.get(f"answer_{i}")
                right_text = q.options[q.correct_index]

                if chosen == q.correct_index:
                    correct_count += 1
                    st.success(f"{i + 1}. Верно! {q.explanation}")
                elif chosen is None:
                    st.warning(f"{i + 1}. Няма отговор. Верният е: {right_text}. {q.explanation}")
                else:
                    st.error(f"{i + 1}. Грешно. Верният е: {right_text}. {q.explanation}")

            st.subheader(f"Резултат: {correct_count} от {len(test)}")
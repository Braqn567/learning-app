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
                # session_state е "паметта" на страницата, за да не изчезне тестът
                st.session_state["test"] = make_test(файл.getvalue(), файл.type)
            except Exception as e:
                st.error(f"Нещо се обърка: {e}")

# Показваме въпросите (засега само за проверка, че AI работи)
if "test" in st.session_state:
    for i, q in enumerate(st.session_state["test"], 1):
        st.write(f"**{i}. {q.question}**  _(тема: {q.topic})_")
        for option in q.options:
            st.write(f"- {option}")
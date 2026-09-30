import streamlit as st

st.title("📚 Помощник за учене")
st.write("Качи документ или снимка от учебния си материал и ще получиш тест.")

# Избор как да добавим материала
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
    st.success(f"Получих: {файл.name if hasattr(файл, 'name') else 'снимка от камерата'}")
    if файл.type.startswith("image"):
        st.image(файл, caption="Твоят материал")
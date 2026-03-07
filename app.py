import streamlit as st
from rag_engine import load_and_index_documents, get_query_engine, generate_quiz, parse_quiz
import os

st.set_page_config(page_title="Teaching Assistant", page_icon="🎓", layout="wide")
st.title("🎓 Teaching Assistant")
st.caption("Upload your slides or notes and I'll help you learn.")

# ---- Session State ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "query_engine" not in st.session_state:
    st.session_state.query_engine = None
if "index" not in st.session_state:
    st.session_state.index = None
if "raw_texts" not in st.session_state:
    st.session_state.raw_texts = []
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_current" not in st.session_state:
    st.session_state.quiz_current = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = False
if "weak_topics" not in st.session_state:
    st.session_state.weak_topics = []
if "selected_answer" not in st.session_state:
    st.session_state.selected_answer = ""

# ---- Sidebar ----
with st.sidebar:
    st.header("📂 Upload Your Material")
    uploaded_files = st.file_uploader(
        "Upload PDFs or text files",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            save_path = os.path.join("data", file.name)
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
        st.success(f"{len(uploaded_files)} file(s) uploaded.")

    if st.button("🔄 Index Documents"):
        with st.spinner("Reading and indexing your documents..."):
            index, raw_texts = load_and_index_documents()
            st.session_state.index = index
            st.session_state.raw_texts = raw_texts
            st.session_state.query_engine = get_query_engine(index)
        st.success("Done! You can now chat or take a quiz.")

    if st.session_state.weak_topics:
        st.header("⚠️ Weak Topics")
        for topic in st.session_state.weak_topics:
            st.warning(topic)

# ---- Tabs ----
chat_tab, quiz_tab = st.tabs(["💬 Chat", "📝 Quiz"])

# ---- Chat Tab ----
with chat_tab:
    if st.session_state.query_engine is None:
        st.info("Upload your study material and click 'Index Documents' to get started.")
    else:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Ask a question about your material...")

        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state.query_engine.query(user_input)
                    st.markdown(str(response))
            st.session_state.chat_history.append({"role": "assistant", "content": str(response)})

# ---- Quiz Tab ----
with quiz_tab:
    if st.session_state.index is None:
        st.info("Upload your study material and click 'Index Documents' to generate a quiz.")
    else:
        if not st.session_state.quiz_questions:
            num_q = st.slider("How many questions?", min_value=1, max_value=5, value=3)

            if st.button("🎯 Generate Quiz"):
                with st.spinner("Generating quiz from your material..."):
                    raw = generate_quiz(st.session_state.raw_texts, num_questions=num_q)
                    questions = parse_quiz(raw)

                if questions:
                    st.session_state.quiz_questions = questions
                    st.session_state.quiz_current = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answered = False
                    st.session_state.selected_answer = ""
                    st.rerun()
                else:
                    st.error("Couldn't generate quiz. Try again.")

        else:
            questions = st.session_state.quiz_questions
            current = st.session_state.quiz_current

            if current < len(questions):
                q = questions[current]
                st.subheader(f"Question {current + 1} of {len(questions)}")
                st.progress(current / len(questions))
                st.markdown(f"**{q['question']}**")

                if not st.session_state.quiz_answered:
                    for key, val in q["options"].items():
                        if st.button(f"{key}) {val}", key=f"opt_{key}"):
                            st.session_state.quiz_answered = True
                            st.session_state.selected_answer = key
                            if key == q["answer"]:
                                st.session_state.quiz_score += 1
                            else:
                                if q["question"] not in st.session_state.weak_topics:
                                    st.session_state.weak_topics.append(q["question"])
                            st.rerun()
                else:
                    selected = st.session_state.selected_answer
                    if selected == q["answer"]:
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Wrong. Correct answer: {q['answer']}")
                    if q.get("explanation"):
                        st.info(f"💡 {q['explanation']}")
                    else:
                        st.info(f"💡 The correct answer is {q['answer']}: {q['options'].get(q['answer'], '')}")

                    if st.button("Next Question ➡️"):
                        st.session_state.quiz_current += 1
                        st.session_state.quiz_answered = False
                        st.session_state.selected_answer = ""
                        st.rerun()
            else:
                total = len(questions)
                score = st.session_state.quiz_score
                st.subheader("🏁 Quiz Complete!")
                st.metric("Your Score", f"{score} / {total}")

                if score == total:
                    st.success("Perfect score! You really know this material.")
                elif score >= total * 0.7:
                    st.info("Good job! Review the weak topics in the sidebar.")
                else:
                    st.warning("Keep studying. Focus on the weak topics flagged in the sidebar.")

                if st.button("🔁 Retake Quiz"):
                    st.session_state.quiz_questions = []
                    st.session_state.weak_topics = []
                    st.session_state.selected_answer = ""
                    st.rerun()
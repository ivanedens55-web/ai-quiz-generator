"""AI Quiz Generator: a Streamlit app that builds multiple-choice quizzes with Gemini."""

import streamlit as st

from ai import QuizGenerationError, generate_quiz

DIFFICULTIES = ["Easy", "Medium", "Hard"]


def init_state() -> None:
    """Set up session state keys used across reruns."""
    defaults = {
        "quiz": None,        # list of question dicts
        "quiz_id": 0,        # bumps on every new quiz so old answers are cleared
        "submitted": False,
        "answers": [],       # answers saved at submit time
        "quiz_topic": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def answer_key(index: int) -> str:
    """Session-state key for the selected answer to question `index`."""
    return f"answer_{st.session_state.quiz_id}_{index}"


def render_header() -> None:
    st.title("AI Quiz Generator")
    st.write(
        "Enter any topic and get a multiple-choice quiz written by Google Gemini. "
        "Answer the questions, submit, and see your score with explanations."
    )


def render_settings() -> None:
    """Quiz settings form. Generates a new quiz when submitted."""
    with st.form("settings"):
        topic = st.text_input("Topic", placeholder="e.g. Java OOP, Photosynthesis, World War II")
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.slider("Number of questions", min_value=3, max_value=10, value=5)
        with col2:
            difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=1)
        generate = st.form_submit_button("Generate Quiz", type="primary", width="stretch")

    if generate:
        if not topic.strip():
            st.warning("Please enter a topic first.")
            return
        with st.spinner(f"Writing {num_questions} {difficulty.lower()} questions about {topic.strip()}..."):
            try:
                quiz = generate_quiz(topic, num_questions, difficulty)
            except QuizGenerationError as e:
                st.error(str(e))
                return

        st.session_state.quiz = quiz
        st.session_state.quiz_id += 1
        st.session_state.submitted = False
        st.session_state.answers = []
        st.session_state.quiz_topic = topic.strip()

        if len(quiz) < num_questions:
            st.info(
                f"The AI returned {len(quiz)} usable question(s) instead of {num_questions}. "
                "Invalid ones were skipped."
            )


def render_quiz() -> None:
    """Show the questions with answer choices and a submit button."""
    quiz = st.session_state.quiz
    st.subheader(f"Quiz: {st.session_state.quiz_topic}")

    with st.form(f"quiz_{st.session_state.quiz_id}"):
        for i, q in enumerate(quiz):
            st.markdown(f"**{i + 1}. {q['question']}**")
            st.radio(
                f"Answer for question {i + 1}",
                q["options"],
                index=None,  # no answer pre-selected
                key=answer_key(i),
                label_visibility="collapsed",
            )
        submit = st.form_submit_button("Submit Quiz", type="primary")

    if submit:
        answers = [st.session_state.get(answer_key(i)) for i in range(len(quiz))]
        unanswered = [str(i + 1) for i, a in enumerate(answers) if a is None]
        if unanswered:
            st.warning(f"Please answer every question before submitting. Missing: {', '.join(unanswered)}")
            return
        # Save a copy: widget values are cleared once the form is no longer shown.
        st.session_state.answers = answers
        st.session_state.submitted = True
        st.rerun()


def calculate_score(quiz: list[dict], answers: list[str | None]) -> int:
    """Count how many answers match the correct answer."""
    return sum(1 for q, a in zip(quiz, answers) if a == q["correct_answer"])


def render_results() -> None:
    """Show the score and per-question feedback."""
    quiz = st.session_state.quiz
    answers = st.session_state.answers
    score = calculate_score(quiz, answers)
    total = len(quiz)

    st.subheader(f"Results: {st.session_state.quiz_topic}")
    st.metric("Your score", f"{score} / {total}", f"{round(score / total * 100)}%", delta_color="off")

    if score == total:
        st.success("Perfect score!")
    elif score >= total / 2:
        st.info("Good work. Review the explanations below for the ones you missed.")
    else:
        st.warning("Keep practicing. The explanations below should help.")

    for i, (q, answer) in enumerate(zip(quiz, answers)):
        correct = answer == q["correct_answer"]
        icon = "✅" if correct else "❌"
        with st.expander(f"{icon} Question {i + 1}: {q['question']}", expanded=not correct):
            st.write(f"**Your answer:** {answer}")
            if not correct:
                st.write(f"**Correct answer:** {q['correct_answer']}")
            st.write(f"**Explanation:** {q['explanation']}")

    if st.button("Start a new quiz"):
        st.session_state.quiz = None
        st.session_state.submitted = False
        st.session_state.answers = []
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="AI Quiz Generator", page_icon="🧠", layout="centered")
    init_state()
    render_header()
    render_settings()

    if st.session_state.quiz and st.session_state.submitted:
        render_results()
    elif st.session_state.quiz:
        render_quiz()


if __name__ == "__main__":
    main()

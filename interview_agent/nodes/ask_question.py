"""Ask the current question to the candidate."""

from interview_agent.state import InterviewState


def ask_question(state: InterviewState) -> InterviewState:
    """Render the current question. The question is already stored in
    state['current_question'] by select_next_question."""
    # Nothing to do here — the question is ready in the state.
    # The CLI layer reads current_question and displays it to the user.
    return state
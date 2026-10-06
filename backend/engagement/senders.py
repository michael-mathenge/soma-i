import os


class ConsoleSender:
    name = "console"

    def send(self, learner, message):
        print(f"[{learner.display_name}] {message}")


class AfricasTalkingSender:
    """Sandbox integration boundary; no network send is implemented in this PoC."""

    name = "africastalking-sandbox"

    def __init__(self):
        self.username = os.getenv("AFRICASTALKING_USERNAME", "sandbox")
        self.api_key = os.getenv("AFRICASTALKING_API_KEY", "")

    def send(self, learner, message):
        if not self.api_key:
            raise RuntimeError(
                "AFRICASTALKING_API_KEY is required for sandbox configuration"
            )
        print(
            f"Sandbox sender configured for {learner.display_name}; delivery is intentionally stubbed."
        )


def message_for(learner, lessons, pathway):
    if learner.preferred_language == "sw":
        return f"SOMA.i: Masomo {lessons} yamebaki hadi hatua inayofuata ya {pathway}. Endelea kujifunza!"
    return (
        f"SOMA.i: {lessons} lessons to your next checkpoint in {pathway}. Keep going!"
    )

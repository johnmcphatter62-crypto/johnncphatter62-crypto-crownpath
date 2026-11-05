"""Synthetic classroom continuity policy tests with AI disabled.

This is an isolated behavioral model, NOT a production route integration test.
No network, live student data, AI API, or payment provider.
"""
from dataclasses import dataclass, field


@dataclass
class OfflineClassroom:
    ai_available: bool = False
    lessons: dict = field(default_factory=lambda: {"scalp-101": "Synthetic scalp lesson"})
    roles: dict = field(default_factory=lambda: {
        "learner-a": "learner", "instructor-a": "instructor", "owner-a": "owner"
    })
    completions: set = field(default_factory=set)

    def lesson(self, actor, lesson_id):
        if self.roles.get(actor) not in {"learner", "instructor", "owner"}:
            return "DENIED"
        return self.lessons.get(lesson_id, "NOT_FOUND")

    def complete(self, actor, lesson_id):
        if self.roles.get(actor) != "learner" or lesson_id not in self.lessons:
            return "DENIED"
        self.completions.add((actor, lesson_id))
        return "RECORDED"

    def ai_assistant(self, actor):
        if self.roles.get(actor) is None:
            return "DENIED"
        return "AVAILABLE" if self.ai_available else "AI_UNAVAILABLE"


def test_learner_can_read_and_complete_saved_lesson_without_ai():
    classroom = OfflineClassroom()
    assert classroom.lesson("learner-a", "scalp-101") == "Synthetic scalp lesson"
    assert classroom.complete("learner-a", "scalp-101") == "RECORDED"
    assert ("learner-a", "scalp-101") in classroom.completions
    assert classroom.ai_assistant("learner-a") == "AI_UNAVAILABLE"


def test_instructor_and_owner_read_saved_lesson_without_ai():
    classroom = OfflineClassroom()
    for actor in ("instructor-a", "owner-a"):
        assert classroom.lesson(actor, "scalp-101") == "Synthetic scalp lesson"
        assert classroom.ai_assistant(actor) == "AI_UNAVAILABLE"


def test_unauthorized_users_still_fail_closed_during_ai_outage():
    classroom = OfflineClassroom()
    assert classroom.lesson("stranger", "scalp-101") == "DENIED"
    assert classroom.complete("stranger", "scalp-101") == "DENIED"
    assert classroom.complete("instructor-a", "scalp-101") == "DENIED"
    assert classroom.ai_assistant("stranger") == "DENIED"
    assert classroom.completions == set()

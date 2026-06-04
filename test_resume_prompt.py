import unittest

from resume_processor import build_resume_prompt


class ResumePromptTests(unittest.TestCase):
    def test_prompt_stays_factual_and_does_not_overstate(self):
        prompt = build_resume_prompt(
            email_body="Recruiter wants a Python/ML engineer",
            base_text="Experience: Python developer at Example Corp",
        )

        self.assertIn("Do not invent", prompt)
        self.assertIn("preserve the existing facts", prompt)
        self.assertNotIn("aggressively emphasize", prompt)
        self.assertNotIn("AI-focused engineer", prompt)


if __name__ == "__main__":
    unittest.main()

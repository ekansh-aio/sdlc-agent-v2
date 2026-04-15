import re


def is_garbage_input(text: str) -> bool:
    stripped = text.strip()
    if len(re.findall(r"[^\w\s]", stripped)) > len(stripped) // 2:
        return True
    if len(set(stripped)) <= 2:
        return True
    return False


def fmt_tcg_response(text: str) -> str:
    replacements = [
        ("TestCaseID:",      "**TestCaseID:** "),
        ("Summary:",         "**Summary:** "),
        ("Description:",     "**Description:** "),
        ("Action:",          "**Action:** "),
        ("Data:",            "**Data:** "),
        ("Expected Result:", "**Expected Result:** "),
        ("Priority:",        "**Priority:** "),
        ("ManualSteps:",     "**Manual Steps:** "),
        ("cucumber_steps:",  "**Cucumber Steps:** "),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def parse_ras_fields(content: str) -> tuple:
    """
    Returns (title, description_md, acceptance_criteria, priority, effort).
    """
    def find(pattern):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else "N/A"

    title    = find(r"(?:\*\*Title:\*\*|###\s*Title[:\s]*)\s*(.+)")
    priority = find(r"(?:\*\*Priority:\*\*|###\s*Priority[:\s]*)\s*(.+)")
    effort   = find(r"(?:\*\*Estimated Effort:\*\*|###\s*Estimated Effort[:\s]*)\s*(.+)")

    ac_match = re.search(
        r"\*\*Acceptance Criteria:\*\*(.*?)(?=\n\*\*Priority:\*\*|\Z)",
        content, flags=re.DOTALL
    )
    acceptance = ac_match.group(0).strip() if ac_match else ""

    desc = re.sub(r"\n?(?:\*\*Title:\*\*|###\s*Title[:\s]*).*", "", content).strip()
    desc = re.sub(r"\n?(?:\*\*Priority:\*\*|###\s*Priority[:\s]*).*", "", desc)
    desc = re.sub(r"\n?(?:\*\*Estimated Effort:\*\*|###\s*Estimated Effort[:\s]*).*", "", desc)
    desc = re.sub(r'\*\*Acceptance Criteria:\*\*.*', '', desc, flags=re.DOTALL).strip()
    desc = desc + "\n\n*Note: AI generated content*"

    return title, desc, acceptance, priority, effort

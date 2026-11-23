"""Clinical and Operational Safety Guardrails for AE-Watch UK.

Implements PII redaction (NHS numbers, postcodes), prompt-injection defense,
and policy citation verification.
Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import re
from typing import Any

from ae_watch.utils.logger import logger

# NHS numbers are 10 digits, formatted as 3-3-4 (e.g. 943 476 5919) or continuous 10 digits
NHS_NUMBER_PATTERN = re.compile(r"\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{4})\b")

# UK Postcodes (e.g., L7 8XP, CH2 1UL, WA5 1QG)
UK_POSTCODE_PATTERN = re.compile(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b", re.IGNORECASE)

# Patient Name / DOB patterns
PATIENT_PII_PATTERN = re.compile(
    r"\b(patient\s+name|dob|date\s+of\s+birth|mr\.|mrs\.|ms\.)[:\s]+([A-Za-z0-9/\-]+)",
    re.IGNORECASE,
)

# Adversarial prompt-injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"act\s+as\s+(an\s+)?unrestricted", re.IGNORECASE),
    re.compile(r"dan\s+mode|jailbreak|bypass\s+safety", re.IGNORECASE),
    re.compile(
        r"print\s+(the\s+)?(raw\s+)?(system|developer)\s+(instructions|prompt)", re.IGNORECASE
    ),
    re.compile(r"reveal\s+your\s+(secret\s+)?(api\s+key|prompt)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"ignore\s+clinical\s+policies", re.IGNORECASE),
]


class ClinicalSafetyGuardrails:
    """Enforces patient privacy, security boundaries, and grounded citations."""

    def sanitize_input(self, user_query: str) -> dict[str, Any]:
        """Detect and redact PII, and check for adversarial prompt injections."""
        pii_found = False
        redacted_text = user_query

        # 1. Redact NHS numbers
        if NHS_NUMBER_PATTERN.search(redacted_text):
            pii_found = True
            redacted_text = NHS_NUMBER_PATTERN.sub("[REDACTED_NHS_NUMBER]", redacted_text)

        # 2. Redact UK postcodes
        if UK_POSTCODE_PATTERN.search(redacted_text):
            pii_found = True
            redacted_text = UK_POSTCODE_PATTERN.sub("[REDACTED_POSTCODE]", redacted_text)

        # 3. Redact Patient demographics
        if PATIENT_PII_PATTERN.search(redacted_text):
            pii_found = True
            redacted_text = PATIENT_PII_PATTERN.sub(r"\1: [REDACTED_PATIENT_PII]", redacted_text)

        # 4. Check for adversarial injection
        is_injection = any(pattern.search(user_query) for pattern in PROMPT_INJECTION_PATTERNS)

        if is_injection:
            logger.warning("prompt_injection_detected", raw_query=user_query[:100])

        if pii_found:
            logger.info("pii_detected_and_redacted", original_len=len(user_query))

        return {
            "sanitized_query": redacted_text,
            "pii_detected": pii_found,
            "is_injection": is_injection,
            "action": "block" if is_injection else "proceed",
        }

    def verify_groundedness_and_citations(
        self, response_text: str, trust_code: str, policy_chunks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Verify that synthesized operational recommendations contain Trust ODS and policy citations."""
        trust_cited = trust_code.upper() in response_text.upper()

        policy_ids = [p["policy_id"] for p in policy_chunks]
        cited_policies = [pid for pid in policy_ids if pid in response_text]

        # Check for standard UEC or OPEL mentions
        has_uec_standard_mention = any(
            term in response_text.lower()
            for term in ["opel", "sdec", "ambulance handover", "virtual ward", "4-hour", "uec"]
        )

        is_grounded = trust_cited and (len(cited_policies) > 0 or has_uec_standard_mention)

        # If policy IDs weren't cited explicitly, append mandatory references
        grounded_response = response_text
        if not cited_policies and policy_chunks:
            mandatory_refs = "\n\n**Mandatory Policy References:**\n" + "\n".join(
                f"- [{p['policy_id']}] {p['title']} ({p['citation']})" for p in policy_chunks[:2]
            )
            grounded_response += mandatory_refs

        return {
            "is_grounded": is_grounded,
            "trust_cited": trust_cited,
            "cited_policies": cited_policies,
            "grounded_response": grounded_response,
        }


safety_guardrails = ClinicalSafetyGuardrails()

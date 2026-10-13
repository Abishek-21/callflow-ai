"""Deterministic, rule-based transcript evaluator.

Used when no LLM API key is configured, and as the safe fallback when the
LLM path fails. It looks for concrete phrases in the agent's and customer's
turns, so the same transcript always produces the same result. It is a
heuristic stand-in for the LLM evaluator, not a substitute for human review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import (
    COACHING_TIPS,
    BusinessType,
    EvaluationResult,
    LeadTemperature,
    RubricCategory,
    RubricScoreItem,
    Urgency,
    compute_overall_score,
)

# Fictional company details used in generated follow-ups.
COMPANY_BY_TYPE = {
    BusinessType.ROOFING: "Summit Roofing",
    BusinessType.HVAC: "Summit Heating & Air",
    BusinessType.PLUMBING: "Summit Plumbing",
    BusinessType.GENERIC: "Summit Home Services",
}
COMPANY_PHONE = "(512) 555-0199"


def _rx(*patterns: str) -> re.Pattern[str]:
    """Case-insensitive alternation of patterns, anchored on word boundaries."""
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


# --- Speaker parsing -------------------------------------------------------

AGENT_LABELS = {"agent", "rep", "csr", "representative", "advisor", "dispatcher"}
SPEAKER_RE = re.compile(r"^\[?([A-Za-z][A-Za-z .'()-]{0,40}?)\]?\s*:\s*(.*)$")
# Generic speaker labels appearing mid-line, e.g. a transcript pasted without line breaks.
INLINE_LABEL_RE = re.compile(r"[ \t]+(?=\b(?:agent|customer|caller|rep|csr)\s*:)", re.IGNORECASE)

# --- Phrase signals ----------------------------------------------------------

GREETING = _rx(r"thank(?:s| you) for calling", r"good (?:morning|afternoon|evening)", r"hello", r"hi", r"hey")
INTRO = _rx(r"this is", r"my name is", r"speaking")
EMPATHY = _rx(
    r"sorry to hear", r"(?:i )?(?:completely |totally )?understand", r"that sounds",
    r"i can imagine", r"happy to help", r"glad you called", r"let's get you", r"we can help",
)

ASK_NAME = _rx(r"your name", r"who am i speaking", r"may i have your name")
ASK_PHONE = _rx(r"phone", r"number to reach", r"best number", r"callback number")
ASK_EMAIL = _rx(r"e-?mail")
ASK_HOMEOWNER = _rx(r"homeowner", r"own the (?:home|house|property)", r"do you own", r"property owner", r"rent or own")
ASK_ADDRESS = _rx(
    r"address", r"zip(?: code)?", r"what city", r"which city",
    r"where is the (?:home|house|property)", r"where are you located",
)
CONTACT_QUESTIONS = (ASK_NAME, ASK_PHONE, ASK_EMAIL, ASK_HOMEOWNER, ASK_ADDRESS)

DISCOVERY_Q = _rx(
    r"when", r"how long", r"how old", r"how (?:bad|big|often)", r"where", r"what", r"which",
    r"any", r"did", r"does", r"is (?:it|the|there|anyone)", r"are (?:you|they|there)",
    r"have you", r"has (?:it|the)", r"can you (?:describe|tell)", r"tell me",
)
NON_DISCOVERY_Q = _rx(r"anything else", r"how can i help", r"works? (?:better|for you)", r"slot", r"available")

AREA_CHECK = _rx(r"service area", r"our area", r"that area", r"located", r"what area")
URGENCY_CHECK = _rx(
    r"how soon", r"urgent", r"emergency", r"right now", r"actively", r"still (?:leaking|dripping|running)",
    r"how long has", r"how bad", r"safe", r"at risk",
)

VALUE = _rx(
    r"free\b[\w\s]{0,25}?\b(?:inspection|estimate|quote)", r"no obligation", r"licensed", r"insured",
    r"certified", r"insurance claim", r"warrant(?:y|ied)", r"guarantee(?:d)?", r"financing",
    r"same[- ]day", r"upfront", r"written estimate", r"\d+ years? (?:of )?experience",
    r"family[- ]owned", r"top[- ]rated",
)

OBJECTION = _rx(
    r"expensive", r"cost(?:s|ly)?", r"price", r"pricing", r"how much", r"afford", r"budget",
    r"too much", r"cheaper", r"other (?:quotes|companies)", r"another company", r"think about it",
    r"talk (?:it over|to my (?:wife|husband|spouse|partner))", r"a fortune", r"not sure (?:if|about)",
)
OBJECTION_RESPONSE = _rx(
    r"(?:i |we )?(?:completely |totally )?understand", r"financing", r"payment plan",
    r"free\b[\w\s]{0,25}?\b(?:inspection|estimate|quote)", r"no obligation", r"no charge", r"upfront",
    r"written estimate", r"warrant(?:y|ied)", r"price match", r"worth", r"save you",
)

APPOINTMENT_ASK = _rx(
    r"schedul\w*", r"book\w*", r"appointment", r"come out", r"send (?:a tech\w*|someone|an inspector|a crew)",
    r"availab\w*", r"works? (?:better|for you)", r"slot", r"set you up",
)
BOOKED = _rx(
    r"you're (?:all )?(?:set|booked|scheduled|confirmed)",
    r"i(?:'ve| have) (?:booked|scheduled|got you down|put you down)",
    r"(?:appointment|inspection|visit|service call) is (?:set|confirmed|booked|scheduled)",
    r"we'll see you", r"booked you", r"scheduled you", r"confirmed for",
)

NEXT_STEP = _rx(
    r"you'll (?:get|receive)", r"you will (?:get|receive)", r"confirmation", r"(?:text|email|call) you",
    r"(?:technician|inspector|tech|crew) will", r"next step", r"(?:i'll|we'll|i will|we will) (?:call|email|text|send)",
    r"arriv\w*",
)
CUSTOMER_BURDEN = _rx(r"call (?:us )?back", r"check back", r"give us a call", r"try (?:again|back)")
WITHIN_TIME = _rx(r"within \d+ (?:minutes|hours?)")
_DAY = r"\b(?:(?:mon|tues|wednes|thurs|fri|satur|sun)day|tomorrow|today|tonight)\b"
# A day word followed closely by a clock time, with no other day word in between
# (so "today, and I'll call you tomorrow at 10 a.m." matches only "tomorrow at 10 a.m.").
TIME_RE = re.compile(
    _DAY + r"(?:(?!" + _DAY + r")[^.?!\n]){0,40}?\b\d{1,2}(?::\d{2})?\s?(?:a\.?m\.?|p\.?m\.?)",
    re.IGNORECASE,
)
MERIDIEM_RE = re.compile(r"\s?\b([ap])\.?m\.?", re.IGNORECASE)
LEADING_FILLER_RE = re.compile(r"^(?:(?:hi|hello|hey|yeah|yes|so|well|um|uh|okay|ok)\b[,\s]*)+", re.IGNORECASE)

UNPROFESSIONAL = _rx(
    r"dunno", r"whatever", r"not my problem", r"calm down", r"can't help you", r"no idea",
    r"gonna", r"gotta", r"um+", r"uh+", r"yeah,? yeah",
)
POLITE = _rx(r"thank(?:s| you)", r"please", r"appreciate", r"have a (?:great|good|nice)", r"you're welcome", r"my pleasure")

HIGH_URGENCY = _rx(
    r"emergency", r"asap", r"right away", r"immediately", r"today", r"tonight",
    r"(?:actively|still) (?:leaking|dripping)", r"coming (?:in|through)", r"dripping (?:through|into)",
    r"flood\w*", r"burst", r"no heat", r"no (?:ac|a/c|air)", r"(?:stopped|not) (?:cooling|working|heating)",
    r"\d{2,3} degrees", r"newborn", r"baby", r"elderly", r"urgent",
)
MEDIUM_URGENCY = _rx(
    r"this week", r"soon", r"few days", r"tomorrow", r"before the weekend", r"getting worse",
    r"spreading", r"leak\w*", r"drip\w*",
)
SAFETY = _rx(
    r"gas smell", r"smell(?:s)? (?:like )?gas", r"sparking", r"sparks", r"exposed wires?",
    r"carbon monoxide", r"sagging", r"collaps\w*", r"mold", r"electrical",
)
FRUSTRATION = _rx(
    r"frustrat\w*", r"angry", r"ridiculous", r"unacceptable", r"cancel", r"waste of time",
    r"called (?:twice|three times|before|again)", r"nobody (?:called|showed)",
)

PROBLEM_WORDS = _rx(
    r"leak\w*", r"drip\w*", r"broke\w*", r"not working", r"isn't", r"won't", r"stopped", r"damage\w*",
    r"problem", r"issue", r"noise", r"clog\w*", r"cooling", r"heat\w*", r"crack\w*", r"missing",
    r"burst", r"warm air", r"water",
)

# --- Extraction ----------------------------------------------------------------

PHONE_RE = re.compile(r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
NAME_RE = re.compile(
    r"(?i:\bmy name is|\bmy name's|\bthis is|\bit's|\bi am|\bi'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z'-]+)?)"
)
NOT_NAMES = {"Calling", "Not", "Just", "So", "Still", "Sure", "About", "Okay", "Really", "Here"}
ADDRESS_RE = re.compile(
    r"\b\d{2,6}\s+(?:[A-Z][a-z]+\s){1,3}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Boulevard|Blvd|Way|Circle|Cir|Place|Pl)\b"
    r"(?:(?:,|\s+in)\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)?"
)
CITY_RE = re.compile(r"(?i:\blive in|\blocated in|\bwe're in|\bi'm in|\bout in|\bover in)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)")

# (business type, pattern, service label); rules for the call's own business
# type are tried first.
SERVICE_RULES: list[tuple[BusinessType, re.Pattern[str], str]] = [
    (BusinessType.ROOFING, _rx(r"storm", r"hail", r"wind damage"), "Storm damage roof repair"),
    (BusinessType.ROOFING, _rx(r"new roof", r"roof replacement", r"replace (?:the|my|our) roof"), "Roof replacement"),
    (BusinessType.ROOFING, _rx(r"roof", r"ceiling", r"shingles?"), "Roof leak repair"),
    (BusinessType.ROOFING, _rx(r"gutters?"), "Gutter service"),
    (BusinessType.HVAC, _rx(r"replac\w*", r"new (?:ac|system|unit)"), "HVAC system replacement"),
    (BusinessType.HVAC, _rx(r"ac", r"a/c", r"air condition\w*", r"cooling"), "AC repair"),
    (BusinessType.HVAC, _rx(r"furnace", r"no heat", r"heater", r"heating"), "Heating repair"),
    (BusinessType.HVAC, _rx(r"thermostats?"), "Thermostat service"),
    (BusinessType.PLUMBING, _rx(r"water heater"), "Water heater service"),
    (BusinessType.PLUMBING, _rx(r"pipes?", r"sink", r"burst", r"supply line"), "Pipe leak repair"),
    (BusinessType.PLUMBING, _rx(r"drain", r"clog\w*"), "Drain cleaning"),
    (BusinessType.PLUMBING, _rx(r"toilet"), "Toilet repair"),
    (BusinessType.GENERIC, _rx(r"garage door"), "Garage door repair"),
    (BusinessType.GENERIC, _rx(r"deck", r"fence", r"porch"), "Deck and fence repair"),
]


@dataclass
class ParsedTranscript:
    agent_lines: list[str]
    customer_lines: list[str]
    labeled: bool

    @property
    def agent(self) -> str:
        return "\n".join(self.agent_lines)

    @property
    def customer(self) -> str:
        return "\n".join(self.customer_lines)


def _normalize(text: str) -> str:
    return (
        text.replace("\u2019", "'").replace("\u2018", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2014", " - ").replace("\u2013", "-")
    )


def parse_transcript(text: str, agent_name: str = "") -> ParsedTranscript:
    """Split a transcript into agent and customer turns using "Speaker: text" labels.

    A label counts as the agent if it contains a generic agent word ("Agent",
    "Rep", ...) or the agent's first name; any other label is the customer.
    Unlabeled lines continue the previous speaker's turn. If no labels are
    found at all, every line is treated as both agent and customer text.
    """
    aliases = set(AGENT_LABELS)
    if agent_name.strip():
        aliases.add(agent_name.strip().split()[0].lower())

    agent_lines: list[str] = []
    customer_lines: list[str] = []
    all_lines: list[str] = []
    current: list[str] | None = None
    labeled = False

    for raw in INLINE_LABEL_RE.sub("\n", _normalize(text)).splitlines():
        line = raw.strip()
        if not line:
            continue
        all_lines.append(line)
        match = SPEAKER_RE.match(line)
        if match:
            labeled = True
            label_words = set(re.findall(r"[a-z]+", match.group(1).lower()))
            current = agent_lines if label_words & aliases else customer_lines
            if match.group(2).strip():
                current.append(match.group(2).strip())
        elif current is not None:
            current.append(line)

    if not labeled:
        return ParsedTranscript(list(all_lines), list(all_lines), labeled=False)
    return ParsedTranscript(agent_lines, customer_lines, labeled=True)


def _questions(lines: list[str]) -> list[str]:
    return [q.strip() for line in lines for q in re.findall(r"[^.?!]*\?", line)]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]


def _distinct(pattern: re.Pattern[str], text: str) -> list[str]:
    """Distinct matches in order of first appearance (case-insensitive), as first written."""
    seen: dict[str, str] = {}
    for m in pattern.finditer(text):
        seen.setdefault(m.group(0).lower(), m.group(0))
    return list(seen.values())


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _lower_first(text: str) -> str:
    first = text.split(" ", 1)[0]
    return text if first.isupper() else text[:1].lower() + text[1:]


# --- Evaluation ----------------------------------------------------------------


@dataclass
class _Facts:
    """Everything extracted from the transcript that scoring and copy depend on."""

    parsed: ParsedTranscript
    business_type: BusinessType
    agent_name: str
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    location: str | None = None
    service_type: str = ""
    customer_problem: str = ""
    urgency: Urgency = Urgency.LOW
    appointment_booked: bool = False
    appointment_time: str | None = None
    callback_time: str | None = None
    objection: str | None = None
    na_categories: set[RubricCategory] = field(default_factory=set)


def _extract(parsed: ParsedTranscript, business_type: BusinessType, agent_name: str) -> _Facts:
    facts = _Facts(parsed=parsed, business_type=business_type, agent_name=agent_name)
    customer, agent = parsed.customer, parsed.agent
    everything = customer + "\n" + agent

    for m in NAME_RE.finditer(customer):
        if m.group(1).split()[0] not in NOT_NAMES:
            facts.customer_name = m.group(1)
            break

    phone = PHONE_RE.search(customer) or PHONE_RE.search(everything)
    facts.customer_phone = phone.group(0) if phone else None
    email = EMAIL_RE.search(customer) or EMAIL_RE.search(everything)
    facts.customer_email = email.group(0) if email else None

    address = ADDRESS_RE.search(customer) or ADDRESS_RE.search(everything)
    if address:
        facts.location = re.sub(r"\s+in\s+", ", ", address.group(0))
    else:
        city = CITY_RE.search(customer)
        facts.location = city.group(1) if city else None

    rules = sorted(SERVICE_RULES, key=lambda r: r[0] != business_type)
    fallback = "General home service" if business_type == BusinessType.GENERIC else f"{business_type.value} service"
    facts.service_type = next((label for _, pattern, label in rules if pattern.search(customer)), fallback)

    problem = next(
        (s for s in _sentences(customer) if PROBLEM_WORDS.search(s)),
        next((s for s in _sentences(customer) if len(s) > 30), "Problem not clearly stated in transcript."),
    )
    problem = LEADING_FILLER_RE.sub("", problem)
    facts.customer_problem = (problem[:1].upper() + problem[1:])[:240]

    if HIGH_URGENCY.search(customer):
        facts.urgency = Urgency.HIGH
    elif MEDIUM_URGENCY.search(customer):
        facts.urgency = Urgency.MEDIUM

    times = [m.group(0) for m in TIME_RE.finditer(agent)]
    last_time = None
    if times:
        # "today at 3 p.m." -> "Today at 3 PM" (no trailing period to collide with sentence ends)
        last_time = MERIDIEM_RE.sub(lambda m: f" {m.group(1).upper()}M", times[-1])
        last_time = last_time[:1].upper() + last_time[1:]
    facts.appointment_booked = bool(BOOKED.search(agent))
    if facts.appointment_booked:
        facts.appointment_time = last_time
    elif last_time and NEXT_STEP.search(agent):
        facts.callback_time = last_time

    objection = OBJECTION.search(customer)
    facts.objection = objection.group(0) if objection else None
    return facts


def _score_opening(f: _Facts) -> tuple[int, str]:
    opening = " ".join(f.parsed.agent_lines[:2])
    checks = {
        "a greeting": bool(GREETING.search(opening)),
        "an agent introduction": bool(INTRO.search(opening)),
        "empathy for the customer's situation": bool(EMPATHY.search(f.parsed.agent)),
    }
    done = [k for k, v in checks.items() if v]
    missed = [k for k, v in checks.items() if not v]
    score = {0: 1, 1: 2, 2: 4, 3: 5}[len(done)]
    return score, _describe(done, missed)


def _score_qualification(f: _Facts) -> tuple[int, str]:
    questions = " ".join(_questions(f.parsed.agent_lines))
    first_name = f.customer_name.split()[0] if f.customer_name else None
    checks = {
        # Using the customer's name counts as capturing it, even if they volunteered it.
        "customer name": bool(ASK_NAME.search(questions))
        or bool(first_name and re.search(rf"\b{re.escape(first_name)}\b", f.parsed.agent)),
        "callback number": bool(ASK_PHONE.search(questions)),
        "email": bool(ASK_EMAIL.search(questions)),
        "homeownership": bool(ASK_HOMEOWNER.search(questions)),
        "service address": bool(ASK_ADDRESS.search(questions)),
    }
    done = [k for k, v in checks.items() if v]
    missed = [k for k, v in checks.items() if not v]
    score = len(done)
    if score == 0 and (f.customer_phone or f.customer_email):
        score = 1  # the customer volunteered contact details without being asked
    return score, _describe(done, missed, verb_done="Confirmed", verb_missed="Did not confirm")


def _score_discovery(f: _Facts) -> tuple[int, str]:
    discovery = [
        q for q in _questions(f.parsed.agent_lines)
        if DISCOVERY_Q.search(q)
        and not NON_DISCOVERY_Q.search(q)
        and not any(p.search(q) for p in CONTACT_QUESTIONS)
    ]
    n = len(discovery)
    score = {0: 0, 1: 2, 2: 3, 3: 4}.get(n, 5)
    feedback = f"Asked {n} discovery question{'s' if n != 1 else ''} about the problem."
    if n < 3:
        feedback += " Dig deeper: when it started, how severe it is, and what has been tried."
    return score, feedback


def _score_area_urgency(f: _Facts) -> tuple[int, str]:
    agent = f.parsed.agent
    questions = " ".join(_questions(f.parsed.agent_lines))
    checks = {
        "service address/area": bool(ASK_ADDRESS.search(questions) or AREA_CHECK.search(agent)),
        "urgency": bool(URGENCY_CHECK.search(agent)),
    }
    done = [k for k, v in checks.items() if v]
    missed = [k for k, v in checks.items() if not v]
    score = {0: 0, 1: 2, 2: 5}[len(done)]
    return score, _describe(done, missed, verb_done="Confirmed", verb_missed="Did not confirm")


def _score_value(f: _Facts) -> tuple[int, str]:
    points = _distinct(VALUE, f.parsed.agent)
    score = {0: 1, 1: 3, 2: 4}.get(len(points), 5)
    if not points:
        return score, "No value points mentioned (e.g., free inspection, warranty, licensing, financing)."
    return score, f"Communicated value: {_join(points)}."


def _score_objection(f: _Facts) -> tuple[int, str]:
    if not f.objection:
        f.na_categories.add(RubricCategory.OBJECTION_HANDLING)
        return 4, "No price or hesitation objection raised on this call."
    responses = _distinct(OBJECTION_RESPONSE, f.parsed.agent)
    score = {0: 1, 1: 3, 2: 4}.get(len(responses), 5)
    if not responses:
        return score, (
            f'Customer raised a concern ("{f.objection}") that the agent did not address '
            "with reassurance, options, or a free estimate."
        )
    return score, f'Customer raised a concern ("{f.objection}"); agent responded with {_join(responses)}.'


def _score_appointment(f: _Facts) -> tuple[int, str]:
    if f.appointment_booked:
        when = f" for {_lower_first(f.appointment_time)}" if f.appointment_time else ""
        return 5, f"Asked for and booked the appointment{when}."
    if APPOINTMENT_ASK.search(f.parsed.agent):
        return 3, "Offered an appointment, but it was not booked."
    return 0, "Never asked to book an appointment."


def _score_next_step(f: _Facts) -> tuple[int, str]:
    agent = f.parsed.agent
    has_step = bool(NEXT_STEP.search(agent))
    has_time = bool(TIME_RE.search(agent) or WITHIN_TIME.search(agent))
    if has_step and has_time:
        return 5, "Ended with a specific next step and time."
    if has_step:
        return 3, "Described a next step, but without a specific time."
    if CUSTOMER_BURDEN.search(agent):
        return 1, "Left the next step to the customer (\"call back\") instead of owning it."
    if has_time:
        return 2, "Mentioned a time but did not state what happens next."
    return 0, "No next step was agreed before the call ended."


def _score_professional(f: _Facts) -> tuple[int, str]:
    agent = f.parsed.agent
    negatives = _distinct(UNPROFESSIONAL, agent)
    polite = bool(POLITE.search(agent))
    score = max(0, min(5, 3 + int(polite) + int(not negatives) - len(negatives)))
    if negatives:
        return score, f"Avoid casual or dismissive language: {_join(negatives)}."
    if polite:
        return score, "Courteous and professional throughout."
    return score, "Professional, but no courtesy phrases (thank you, please) used."


def _describe(done: list[str], missed: list[str], verb_done: str = "Included", verb_missed: str = "Missed") -> str:
    parts = []
    if done:
        parts.append(f"{verb_done} {_join(done)}.")
    if missed:
        parts.append(f"{verb_missed} {_join(missed)}.")
    return " ".join(parts)


SCORERS = {
    RubricCategory.OPENING_RAPPORT: _score_opening,
    RubricCategory.LEAD_QUALIFICATION: _score_qualification,
    RubricCategory.PROBLEM_DISCOVERY: _score_discovery,
    RubricCategory.SERVICE_AREA_URGENCY: _score_area_urgency,
    RubricCategory.VALUE_COMMUNICATION: _score_value,
    RubricCategory.OBJECTION_HANDLING: _score_objection,
    RubricCategory.APPOINTMENT_ATTEMPT: _score_appointment,
    RubricCategory.CLEAR_NEXT_STEP: _score_next_step,
    RubricCategory.PROFESSIONAL_COMMUNICATION: _score_professional,
}


def _lead_temperature(f: _Facts) -> LeadTemperature:
    if f.appointment_booked or f.urgency == Urgency.HIGH:
        return LeadTemperature.HOT
    if f.urgency == Urgency.MEDIUM or f.customer_phone or f.customer_email:
        return LeadTemperature.WARM
    return LeadTemperature.COLD


def _risk_flags(f: _Facts, scores: dict[RubricCategory, int], overall: int) -> list[str]:
    flags = []
    customer = f.parsed.customer
    if f.urgency == Urgency.HIGH and not f.appointment_booked:
        flags.append("High-urgency issue with no appointment booked; risk of losing the lead to a competitor.")
    if not f.customer_phone and not f.customer_email:
        flags.append("No callback number or email captured.")
    if f.objection and scores[RubricCategory.OBJECTION_HANDLING] <= 2:
        flags.append("Price or hesitation objection was not resolved.")
    if SAFETY.search(customer):
        flags.append("Possible safety hazard mentioned; prioritize the response.")
    if FRUSTRATION.search(customer):
        flags.append("Customer expressed frustration.")
    if overall < 50:
        flags.append("Low call-quality score; recommend manager review.")
    if not f.parsed.labeled:
        flags.append("Transcript has no speaker labels (e.g. 'Agent:', 'Customer:'); scores are approximate.")
    return flags


def _next_action(f: _Facts, temperature: LeadTemperature, scores: dict[RubricCategory, int]) -> str:
    service = _lower_first(f.service_type)
    if f.appointment_booked:
        when = _lower_first(f.appointment_time) if f.appointment_time else "the scheduled visit"
        return f"Send the appointment confirmation for {when} and brief the technician on the {service} request."
    if f.callback_time:
        return f"Make the promised callback {_lower_first(f.callback_time)} and offer two specific appointment slots."
    if temperature == LeadTemperature.HOT:
        return "Call back within 1 hour to book an urgent visit; offer the earliest available slot."
    if f.objection and scores[RubricCategory.OBJECTION_HANDLING] <= 2:
        return "Follow up within 24 hours with pricing context (free inspection, financing) and offer two appointment times."
    if temperature == LeadTemperature.WARM:
        return "Follow up within 24 hours and offer two specific appointment times."
    return "Add to the nurture sequence and follow up within 3 days."


def _follow_ups(f: _Facts) -> tuple[str, str, str]:
    company = COMPANY_BY_TYPE[f.business_type]
    first = f.customer_name.split()[0] if f.customer_name else "there"
    service = _lower_first(f.service_type)

    if f.appointment_booked:
        when = _lower_first(f.appointment_time) if f.appointment_time else "your scheduled visit"
        sms_step = f"You're confirmed for {when}."
        email_step = f"Your appointment is confirmed for {when}. You'll receive a reminder before the visit."
        cta = f"If you need to reschedule, just reply to this email or call us at {COMPANY_PHONE}."
        subject = f"Your {service} appointment is confirmed"
    elif f.callback_time:
        when = _lower_first(f.callback_time)
        sms_step = f"As promised, we'll call you {when}."
        email_step = f"As promised, we'll call you {when} to answer any questions and find a time that works for you."
        cta = f"If you're ready sooner, reply to this email or call us at {COMPANY_PHONE} to book your visit."
        subject = f"Next steps for your {service} request"
    else:
        sms_step = "We'd like to get a technician out to take a look. Reply with a day and time that works for you."
        email_step = (
            "The next step is a visit from one of our technicians to diagnose the problem "
            "and give you a clear, upfront estimate."
        )
        cta = f"Reply to this email or call us at {COMPANY_PHONE} to pick a time, and we'll get you on the schedule."
        subject = f"Next steps for your {service} request"

    sms = f"Hi {first}, thanks for calling {company} about your {service}. {sms_step} Questions? Call {COMPANY_PHONE}."
    email = (
        f"Hi {first},\n\n"
        f"Thank you for calling {company} about your {service}. "
        f'We know how disruptive this can be. You mentioned: "{f.customer_problem}"\n\n'
        f"{email_step}\n\n"
        "Our team is licensed and insured, and every estimate is provided upfront with no obligation.\n\n"
        f"{cta}\n\n"
        f"Best regards,\n{f.agent_name}\n{company}\n{COMPANY_PHONE}"
    )
    return sms, subject, email


def evaluate_transcript_mock(
    transcript: str,
    business_type: BusinessType = BusinessType.GENERIC,
    agent_name: str = "Agent",
) -> EvaluationResult:
    parsed = parse_transcript(transcript, agent_name)
    facts = _extract(parsed, business_type, agent_name)

    rubric: list[RubricScoreItem] = []
    for category, scorer in SCORERS.items():
        score, feedback = scorer(facts)
        rubric.append(RubricScoreItem(category=category, score=score, feedback=feedback))
    scores = {r.category: r.score for r in rubric}
    overall = compute_overall_score(rubric)

    strengths = [
        f"{r.category.value}: {r.feedback}"
        for r in rubric
        if r.score >= 4 and r.category not in facts.na_categories
    ]
    missed = [f"{r.category.value}: {r.feedback}" for r in rubric if r.score <= 2]
    weakest = min(rubric, key=lambda r: r.score)  # ties resolve to rubric order
    if weakest.score >= 4:
        coaching = "Strong call overall. Keep using this structure and share it as an example for the team."
    else:
        coaching = COACHING_TIPS[weakest.category]

    temperature = _lead_temperature(facts)
    next_action = _next_action(facts, temperature, scores)
    sms, subject, email = _follow_ups(facts)

    if facts.appointment_booked:
        appointment = f"Booked ({facts.appointment_time})" if facts.appointment_time else "Booked"
    elif facts.callback_time:
        appointment = f"Not booked; callback {_lower_first(facts.callback_time)}"
    else:
        appointment = "Not booked"
    crm_note = (
        f"{facts.customer_name or 'Unknown caller'} | {facts.customer_phone or 'no phone captured'} | "
        f"{facts.customer_email or 'no email captured'}\n"
        f"Service: {facts.service_type} at {facts.location or 'location not captured'}\n"
        f"Problem: {facts.customer_problem}\n"
        f"Urgency: {facts.urgency.value} | Lead: {temperature.value} | Appointment: {appointment}\n"
        f"Agent: {agent_name} | QA score: {overall}/100\n"
        f"Next action: {next_action}"
    )

    return EvaluationResult(
        customer_name=facts.customer_name,
        customer_phone=facts.customer_phone,
        customer_email=facts.customer_email,
        service_type=facts.service_type,
        location=facts.location,
        customer_problem=facts.customer_problem,
        urgency=facts.urgency,
        lead_temperature=temperature,
        appointment_booked=facts.appointment_booked,
        appointment_time=facts.appointment_time,
        overall_score=overall,
        rubric_scores=rubric,
        strengths=strengths,
        missed_opportunities=missed,
        coaching_recommendation=coaching,
        risk_flags=_risk_flags(facts, scores, overall),
        crm_note=crm_note,
        recommended_next_action=next_action,
        sms_follow_up=sms,
        email_subject=subject,
        email_follow_up=email,
    )

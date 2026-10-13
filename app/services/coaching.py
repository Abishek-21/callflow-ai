"""Turn stored rubric scores into team and per-agent coaching insights."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean

from app.schemas import (
    COACHING_TIPS,
    AgentCategoryScore,
    AgentCoaching,
    AgentGapCount,
    CategoryInsight,
    CoachingInsights,
    GapExample,
    RecurringGap,
    RubricCategory,
)

GAP_SCORE = 2  # same threshold as "missed opportunities" on a single call
RECURRING_MIN_CALLS = 2  # a gap on at least this many calls is "recurring"
FOCUS_BELOW = 3.0  # an agent's category average under this is a focus area
STRENGTH_AT = 4.0  # ...and at or above this, a strength (same as per-call strengths)
MAX_FOCUS_AREAS = 3
MAX_EXAMPLES = 3


@dataclass(frozen=True)
class ScoreRow:
    evaluation_id: int
    call_date: date
    agent_name: str
    overall_score: int
    category: RubricCategory
    score: int
    feedback: str


def _avg(values) -> float:
    return round(mean(values), 1)


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def build_insights(rows: list[ScoreRow]) -> CoachingInsights:
    """`rows` holds one entry per (call, category), newest call first."""
    overall_by_call: dict[int, int] = {}
    agent_by_call: dict[int, str] = {}
    by_category: dict[RubricCategory, list[ScoreRow]] = defaultdict(list)
    by_agent_category: dict[str, dict[RubricCategory, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        overall_by_call[row.evaluation_id] = row.overall_score
        agent_by_call[row.evaluation_id] = row.agent_name
        by_category[row.category].append(row)
        by_agent_category[row.agent_name][row.category].append(row.score)

    total = len(overall_by_call)
    categories = [c for c in RubricCategory if by_category[c]]

    insights = []
    gaps = []
    for category in categories:
        scored = by_category[category]
        gap_rows = [r for r in scored if r.score <= GAP_SCORE]
        insights.append(
            CategoryInsight(
                category=category,
                average_score=_avg(r.score for r in scored),
                calls=len(scored),
                gap_calls=len(gap_rows),
                gap_rate=_pct(len(gap_rows), len(scored)),
            )
        )
        if len(gap_rows) >= RECURRING_MIN_CALLS:
            per_agent: dict[str, int] = defaultdict(int)
            for r in gap_rows:
                per_agent[r.agent_name] += 1
            gaps.append(
                RecurringGap(
                    category=category,
                    gap_calls=len(gap_rows),
                    gap_rate=_pct(len(gap_rows), len(scored)),
                    agents=[
                        AgentGapCount(agent_name=name, gap_calls=n)
                        for name, n in sorted(per_agent.items(), key=lambda kv: (-kv[1], kv[0]))
                    ],
                    coaching_tip=COACHING_TIPS[category],
                    examples=[
                        GapExample(
                            evaluation_id=r.evaluation_id,
                            call_date=r.call_date,
                            agent_name=r.agent_name,
                            score=r.score,
                            feedback=r.feedback,
                        )
                        for r in gap_rows[:MAX_EXAMPLES]
                    ],
                )
            )

    agents = []
    for name, scores_by_category in by_agent_category.items():
        call_ids = [cid for cid, agent in agent_by_call.items() if agent == name]
        category_scores = [
            AgentCategoryScore(category=c, average_score=_avg(scores_by_category[c]))
            for c in RubricCategory
            if scores_by_category[c]
        ]
        ranked = sorted(category_scores, key=lambda s: s.average_score)  # stable: ties keep rubric order
        focus = [s.category for s in ranked if s.average_score < FOCUS_BELOW][:MAX_FOCUS_AREAS]
        best = max(category_scores, key=lambda s: s.average_score)
        agents.append(
            AgentCoaching(
                agent_name=name,
                calls=len(call_ids),
                average_score=_avg(overall_by_call[cid] for cid in call_ids),
                category_scores=category_scores,
                focus_areas=focus,
                strongest_area=best.category if best.average_score >= STRENGTH_AT else None,
                coaching_tip=COACHING_TIPS[focus[0]] if focus else None,
            )
        )

    return CoachingInsights(
        total_calls=total,
        gap_threshold=GAP_SCORE,
        recurring_gaps=sorted(gaps, key=lambda g: -g.gap_calls),
        category_insights=sorted(insights, key=lambda i: i.average_score),
        agents=sorted(agents, key=lambda a: (a.average_score, a.agent_name)),
    )

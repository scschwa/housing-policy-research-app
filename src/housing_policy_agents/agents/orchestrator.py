"""Deterministic intake and research-plan generation."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    BranchName,
    ClarificationQuestion,
    ManagerName,
    ResearchAssignment,
    ResearchBrief,
    ResearchPlan,
    ResearchProviderName,
    RunMode,
    SearchQuery,
    UserResearchRequest,
)


DEFAULT_AUDIENCE = "a sophisticated policy decision-maker"
DEFAULT_SCOPE = "U.S. policy design, implementation, effects, trade-offs, and uncertainty"
DEFAULT_HORIZON = "current baseline and a 5-to-10-year policy horizon"
DEFAULT_STAKEHOLDER = "balanced treatment of affected stakeholders"


@dataclass
class ClarificationDecision:
    questions: list[ClarificationQuestion]
    sufficient: bool


def decide_clarifications(request: UserResearchRequest) -> ClarificationDecision:
    questions: list[ClarificationQuestion] = []
    if not request.audience:
        questions.append(ClarificationQuestion(
            question_id="audience",
            prompt="Who is the primary decision-maker or audience for this research?",
            rationale="The report can prioritize different evidence and implementation details by audience.",
            options=["Legislative or regulatory staff", "Researchers", "Market or risk professionals", "Consumer or community advocates"],
            default=DEFAULT_AUDIENCE,
        ))
    if not request.policy_scope:
        questions.append(ClarificationQuestion(
            question_id="scope",
            prompt="What policy design, jurisdictional boundary, or comparison should be in scope?",
            rationale="A bounded scope prevents irrelevant branches and false precision.",
            default=DEFAULT_SCOPE,
        ))
    if not request.time_horizon:
        questions.append(ClarificationQuestion(
            question_id="time_horizon",
            prompt="What time horizon should the analysis emphasize?",
            rationale="Effects and evidence differ across immediate implementation and longer-run outcomes.",
            options=["Immediate implementation", "3-to-5 years", "5-to-10 years", "Long-run fiscal and systemic effects"],
            default=DEFAULT_HORIZON,
        ))
    if not request.stakeholder_perspective:
        questions.append(ClarificationQuestion(
            question_id="stakeholders",
            prompt="Should the report prioritize any stakeholder perspective?",
            rationale="The system is balanced by default but can emphasize the user's decision context.",
            options=["Balanced", "Consumer and community effects", "Market and financial risk", "Legal and implementation feasibility"],
            default=DEFAULT_STAKEHOLDER,
        ))
    return ClarificationDecision(questions=questions[:5], sufficient=not questions)


def build_brief(request: UserResearchRequest, answers: dict[str, str] | None = None) -> ResearchBrief:
    answers = answers or {}
    decision = decide_clarifications(request)
    defaults: list[str] = []

    def value(field: str, answer_key: str, default: str) -> str:
        explicit = getattr(request, field)
        if explicit:
            return explicit
        if answers.get(answer_key):
            return answers[answer_key]
        defaults.append(answer_key)
        return default

    return ResearchBrief(
        request_id=request.request_id,
        question=request.question,
        audience=value("audience", "audience", DEFAULT_AUDIENCE),
        jurisdiction=request.jurisdiction,
        policy_scope=value("policy_scope", "scope", DEFAULT_SCOPE),
        time_horizon=value("time_horizon", "time_horizon", DEFAULT_HORIZON),
        stakeholder_perspective=value("stakeholder_perspective", "stakeholders", DEFAULT_STAKEHOLDER),
        mode=request.mode,
        defaults_applied=defaults,
        clarification_questions=[] if request.accept_defaults or request.mode == RunMode.FAST else decision.questions,
        safety_disclosures=[
            "Research assistance only; not legal advice.",
            "Sources must be verified before formal reliance.",
            "Synthetic offline fixtures are not verified live evidence.",
        ],
    )


def _manager(branch: BranchName) -> ManagerName:
    if branch in {BranchName.GOVERNMENT, BranchName.LEGAL, BranchName.ACADEMIC}:
        return ManagerName.POLICY
    if branch in {BranchName.CONSUMER, BranchName.ORIGINATOR, BranchName.SERVICING, BranchName.RISK_TRANSFER}:
        return ManagerName.INDUSTRY
    if branch in {BranchName.GENERAL_ADVOCACY, BranchName.DISADVANTAGED_COMMUNITIES, BranchName.FINANCIAL_SUSTAINABILITY}:
        return ManagerName.ADVOCACY
    return ManagerName.GLOBAL


def select_branches(question: str) -> list[BranchName]:
    text = question.lower()
    branches = [BranchName.GOVERNMENT, BranchName.LEGAL, BranchName.ACADEMIC]
    mortgage = any(word in text for word in ["mortgage", "underwriting", "borrower", "credit", "servic", "foreclos", "securit"])
    consumer = any(word in text for word in ["consumer", "homebuyer", "access", "afford", "price", "rent", "tenant", "mobility", "equity", "distribution"])
    market = any(word in text for word in ["market", "taxpayer", "fiscal", "risk", "finance", "investor", "insurance", "capital"])
    if mortgage:
        branches.extend([BranchName.CONSUMER, BranchName.ORIGINATOR, BranchName.SERVICING, BranchName.RISK_TRANSFER])
    elif consumer:
        branches.append(BranchName.CONSUMER)
    if any(word in text for word in ["consumer", "tenant", "rent", "homebuyer", "fair", "advocacy", "choice"]) or consumer:
        branches.append(BranchName.GENERAL_ADVOCACY)
    if any(word in text for word in ["distribution", "equity", "racial", "rural", "first-generation", "underserved", "disadvantaged"]) or consumer:
        branches.append(BranchName.DISADVANTAGED_COMMUNITIES)
    if market or mortgage or consumer:
        branches.append(BranchName.FINANCIAL_SUSTAINABILITY)
    if any(word in text for word in ["international", "abroad", "foreign", "country", "countries", "comparator", "precedent", "learn from"]):
        branches.append(BranchName.GLOBAL)
    return list(dict.fromkeys(branches))


def _queries(branch: BranchName, question: str) -> list[SearchQuery]:
    purpose = {
        BranchName.GOVERNMENT: "current law, policy baseline, official analysis, and administrative data",
        BranchName.LEGAL: "authority, jurisdiction, legal constraints, and unresolved interpretations",
        BranchName.ACADEMIC: "empirical evidence, causal identification, models, and contrary research",
        BranchName.CONSUMER: "household effects, affordability, mobility, access, and behavior",
        BranchName.ORIGINATOR: "origination operations, underwriting, pricing, compliance, and incentives",
        BranchName.SERVICING: "servicing operations, transfers, loss mitigation, escrow, and communication",
        BranchName.RISK_TRANSFER: "prepayment, capital, guarantee, taxpayer, liquidity, and systemic risk",
        BranchName.GENERAL_ADVOCACY: "consumer protection, transparency, fees, market power, and remedies",
        BranchName.DISADVANTAGED_COMMUNITIES: "distributional outcomes, underserved communities, and displacement",
        BranchName.FINANCIAL_SUSTAINABILITY: "durability, adverse selection, moral hazard, fiscal exposure, and stress",
        BranchName.GLOBAL: "comparable foreign policy design, institutional differences, outcomes, and failures",
    }[branch]
    return [SearchQuery(text=question, purpose=purpose, branch=branch, max_results=5)]


def build_plan(brief: ResearchBrief) -> ResearchPlan:
    branches = select_branches(brief.question)
    assignments = [
        ResearchAssignment(
            branch=branch,
            manager=_manager(branch),
            objective=f"Analyze the question through the {branch.value.replace('_', ' ')} lens.",
            required_questions=[f"What does evidence say about {brief.question}?", "What is uncertain or contested?"],
            search_queries=_queries(branch, brief.question),
            max_sources=8,
        )
        for branch in branches
    ]
    rationale = {branch: f"Selected because the question contains terms relevant to {branch.value.replace('_', ' ')}." for branch in branches}
    return ResearchPlan(brief=brief, selected_branches=branches, assignments=assignments, branch_rationale=rationale, clarification_questions=brief.clarification_questions)

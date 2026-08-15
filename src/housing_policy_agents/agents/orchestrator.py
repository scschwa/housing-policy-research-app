"""Deterministic intake and research-plan generation."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    MAX_SEARCH_QUERY_CHARS,
    BranchName,
    ClarificationQuestion,
    ManagerName,
    ResearchAssignment,
    ResearchBrief,
    ResearchPlan,
    RunMode,
    SearchQuery,
    UserResearchRequest,
)

DEFAULT_AUDIENCE = "a sophisticated policy decision-maker"
DEFAULT_SCOPE = "U.S. policy design, implementation, effects, trade-offs, and uncertainty"
DEFAULT_HORIZON = "current baseline and a 5-to-10-year policy horizon"
DEFAULT_STAKEHOLDER = "balanced treatment of affected stakeholders"


@dataclass(frozen=True)
class BranchResearchProfile:
    role: str
    role_definition: str
    in_scope: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    preferred_sources: tuple[str, ...]
    research_dimensions: tuple[str, ...]


BRANCH_PROFILES: dict[BranchName, BranchResearchProfile] = {
    BranchName.GOVERNMENT: BranchResearchProfile(
        role="Government Sources Researcher",
        role_definition=(
            "Produce a claim-level record of authoritative public-sector evidence that lets the "
            "Policy Research Manager identify the current policy baseline, governing authority, "
            "implementation requirements, public evidence, unresolved issues, and contradictions."
        ),
        in_scope=(
            "statutory and regulatory authority",
            "current agency policy and program baseline",
            "official policy history and prior pilots",
            "government empirical analysis and administrative data",
            "officially documented borrower, market, taxpayer, and implementation effects",
        ),
        out_of_scope=(
            "general manufactured-housing background without a policy implication",
            "general industry feedback unless summarized in an official record",
            "legal conclusions beyond what the cited authority supports",
            "secondary commentary when the underlying government source is available",
        ),
        preferred_sources=(
            "statutes, regulations, court opinions, agency orders, Federal Register notices",
            "FHFA, HUD, CFPB, Treasury, Federal Reserve, GAO, CBO, CRS, and official GSE documents",
            "official hearings, testimony records, program evaluations, and administrative datasets",
        ),
        research_dimensions=(
            "current authority and policy status",
            "historical policy development and prior pilots",
            "officially documented borrower and market effects",
            "GSE, credit, capital, and taxpayer risk",
            "implementation, data, and consumer-protection requirements",
        ),
    ),
    BranchName.LEGAL: BranchResearchProfile(
        role="Legal and Regulatory Researcher",
        role_definition=(
            "Map the governing legal and regulatory constraints and distinguish controlling authority, "
            "agency interpretation, proposed policy, and unresolved legal questions."
        ),
        in_scope=(
            "statutes, regulations, charters, conservatorship and PSPA constraints",
            "FHFA approval, rulemaking, Duty to Serve, and agency authority",
            "state-law implementation issues where material to feasibility",
            "legal conditions, procedural requirements, and unresolved interpretations",
        ),
        out_of_scope=(
            "predicting litigation outcomes without authority or clearly labeled assumptions",
            "general market or consumer commentary unless it bears on implementation law",
            "formal legal advice or conclusions outside the cited jurisdiction",
        ),
        preferred_sources=(
            "U.S. Code, Code of Federal Regulations, Federal Register, agency orders and guidance",
            "official FHFA, Treasury, HUD, CFPB, GSE, CRS, GAO, and court materials",
            "reputable legal analysis only when primary authority is unavailable and clearly labeled",
        ),
        research_dimensions=(
            "current authority and permissible activity",
            "required legislative, regulatory, or FHFA action",
            "charter, conservatorship, and risk-governance constraints",
            "state-law title, lien, servicing, and enforcement variation",
            "unresolved interpretations and legal evidence gaps",
        ),
    ),
    BranchName.ACADEMIC: BranchResearchProfile(
        role="Think Tank and Academic Researcher",
        role_definition=(
            "Produce transparent empirical and analytical evidence, including contrary findings, "
            "that helps the Policy Research Manager assess mechanisms, magnitudes, and uncertainty."
        ),
        in_scope=(
            "peer-reviewed studies, working papers, think-tank analysis, and transparent models",
            "causal evidence, descriptive evidence, analogous markets, and methodological limits",
            "distributional, market, pricing, credit, and consumer-outcome research",
            "evidence that challenges or qualifies the policy mechanism",
        ),
        out_of_scope=(
            "treating an analogy as direct evidence about a GSE chattel program",
            "using a think-tank or industry position as controlling legal authority",
            "unsupported numerical estimates or consensus claims",
        ),
        preferred_sources=(
            "peer-reviewed research and transparent working papers",
            "Urban Institute, academic centers, Federal Reserve research, and methodologically explicit studies",
            "official datasets used with appropriate causal and measurement caveats",
        ),
        research_dimensions=(
            "mechanisms and expected effects",
            "empirical magnitude and causal identification",
            "analogous securitization, guarantee, or manufactured-housing evidence",
            "distributional and stakeholder effects",
            "contrary evidence, uncertainty, and transferability limits",
        ),
    ),
    BranchName.CONSUMER: BranchResearchProfile(
        role="Consumer Outcomes Researcher",
        role_definition=(
            "Assess borrower-facing consequences, affordability, access, terms, mobility, and consumer risk "
            "without treating aggregate access as equivalent to durable consumer benefit."
        ),
        in_scope=(
            "pricing, eligibility, access, loan terms, defaults, repossession, and wealth effects",
            "consumer protection, disclosure, servicing, and complaint evidence",
            "differences across borrower types and housing tenure arrangements",
        ),
        out_of_scope=(
            "legal conclusions, lender strategy, or advocacy claims presented as neutral facts",
            "unsupported claims that lower rates necessarily improve welfare",
        ),
        preferred_sources=(
            "CFPB, HUD, FHFA, GAO, Federal Reserve, official complaint and administrative data",
            "transparent household surveys and peer-reviewed consumer-finance research",
        ),
        research_dimensions=(
            "access and affordability",
            "terms, defaults, repossession, and servicing experience",
            "consumer protection and distributional effects",
        ),
    ),
    BranchName.ORIGINATOR: BranchResearchProfile(
        role="Loan Origination Researcher",
        role_definition=(
            "Analyze underwriting, pricing, compliance, capacity, incentives, and operational effects on originators."
        ),
        in_scope=(
            "underwriting standards, pricing, documentation, compliance, and capacity",
            "origination incentives, competition, adverse selection, and product design",
            "differences between mortgage and personal-property lending workflows",
        ),
        out_of_scope=(
            "treating lender statements as unbiased evidence",
            "legal advice or consumer outcomes outside origination mechanisms",
        ),
        preferred_sources=(
            "agency examinations, official program guidance, transparent market studies",
            "peer-reviewed lending research and clearly attributed industry evidence",
        ),
        research_dimensions=(
            "underwriting and pricing",
            "origination capacity and compliance",
            "incentives, competition, and adverse selection",
        ),
    ),
    BranchName.SERVICING: BranchResearchProfile(
        role="Servicing and Operations Researcher",
        role_definition=(
            "Identify servicing, title, loss-mitigation, repossession, communications, and systems requirements "
            "that could determine whether the policy works in practice."
        ),
        in_scope=(
            "servicing transfers, payment processing, loss mitigation, default, repossession, and disputes",
            "title, lien perfection, state-law variation, data, and operational controls",
            "borrower communications and consumer-protection implementation",
        ),
        out_of_scope=(
            "assuming mortgage servicing processes transfer unchanged to chattel loans",
            "speculative cost estimates without operational evidence",
        ),
        preferred_sources=(
            "agency servicing rules, GSE guides, CFPB/HUD materials, state-law sources",
            "transparent servicing studies and documented program experience",
        ),
        research_dimensions=(
            "servicing and loss mitigation",
            "title, repossession, and state-law operations",
            "data, controls, and borrower communications",
        ),
    ),
    BranchName.RISK_TRANSFER: BranchResearchProfile(
        role="Secondary Market and Risk Transfer Researcher",
        role_definition=(
            "Trace liquidity, securitization, capital, guarantee, credit-risk-transfer, systemic, and taxpayer mechanisms."
        ),
        in_scope=(
            "secondary-market liquidity, securitization, guarantee fees, capital, CRT, and risk retention",
            "credit performance, loss severity, investor demand, moral hazard, and taxpayer exposure",
            "stress scenarios and conditions for risk containment",
        ),
        out_of_scope=(
            "presenting a market analogy as a calibrated GSE forecast",
            "quantitative fiscal claims without disclosed assumptions and data",
        ),
        preferred_sources=(
            "FHFA, Treasury, Federal Reserve, GAO, CBO, official GSE CRT and capital documents",
            "peer-reviewed securitization and financial-risk research with transparent methods",
        ),
        research_dimensions=(
            "liquidity and market structure",
            "credit, capital, guarantee, and risk transfer",
            "stress, systemic, and taxpayer exposure",
        ),
    ),
    BranchName.GENERAL_ADVOCACY: BranchResearchProfile(
        role="General Consumer Advocacy Researcher",
        role_definition=(
            "Surface consumer-protection, transparency, market-power, remedy, and accountability concerns, "
            "clearly distinguishing advocacy positions from measured findings."
        ),
        in_scope=(
            "fees, disclosures, fair dealing, complaints, remedies, market power, and accountability",
            "consumer and resident advocacy positions with source provenance",
            "design safeguards and enforcement mechanisms",
        ),
        out_of_scope=(
            "representing a stakeholder position as neutral evidence",
            "legal conclusions or broad distributional claims without supporting evidence",
        ),
        preferred_sources=(
            "CFPB, HUD, FTC, agency comment records, complaint data, and enforcement materials",
            "transparent consumer-advocacy research and clearly attributed public comments",
        ),
        research_dimensions=(
            "consumer protection and transparency",
            "market power and remedies",
            "stakeholder positions and safeguards",
        ),
    ),
    BranchName.DISADVANTAGED_COMMUNITIES: BranchResearchProfile(
        role="Distributional Equity Researcher",
        role_definition=(
            "Analyze who benefits, who bears risk, and how geography, income, race, tenure, rurality, and "
            "institutional access may change the policy effects."
        ),
        in_scope=(
            "distributional outcomes across borrower, owner, renter, community, and geographic groups",
            "access, displacement, wealth, exclusion, and unintended consequences",
            "measurement gaps and subgroup-specific safeguards",
        ),
        out_of_scope=(
            "assuming aggregate affordability proves equitable benefit",
            "using demographic generalizations without evidence or uncertainty labels",
        ),
        preferred_sources=(
            "official demographic and housing datasets, HUD/CFPB/FHFA/GAO analysis",
            "peer-reviewed and transparent equity research with subgroup methods",
        ),
        research_dimensions=(
            "who gains and who bears risk",
            "geographic, income, racial, tenure, and rural differences",
            "equity safeguards and evidence gaps",
        ),
    ),
    BranchName.FINANCIAL_SUSTAINABILITY: BranchResearchProfile(
        role="Financial Sustainability Researcher",
        role_definition=(
            "Stress-test durability, incentives, fiscal exposure, adverse selection, moral hazard, and governance "
            "conditions without inventing a quantitative forecast."
        ),
        in_scope=(
            "downturns, defaults, rate shocks, adverse selection, moral hazard, and fiscal exposure",
            "governance, program limits, capital, monitoring, and exit conditions",
            "assumptions needed for credible stress analysis",
        ),
        out_of_scope=(
            "single-point fiscal estimates without a calibrated model",
            "treating historical GSE experience as direct evidence about chattel performance",
        ),
        preferred_sources=(
            "GAO, CBO, FHFA, Treasury, Federal Reserve, official stress and capital materials",
            "transparent financial-risk and public-finance research",
        ),
        research_dimensions=(
            "durability and stress scenarios",
            "fiscal, taxpayer, and governance exposure",
            "risk controls, monitoring, and exit triggers",
        ),
    ),
    BranchName.GLOBAL: BranchResearchProfile(
        role="International Comparator Researcher",
        role_definition=(
            "Identify genuinely comparable foreign policy designs and extract transferable mechanisms while "
            "making institutional differences explicit."
        ),
        in_scope=(
            "foreign programs with comparable housing-finance, guarantee, title, or risk-transfer mechanisms",
            "institutional differences, outcomes, implementation, and failure modes",
            "lessons that can be translated into conditional U.S. design questions",
        ),
        out_of_scope=(
            "listing countries without a policy mechanism or comparator reason",
            "directly transplanting foreign outcomes into the U.S. context",
            "international commentary unrelated to the assigned policy mechanism",
        ),
        preferred_sources=(
            "foreign government, central bank, regulator, multilateral, and official statistical sources",
            "peer-reviewed comparative research with clear institutional caveats",
        ),
        research_dimensions=(
            "comparable design and eligibility",
            "funding, risk allocation, and administration",
            "outcomes, failure modes, and transferability",
        ),
    ),
}


@dataclass
class ClarificationDecision:
    questions: list[ClarificationQuestion]
    sufficient: bool


def decide_clarifications(request: UserResearchRequest) -> ClarificationDecision:
    questions: list[ClarificationQuestion] = []
    if not request.audience:
        questions.append(
            ClarificationQuestion(
                question_id="audience",
                prompt="Who is the primary decision-maker or audience for this research?",
                rationale="The report can prioritize different evidence and implementation details by audience.",
                options=[
                    "Legislative or regulatory staff",
                    "Researchers",
                    "Market or risk professionals",
                    "Consumer or community advocates",
                ],
                default=DEFAULT_AUDIENCE,
            )
        )
    if not request.policy_scope:
        questions.append(
            ClarificationQuestion(
                question_id="scope",
                prompt="What policy design, jurisdictional boundary, or comparison should be in scope?",
                rationale="A bounded scope prevents irrelevant branches and false precision.",
                default=DEFAULT_SCOPE,
            )
        )
    if not request.time_horizon:
        questions.append(
            ClarificationQuestion(
                question_id="time_horizon",
                prompt="What time horizon should the analysis emphasize?",
                rationale="Effects and evidence differ across immediate implementation and longer-run outcomes.",
                options=[
                    "Immediate implementation",
                    "3-to-5 years",
                    "5-to-10 years",
                    "Long-run fiscal and systemic effects",
                ],
                default=DEFAULT_HORIZON,
            )
        )
    if not request.stakeholder_perspective:
        questions.append(
            ClarificationQuestion(
                question_id="stakeholders",
                prompt="Should the report prioritize any stakeholder perspective?",
                rationale="The system is balanced by default but can emphasize the user's decision context.",
                options=[
                    "Balanced",
                    "Consumer and community effects",
                    "Market and financial risk",
                    "Legal and implementation feasibility",
                ],
                default=DEFAULT_STAKEHOLDER,
            )
        )
    return ClarificationDecision(questions=questions[:5], sufficient=not questions)


def build_brief(
    request: UserResearchRequest,
    answers: dict[str, str] | None = None,
    clarification_enabled: bool = True,
) -> ResearchBrief:
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
        stakeholder_perspective=value(
            "stakeholder_perspective", "stakeholders", DEFAULT_STAKEHOLDER
        ),
        mode=request.mode,
        defaults_applied=defaults,
        clarification_questions=[]
        if (
            not clarification_enabled
            or request.accept_defaults
            or request.mode == RunMode.FAST
        )
        else decision.questions,
        safety_disclosures=[
            "Research assistance only; not legal advice.",
            "Sources must be verified before formal reliance.",
            "Synthetic offline fixtures are not verified live evidence.",
        ],
    )


def _manager(branch: BranchName) -> ManagerName:
    if branch in {BranchName.GOVERNMENT, BranchName.LEGAL, BranchName.ACADEMIC}:
        return ManagerName.POLICY
    if branch in {
        BranchName.CONSUMER,
        BranchName.ORIGINATOR,
        BranchName.SERVICING,
        BranchName.RISK_TRANSFER,
    }:
        return ManagerName.INDUSTRY
    if branch in {
        BranchName.GENERAL_ADVOCACY,
        BranchName.DISADVANTAGED_COMMUNITIES,
        BranchName.FINANCIAL_SUSTAINABILITY,
    }:
        return ManagerName.ADVOCACY
    return ManagerName.GLOBAL


def select_branches(question: str) -> list[BranchName]:
    text = question.lower()
    branches = [BranchName.GOVERNMENT, BranchName.LEGAL, BranchName.ACADEMIC]
    mortgage = any(
        word in text
        for word in [
            "mortgage",
            "underwriting",
            "borrower",
            "credit",
            "servic",
            "foreclos",
            "securit",
        ]
    )
    consumer = any(
        word in text
        for word in [
            "consumer",
            "homebuyer",
            "access",
            "afford",
            "price",
            "rent",
            "tenant",
            "mobility",
            "equity",
            "distribution",
        ]
    )
    market = any(
        word in text
        for word in [
            "market",
            "taxpayer",
            "fiscal",
            "risk",
            "finance",
            "investor",
            "insurance",
            "capital",
        ]
    )
    if mortgage:
        branches.extend(
            [
                BranchName.CONSUMER,
                BranchName.ORIGINATOR,
                BranchName.SERVICING,
                BranchName.RISK_TRANSFER,
            ]
        )
    elif consumer:
        branches.append(BranchName.CONSUMER)
    if (
        any(
            word in text
            for word in ["consumer", "tenant", "rent", "homebuyer", "fair", "advocacy", "choice"]
        )
        or consumer
    ):
        branches.append(BranchName.GENERAL_ADVOCACY)
    if (
        any(
            word in text
            for word in [
                "distribution",
                "equity",
                "racial",
                "rural",
                "first-generation",
                "underserved",
                "disadvantaged",
            ]
        )
        or consumer
    ):
        branches.append(BranchName.DISADVANTAGED_COMMUNITIES)
    if market or mortgage or consumer:
        branches.append(BranchName.FINANCIAL_SUSTAINABILITY)
    if any(
        word in text
        for word in [
            "international",
            "abroad",
            "foreign",
            "country",
            "countries",
            "comparator",
            "precedent",
            "learn from",
        ]
    ):
        branches.append(BranchName.GLOBAL)
    return list(dict.fromkeys(branches))


def _compact_search_query(question: str) -> str:
    """Bound a search hint while preserving the full question in the assignment."""
    normalized = " ".join(question.split())
    if len(normalized) <= MAX_SEARCH_QUERY_CHARS:
        return normalized

    separator = " ... "
    available = MAX_SEARCH_QUERY_CHARS - len(separator)
    head_budget = (available * 2) // 3
    tail_budget = available - head_budget
    head = normalized[:head_budget].rsplit(" ", 1)[0] or normalized[:head_budget]
    tail_fragment = normalized[-tail_budget:]
    tail = (
        tail_fragment.split(" ", 1)[1]
        if " " in tail_fragment
        else tail_fragment
    )
    return f"{head}{separator}{tail}"


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
    return [
        SearchQuery(
            text=_compact_search_query(question),
            purpose=purpose,
            branch=branch,
            max_results=5,
        )
    ]


def build_plan(brief: ResearchBrief) -> ResearchPlan:
    branches = select_branches(brief.question)
    assignments: list[ResearchAssignment] = []
    for branch in branches:
        profile = BRANCH_PROFILES[branch]
        manager = _manager(branch)
        siblings = [
            item.value.replace("_", " ")
            for item in branches
            if item != branch and _manager(item) == manager
        ]
        sibling_text = ", ".join(siblings) if siblings else "none selected"
        research_context = (
            f"This is one bounded branch of a multi-agent housing-policy research workflow. "
            f"The {manager.value.replace('_', ' ').title()} will reconcile your finding with sibling "
            f"branches ({sibling_text}) before handing an evidence package to the synthesis writer. "
            f"The downstream report is for {brief.audience}, covers {brief.jurisdiction}, and "
            f"uses the scope '{brief.policy_scope}' over {brief.time_horizon}. Do not duplicate "
            "other branches when you can identify a distinct contribution; flag questions that "
            "must be answered by a sibling branch."
        )
        objective = (
            f"{profile.role_definition} Focus on the policy question rather than a general topic "
            f"overview. Produce evidence the manager can compare with sibling findings and use in "
            "a decision-ready report."
        )
        handoff_instructions = [
            "Return claim-level evidence and a concise synthesis, not a narrative research memo.",
            "Distinguish current, proposed, historical, pilot, analytical, and stakeholder evidence.",
            "Record contrary evidence, material limitations, and unresolved questions for the manager.",
            "Use short stable source IDs (for example s1 or s_fhfa_chattel); put the complete URL only in the source url field.",
            "Use those same source IDs in every claim, contradiction, comparison, and source_ids reference.",
            "Before returning, verify every cited source ID exists in discovered_sources and that every source has a title, URL when available, source type, tier, and excerpt.",
            "Return only the typed finding object: no Markdown fences, preamble, commentary, or trailing text.",
        ]
        assignments.append(
            ResearchAssignment(
                branch=branch,
                manager=manager,
                objective=objective,
                research_context=research_context,
                in_scope=list(profile.in_scope),
                out_of_scope=list(profile.out_of_scope),
                preferred_sources=list(profile.preferred_sources),
                policy_decisions_supported=[
                    "which consequences are established by evidence versus conditional or speculative",
                    "whether the policy design should be explored, piloted, narrowed, or rejected",
                    "what safeguards, implementation conditions, or risk controls are necessary",
                    "what additional evidence, data, or modeling the manager should request",
                ],
                handoff_instructions=handoff_instructions,
                required_questions=[
                    f"What does the relevant evidence establish about {brief.question}?",
                    "What is uncertain, contested, proposed rather than current, or dependent on assumptions?",
                    "What should the manager ask the sibling branches or carry into implementation analysis?",
                ],
                search_queries=_queries(branch, brief.question),
                max_sources=8,
            )
        )
    rationale = {
        branch: f"Selected because the question contains terms relevant to {branch.value.replace('_', ' ')}."
        for branch in branches
    }
    return ResearchPlan(
        brief=brief,
        selected_branches=branches,
        assignments=assignments,
        branch_rationale=rationale,
        clarification_questions=brief.clarification_questions,
    )

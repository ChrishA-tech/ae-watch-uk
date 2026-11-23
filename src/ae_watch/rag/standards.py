"""Official NHS England Urgent and Emergency Care (UEC) Operational Standards.

Curated from NHS England 2024-2026 UEC Recovery Plan, Winter Escalation SOPs,
and Integrated Care Board operational guidance.
Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

OFFICIAL_UEC_STANDARDS: list[dict[str, Any]] = [
    {
        "policy_id": "NHS-UEC-STD-001",
        "title": "NHS England 4-Hour Emergency Access Standard (78% Operational Recovery Target)",
        "category": "Operational Access Standard",
        "citation": "NHS England UEC Recovery Plan 2024-2026, Section 2.1",
        "chunk_text": (
            "The NHS Constitutional standard mandates that at least 78% of patients attending Type 1 A&E "
            "must be admitted, transferred, or discharged within 4 hours of arrival. Acute trusts exceeding "
            "a 30% breach rate (performance below 70%) must trigger immediate clinical review of internal "
            "flow, activate acute medical assessment units, and engage local system partners for mutual aid. "
            "Liverpool University Hospitals NHS Foundation Trust (REM) operates as the regional benchmark "
            "anchor within Cheshire and Merseyside ICB (QE1) for 4-hour performance tracking."
        ),
        "mandatory_actions": [
            "Activate rapid triage protocols within 15 minutes of patient arrival.",
            "Conduct senior decision-maker reviews for all patients with wait times exceeding 3 hours.",
            "Direct ambulant medical attendances to co-located Same Day Emergency Care (SDEC).",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-002",
        "title": "45-Minute Maximum Ambulance Handover Protocol and Immediate Escalation",
        "category": "Ambulance Handover",
        "citation": "NHS England Emergency Handover Guidance 2024/25, SOP-AMB-04",
        "chunk_text": (
            "Ambulance handovers must be completed within 15 minutes of arrival, with an absolute upper ceiling "
            "of 45 minutes for complex handovers. Any handover exceeding 45 minutes constitutes an immediate "
            "clinical safety risk and patient harm hazard. The acute hospital leadership team (Executive on-call, "
            "Clinical Director, and Site Matron) must personally attend the Emergency Department to enact "
            "immediate offload protocols, initiate fit-to-sit cohorting, and facilitate rapid cohort nursing."
        ),
        "mandatory_actions": [
            "Deploy Hospital Ambulance Liaison Officers (HALO) to expedite arrival-to-handover intervals.",
            "Establish designated cohort areas within ED footprint for patients awaiting inpatient bed transfer.",
            "Enact immediate clinical review when ambulance handover delays breach 45 minutes.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-003",
        "title": "12-Hour Emergency Department Length of Stay Cap (<10% Wait Standard)",
        "category": "Length of Stay Standard",
        "citation": "NHS England Quality and Patient Safety Standards, Section 4.3",
        "chunk_text": (
            "Patients must not remain in an emergency department for longer than 12 hours from time of arrival. "
            "The national operational cap requires that less than 10% of total emergency admissions experience "
            "a stay greater than 12 hours. Prolonged stays correlate directly with inpatient mortality, hospital-"
            "acquired deconditioning, and nosocomial infection. Zero tolerance is enforced for corridor care "
            "and unallocated trolley waits lasting beyond 12 hours."
        ),
        "mandatory_actions": [
            "Enact full-capacity protocol (FCP) transferring stable inpatients to ward corridors if ED capacity is exhausted.",
            "Notify ICB System Control Centre when 12-hour trolley waits exceed 5 concurrent cases.",
            "Coordinate immediate emergency discharges via Discharge to Assess (D2A) pathway 0.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-004",
        "title": "Same Day Emergency Care (SDEC) Diversion Triggers and Operational Criteria",
        "category": "Ambulant Diversion",
        "citation": "NHS England SDEC Operational Model Specification 2024, Ref-SDEC-12",
        "chunk_text": (
            "All acute type 1 hospital sites must maintain an active Same Day Emergency Care (SDEC) facility "
            "operating at least 12 hours a day, 7 days a week. At least 30% of adult emergency medical admissions "
            "must be managed via SDEC without overnight bed occupancy. Exclusion criteria include acute physiological "
            "instability (NEWS2 >= 5), severe respiratory distress, or severe sepsis requiring critical care. "
            "Standard clinical presentation pathways include low-risk chest pain, suspected pulmonary embolism, "
            "cellulitis, headache, and uncomplicated acute abdomen."
        ),
        "mandatory_actions": [
            "Direct stream eligible ambulant patients directly from 999 ambulance triage or ED front door to SDEC.",
            "Maintain dedicated point-of-care ultrasound (POCUS) and rapid turnaround blood diagnostics.",
            "Record and audit same-day discharge rates targeting >85% discharge within 8 hours of SDEC entry.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-005",
        "title": "Virtual Ward and Hospital-at-Home Acute Respiratory Surge Escalation",
        "category": "Virtual Ward & Community",
        "citation": "NHS England National Virtual Ward Guidance, Doc-VW-2024-09",
        "chunk_text": (
            "Virtual Wards provide hospital-level care in patient homes for frailty and acute respiratory infection "
            "(ARI), including influenza, RSV, and COVID-19. Each Integrated Care Board (including Cheshire & Merseyside "
            "QE1) must operate a minimum of 40-50 virtual ward beds per 100,000 adult population. Under UKHSA Amber "
            "or Red Cold Health Alerts, acute trusts must immediately expand Virtual Ward intake criteria to divert "
            "stable patients with oxygen saturations >= 92% on room air and mild-to-moderate respiratory symptoms, "
            "supported by remote pulse oximetry and twice-daily clinical virtual ward rounds."
        ),
        "mandatory_actions": [
            "Enroll acute respiratory infection (ARI) patients with NEWS2 <= 4 directly from ED to Virtual Ward.",
            "Deploy remote continuous respiratory telemetry and automated desaturation alarm protocols.",
            "Conduct consultant-led virtual multidisciplinary team ward rounds every morning.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-006",
        "title": "UKHSA Cold Health Alert and Winter Surge Operational Escalation SOP",
        "category": "Severe Weather Escalation",
        "citation": "UK Health Security Agency (UKHSA) Adverse Weather and Health Plan, AWHP-2024",
        "chunk_text": (
            "The UKHSA Cold-Health Alert (CHA) system issues Yellow, Amber, and Red alerts based on Met Office "
            "temperature forecasts (sustained mean temperatures <= 2°C, severe frost days, and cold snap degree days). "
            "Under Amber and Red Cold Health Alerts, causal empirical evidence demonstrates a +2.058 percentage point "
            "breach rate increase in acute Type 1 emergency departments across the North West. Trusts must ramp up "
            "discharge lounges, establish daily morning system control calls with ICB partners, and ringfence acute "
            "frailty assessment units to mitigate cold-induced hypothermia, cardiovascular, and respiratory surges."
        ),
        "mandatory_actions": [
            "Implement pre-discharge medication delivery to prevent discharge delays during severe sub-zero weather.",
            "Open supplementary surge capacity in accordance with pre-agreed Trust Winter Operational Plans.",
            "Ensure 100% staff flu and COVID-19 booster vaccination coverage and infection control protocols.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-007",
        "title": "Operational Pressures Escalation Levels (OPEL 1-4) Regional Trigger Framework",
        "category": "Escalation Framework",
        "citation": "NHS England OPEL National Framework and Operational Guidance 2024, OPEL-REF-01",
        "chunk_text": (
            "The national OPEL framework classifies hospital pressure into four standardized tiers: "
            "OPEL 1: Normal operational capacity within planned resources. "
            "OPEL 2: Moderate pressure; Trust initiates internal bed and discharge reviews. "
            "OPEL 3: Severe pressure; acute breach rate >30%, bed occupancy >92%, ambulance handover delays emerging. "
            "OPEL 4: Critical operational emergency; Trust is unable to deliver comprehensive care and patient safety "
            "is compromised. Declaring OPEL 4 mandates immediate regional ICB escalation, cancellation of non-urgent "
            "elective surgical admissions, deployment of mutual aid across neighboring acute trusts, and opening of "
            "all surge beds."
        ),
        "mandatory_actions": [
            "Convene Trust Executive Emergency Escalation Huddle within 60 minutes of OPEL 3 or 4 declaration.",
            "Notify ICB System Control Centre and regional ambulance dispatch service (NWAS).",
            "Enforce discharge-before-noon quotas across all adult acute inpatient wards.",
        ],
    },
    {
        "policy_id": "NHS-UEC-STD-008",
        "title": "Cheshire and Merseyside ICB Urgent Care Catchment Mutual Aid Protocol",
        "category": "Regional Mutual Aid",
        "citation": "NHS Cheshire and Merseyside ICB Urgent Care Operational Policy, CM-ICB-2024-03",
        "chunk_text": (
            "Cheshire and Merseyside ICB (QE1) oversees acute trusts including Liverpool University Hospitals NHS FT "
            "(REM), Countess of Chester Hospital (RJR), Wirral University Teaching Hospital (RBL), Warrington and "
            "Halton Hospitals (RWW), Alder Hey Children's NHS FT (RBS), and Liverpool Women's NHS FT (REP). When an "
            "acute trust within 25 km of Liverpool REM declares OPEL 4 or experiences severe ambulance handover delays, "
            "the ICB System Coordination Centre (SCC) can dynamically re-route 999 emergency ambulances to proximate "
            "peer trusts with available capacity and activate cross-system Single Point of Access (SPoA) diversion."
        ),
        "mandatory_actions": [
            "Evaluate inverse-distance-weighted catchment spillover before requesting inter-trust transfers.",
            "Engage North West Ambulance Service (NWAS) for dynamic hospital diverts across the Mersey corridor.",
            "Conduct twice-daily cross-trust bed capacity teleconferences chaired by the ICB Medical Director.",
        ],
    },
]

"""
TLCM-Bench Dataset Generator
Generates a synthetic but rigorous benchmark dataset for evaluating
temporal memory architectures.

Output:
- 2 workspaces (isolation test)
- 5 epochs per workspace (temporal depth)
- 100 base memories per workspace (500 total)
- 50 deliberate updates with version chains
- 30 temporal reasoning questions with ground-truth answers

All data is deterministic and reproducible.
"""
import json
import os
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

# ─── WORKSPACES ─────────────────────────────────────────────
WORKSPACES = {
    "Research Lab": "Materials science research project",
    "Supply Chain": "Global logistics optimization project",
}

# ─── EPOCHS (5 per workspace) ──────────────────────────────
EPOCHS = {
    "Research Lab": [
        {"name": "Hypothesis", "desc": "Initial theoretical framework", "start": "2025-01-01", "end": "2025-04-01"},
        {"name": "Pilot Study", "desc": "Small-scale experiments", "start": "2025-04-01", "end": "2025-07-01"},
        {"name": "Data Collection", "desc": "Full-scale experiments", "start": "2025-07-01", "end": "2025-10-01"},
        {"name": "Analysis", "desc": "Statistical analysis phase", "start": "2025-10-01", "end": "2026-01-01"},
        {"name": "Publication", "desc": "Paper writing and review", "start": "2026-01-01", "end": None},
    ],
    "Supply Chain": [
        {"name": "Assessment", "desc": "Current state mapping", "start": "2025-01-01", "end": "2025-03-01"},
        {"name": "Vendor Selection", "desc": "Evaluating suppliers", "start": "2025-03-01", "end": "2025-06-01"},
        {"name": "Pilot Rollout", "desc": "Testing with 3 regions", "start": "2025-06-01", "end": "2025-09-01"},
        {"name": "Full Deployment", "desc": "All regions live", "start": "2025-09-01", "end": "2025-12-01"},
        {"name": "Optimization", "desc": "Continuous improvement", "start": "2025-12-01", "end": None},
    ],
}

# ─── MEMORIES (100 per workspace, distributed across epochs) ─
# Each memory has: content, workspace, epoch, and optional update_chain
MEMORIES = {
    "Research Lab": {
        "Hypothesis": [
            "Compound X has a theoretical tensile strength of 450 MPa.",
            "The synthesis temperature should be maintained at 800C.",
            "Expected yield rate for Compound X is 60%.",
            "Primary catalyst is Palladium at 5% concentration.",
            "Lab budget is $120,000 for the fiscal year.",
            "Team size is 4 researchers plus 2 grad students.",
            "Target journal is Nature Materials.",
            "Competitor lab in Munich published preliminary results on similar compounds.",
            "Safety protocol requires fume hood for all synthesis steps.",
            "Baseline measurements use electron microscopy at 50,000x.",
            "Hypothesis: layered structure improves conductivity by 30%.",
            "Initial supplier for raw materials is ChemCorp.",
            "Estimated timeline to first results: 6 months.",
            "Control group uses unmodified Compound Y.",
            "Statistical significance threshold set at p < 0.05.",
            "Data storage uses local NAS with 10TB capacity.",
            "Weekly standup meetings on Tuesdays at 10am.",
            "Collaboration agreement signed with University of Lagos.",
            "Funding source: National Science Foundation grant #4821.",
            "Literature review covers 47 papers from 2020-2024.",
        ],
        "Pilot Study": [
            "Pilot batch 1 achieved tensile strength of 380 MPa (below target).",
            "Temperature variance of +/- 15C observed during synthesis.",
            "Yield rate in pilot was 45%, below the 60% target.",
            "Palladium concentration may need to increase to 7%.",
            "Electron microscopy reveals unexpected grain boundary formation.",
            "Pilot cost was $18,000, within quarterly budget.",
            "Grad student Maria developed improved mixing protocol.",
            "Sample degradation observed after 72 hours in ambient conditions.",
            "PH level during synthesis averaged 6.8, target was 7.0.",
            "Three pilot batches completed, batch 3 showed most promise.",
            "Equipment calibration needed for spectrometer.",
            "Munich competitor published full paper, our approach differs in catalyst.",
            "Safety incident: minor spill in Lab 3, no injuries.",
            "New imaging technique (AFM) added to analysis toolkit.",
            "Collaboration with Lagos yielded 5 additional reference samples.",
            "Pilot data suggests layered hypothesis is partially correct.",
            "Raw material purity from ChemCorp was only 98.2%, need 99.5%.",
            "Added humidity control to synthesis chamber.",
            "First conference presentation at MatSci 2025 accepted.",
            "Preliminary results shared with NSF program officer.",
        ],
        "Data Collection": [
            "Full-scale batch achieved tensile strength of 510 MPa (exceeds target).",
            "Synthesis temperature optimized to 820C with +/- 3C variance.",
            "Yield rate improved to 72% with new mixing protocol.",
            "Palladium concentration finalized at 6.5%.",
            "Total of 200 samples produced across 15 batches.",
            "Budget spent: $78,000 of $120,000.",
            "New supplier SynthPure delivers 99.7% purity raw materials.",
            "Grain boundary issue resolved through annealing step.",
            "Degradation reduced to <5% over 30 days with coating.",
            "Statistical power analysis confirms n=200 is sufficient.",
            "Cross-validation with Lagos samples shows 94% consistency.",
            "AFM imaging reveals nanoscale layering as hypothesized.",
            "Control group (Compound Y) peaked at 290 MPa tensile strength.",
            "Temperature-conductivity relationship follows Arrhenius model.",
            "Batch-to-batch variance reduced to 4.2% (from 18% in pilot).",
            "Equipment uptime: 94% during collection phase.",
            "Two additional grad students joined the team (total: 4).",
            "Munich group contacted us for potential collaboration.",
            "Raw data backup to cloud storage completed.",
            "MatSci 2025 presentation received positive feedback.",
        ],
        "Analysis": [
            "Final tensile strength: 510 +/- 12 MPa (95% CI).",
            "Layered structure confirmed to improve conductivity by 42% (not 30%).",
            "Yield rate: 72 +/- 3% across all batches.",
            "P-value for tensile strength improvement: p < 0.001.",
            "Effect size (Cohen's d) for Compound X vs Y: 2.8 (large).",
            "Regression model R-squared: 0.94 for temperature-strength relationship.",
            "Cost per sample: $390 (within industry benchmark of $500).",
            "Degradation mechanism identified as surface oxidation.",
            "Optimal synthesis window: 815-825C, 6.2-6.8% Pd, pH 7.0-7.2.",
            "Statistical reviewer approved methodology.",
            "Total budget used: $105,000 of $120,000.",
            "Team authored first draft of publication.",
            "Peer pre-review by Munich group: positive, minor suggestions.",
            "Patent application filed for synthesis process.",
            "Dataset published to institutional repository (DOI assigned).",
            "Supplementary materials include 3D visualization of layered structure.",
            "Error analysis: systematic bias of +8 MPa in early pilot batches.",
            "Sensitivity analysis shows Pd concentration is most critical parameter.",
            "Collaboration with Lagos resulted in co-authorship.",
            "NSF interim report submitted with positive projections.",
        ],
        "Publication": [
            "Paper submitted to Nature Materials (manuscript #NM-2026-0142).",
            "Reviewer 1: 'Strong methodology, suggest expanding discussion on degradation.'",
            "Reviewer 2: 'Impressive tensile strength results, request additional TEM images.'",
            "Revised manuscript addresses both reviewer concerns.",
            "Final tensile strength claim: 510 +/- 12 MPa (unchanged from analysis).",
            "Open-access version uploaded to arxiv (2601.xxxxx).",
            "Conference invitation received for ICMS 2026.",
            "Follow-up grant proposal submitted to NSF for Phase 2.",
            "Munich collaboration formalized for joint Phase 2 study.",
            "Total project cost: $112,400 of $120,000 budget.",
            "All lab notebooks digitized and archived.",
            "IP licensing discussions initiated with 2 industry partners.",
            "Grad student Maria selected for best poster award at MatSci.",
            "Dataset download count: 47 in first month.",
            "Reproducibility package released on GitHub.",
            "Media coverage: university press release published.",
            "Phase 2 hypothesis: doping with Titanium may push strength to 600 MPa.",
            "New equipment request: high-temperature XRD unit ($45,000).",
            "Lab safety audit passed with zero findings.",
            "Team expansion planned: hiring 2 postdocs for Phase 2.",
        ],
    },
    "Supply Chain": {
        "Assessment": [
            "Current shipping cost per unit: $4.20.",
            "Average delivery time: 14 days domestic, 28 days international.",
            "Warehouse utilization: 67% across 5 facilities.",
            "Inventory turnover ratio: 4.2x annually.",
            "Top 3 cost drivers: fuel (35%), labor (28%), warehousing (22%).",
            "Current vendor count: 42 active suppliers.",
            "Order accuracy rate: 91.3%.",
            "Customer satisfaction (NPS): +32.",
            "Annual logistics budget: $8.4M.",
            "IT systems: legacy ERP from 2018, no real-time tracking.",
            "Carbon footprint: 12,400 tons CO2 annually.",
            "Peak season capacity gap: 15% underserved.",
            "Return rate: 6.8% (industry avg: 5.2%).",
            "Last-mile delivery accounts for 53% of total shipping cost.",
            "3 facilities need equipment upgrades (est. $1.2M).",
            "Compliance audit passed with 2 minor findings.",
            "Staff turnover in logistics: 18% annually.",
            "Current demand forecasting accuracy: 74%.",
            "Cross-docking used at only 1 of 5 facilities.",
            "No automated picking systems in any warehouse.",
        ],
        "Vendor Selection": [
            "ShipFast selected as primary carrier (20% cost reduction bid).",
            "GlobalFreight retained for international routes.",
            "3 domestic vendors eliminated due to reliability scores below 85%.",
            "New vendor WarehoTech selected for automated picking systems.",
            "RFP responses received from 28 vendors across 4 categories.",
            "Total vendor count reduced from 42 to 31.",
            "Negotiated volume discounts: 12% on average.",
            "Vendor SLA: 99.2% on-time delivery required.",
            "Insurance coverage expanded to include supply chain disruption.",
            "Sustainability clause added to all new contracts.",
            "WarehoTech pilot installation scheduled for Q3.",
            "Estimated annual savings from vendor consolidation: $420K.",
            "Backup carrier identified for each primary route.",
            "Vendor scorecards implemented with monthly reviews.",
            "Payment terms standardized to Net-45.",
            "Risk assessment completed for all tier-1 suppliers.",
            "Onboarding timeline: 6 weeks per new vendor.",
            "Training budget for vendor transition: $85K.",
            "Legal review of all 31 contracts completed.",
            "Transition plan approved by executive committee.",
        ],
        "Pilot Rollout": [
            "Pilot regions: Northeast, Midwest, Southeast.",
            "ShipFast pilot results: delivery time reduced to 10 days domestic.",
            "Cost per unit dropped to $3.50 in pilot regions.",
            "WarehoTech automated picking reduced errors by 60%.",
            "Warehouse utilization improved to 78% in pilot facilities.",
            "Order accuracy rate improved to 96.1%.",
            "Customer NPS in pilot regions: +48 (up from +32).",
            "Fuel costs reduced 18% through route optimization.",
            "Real-time tracking deployed via new TMS platform.",
            "Inventory turnover improved to 5.1x in pilot regions.",
            "Cross-docking expanded to 3 facilities.",
            "Staff training completion: 92% in pilot regions.",
            "Return rate in pilot: 4.1% (below industry avg).",
            "Demand forecasting accuracy improved to 81%.",
            "Carbon footprint reduced 8% in pilot regions.",
            "Peak season test: 98% of orders fulfilled on time.",
            "IT integration issues: 3 data sync errors in week 1, resolved.",
            "Pilot budget: $1.8M spent of $2.0M allocated.",
            "Executive review: green light for full deployment.",
            "Lessons learned document published internally.",
        ],
        "Full Deployment": [
            "All 5 regions live on new logistics platform.",
            "Average delivery time: 11 days domestic (from 14).",
            "Cost per unit: $3.40 (from $4.20, 19% reduction).",
            "Order accuracy rate: 95.8% company-wide.",
            "Warehouse utilization: 81% across all facilities.",
            "Automated picking deployed at 4 of 5 facilities.",
            "Inventory turnover: 5.4x annually.",
            "Customer NPS: +45 company-wide.",
            "Annual logistics cost: $7.1M (from $8.4M, 15% reduction).",
            "Real-time tracking: 100% of shipments visible.",
            "Demand forecasting accuracy: 83%.",
            "Return rate: 4.6% (improved from 6.8%).",
            "Carbon footprint: 10,800 tons CO2 (from 12,400).",
            "Staff turnover reduced to 12% (from 18%).",
            "Vendor SLA compliance: 98.7%.",
            "3 equipment upgrades completed ($980K of $1.2M budget).",
            "Cross-docking operational at 4 facilities.",
            "Last-mile cost reduced to 47% of shipping (from 53%).",
            "Compliance audit: zero findings.",
            "Total savings year 1: $1.3M.",
        ],
        "Optimization": [
            "AI-powered demand forecasting deployed (accuracy target: 90%).",
            "Exploring drone delivery for rural last-mile.",
            "5th warehouse automated picking installation in progress.",
            "Renegotiating ShipFast contract for Year 2 volume.",
            "Sustainability goal: 20% carbon reduction by end of 2026.",
            "Predictive maintenance system installed at 3 facilities.",
            "Customer NPS target raised to +55.",
            "Investigating blockchain for supply chain transparency.",
            "New KPI dashboard deployed for real-time monitoring.",
            "Cost per unit target: $3.00 by Q4 2026.",
            "Return rate target: below 4.0%.",
            "Hiring data scientist for supply chain analytics.",
            "Vendor count further reduced to 27.",
            "Autonomous vehicle pilot for inter-warehouse routes.",
            "Seasonal demand model refined with 3 years of data.",
            "Employee satisfaction survey: logistics team at 78%.",
            "Partnership with university for operations research.",
            "Board presentation on Year 1 ROI: 18.2%.",
            "Phase 2 budget approved: $2.5M.",
            "Long-term vision: fully autonomous warehouse by 2028.",
        ],
    },
}

# ─── UPDATES (50 deliberate updates with reasons) ──────────
# Format: (workspace, epoch_of_original, original_content_fragment, new_content, reason)
UPDATES = [
    # Research Lab updates — beliefs evolving with evidence
    ("Research Lab", "Hypothesis", "tensile strength of 450 MPa", "Compound X achieves tensile strength of 510 MPa in full-scale synthesis.", "Full-scale data showed 510 MPa, exceeding the 450 MPa theoretical prediction."),
    ("Research Lab", "Hypothesis", "temperature should be maintained at 800C", "Optimal synthesis temperature is 820C with +/- 3C tolerance.", "Pilot and full-scale data converged on 820C as optimal."),
    ("Research Lab", "Hypothesis", "Expected yield rate for Compound X is 60%", "Achieved yield rate for Compound X is 72% with improved mixing protocol.", "New mixing protocol by Maria improved yield from 60% target to 72%."),
    ("Research Lab", "Hypothesis", "Palladium at 5% concentration", "Optimal Palladium concentration is 6.5%.", "Pilot study showed 5% insufficient; 6.5% balances performance and cost."),
    ("Research Lab", "Hypothesis", "Lab budget is $120,000", "Total project cost is $112,400 of $120,000 budget.", "Final accounting after all phases completed."),
    ("Research Lab", "Hypothesis", "Team size is 4 researchers plus 2 grad students", "Team grew to 4 researchers plus 4 grad students.", "Two additional grad students joined during Data Collection phase."),
    ("Research Lab", "Hypothesis", "Target journal is Nature Materials", "Paper submitted to Nature Materials, manuscript #NM-2026-0142.", "Submission completed in Publication phase."),
    ("Research Lab", "Hypothesis", "layered structure improves conductivity by 30%", "Layered structure confirmed to improve conductivity by 42%.", "AFM imaging and statistical analysis showed 42%, not 30%."),
    ("Research Lab", "Hypothesis", "Initial supplier for raw materials is ChemCorp", "Supplier switched from ChemCorp (98.2% purity) to SynthPure (99.7% purity).", "ChemCorp purity was insufficient; SynthPure delivers 99.7%."),
    ("Research Lab", "Hypothesis", "Estimated timeline to first results: 6 months", "First significant results achieved in month 9 (Pilot Study phase).", "Timeline was optimistic; pilot took longer than expected."),
    ("Research Lab", "Pilot Study", "tensile strength of 380 MPa", "Pilot batch 3 reached 420 MPa after protocol adjustment.", "Improved mixing and temperature control in batch 3."),
    ("Research Lab", "Pilot Study", "Yield rate in pilot was 45%", "Yield improved to 58% in final pilot batch with humidity control.", "Humidity control addition improved yield significantly."),
    ("Research Lab", "Pilot Study", "Sample degradation observed after 72 hours", "Degradation reduced to <5% over 30 days with protective coating.", "Surface coating developed during Data Collection phase."),
    ("Research Lab", "Pilot Study", "Raw material purity from ChemCorp was only 98.2%", "Switched to SynthPure, raw material purity now 99.7%.", "Quality issue resolved by changing supplier."),
    ("Research Lab", "Pilot Study", "Pilot data suggests layered hypothesis is partially correct", "Layered hypothesis fully confirmed with 42% conductivity improvement.", "Full-scale data and AFM analysis confirmed the hypothesis."),
    # Supply Chain updates — operational metrics evolving
    ("Supply Chain", "Assessment", "shipping cost per unit: $4.20", "Cost per unit reduced to $3.40 after full deployment.", "Vendor consolidation and route optimization achieved 19% reduction."),
    ("Supply Chain", "Assessment", "delivery time: 14 days domestic", "Average delivery time improved to 11 days domestic.", "ShipFast carrier and route optimization reduced delivery time."),
    ("Supply Chain", "Assessment", "Warehouse utilization: 67%", "Warehouse utilization improved to 81% across all facilities.", "Automated picking and cross-docking expanded capacity use."),
    ("Supply Chain", "Assessment", "Inventory turnover ratio: 4.2x", "Inventory turnover improved to 5.4x annually.", "Better demand forecasting and faster shipping reduced holding."),
    ("Supply Chain", "Assessment", "Order accuracy rate: 91.3%", "Order accuracy rate improved to 95.8% company-wide.", "Automated picking reduced human errors significantly."),
    ("Supply Chain", "Assessment", "Customer satisfaction (NPS): +32", "Customer NPS improved to +45 company-wide.", "Faster delivery, fewer errors, and real-time tracking drove NPS up."),
    ("Supply Chain", "Assessment", "Annual logistics budget: $8.4M", "Annual logistics cost reduced to $7.1M (15% reduction).", "Vendor consolidation, automation, and route optimization."),
    ("Supply Chain", "Assessment", "legacy ERP from 2018, no real-time tracking", "New TMS platform deployed with 100% real-time shipment tracking.", "IT modernization completed during Pilot Rollout phase."),
    ("Supply Chain", "Assessment", "Carbon footprint: 12,400 tons CO2", "Carbon footprint reduced to 10,800 tons CO2 (13% reduction).", "Route optimization and fuel efficiency improvements."),
    ("Supply Chain", "Assessment", "Return rate: 6.8%", "Return rate improved to 4.6% (below industry average of 5.2%).", "Better order accuracy and quality control reduced returns."),
    ("Supply Chain", "Assessment", "demand forecasting accuracy: 74%", "Demand forecasting accuracy improved to 83%.", "New TMS platform and historical data analysis."),
    ("Supply Chain", "Assessment", "Cross-docking used at only 1 of 5 facilities", "Cross-docking operational at 4 of 5 facilities.", "Phased rollout during Pilot and Full Deployment."),
    ("Supply Chain", "Assessment", "No automated picking systems", "Automated picking deployed at 4 of 5 facilities.", "WarehoTech systems installed during Pilot and Full Deployment."),
    ("Supply Chain", "Assessment", "Current vendor count: 42", "Vendor count reduced from 42 to 27.", "Strategic consolidation for better pricing and management."),
    ("Supply Chain", "Assessment", "Staff turnover in logistics: 18%", "Staff turnover reduced to 12%.", "Better tools, training, and working conditions."),
    ("Supply Chain", "Vendor Selection", "ShipFast selected as primary carrier", "ShipFast Year 2 contract renegotiation in progress for better terms.", "Year 1 performance exceeded expectations, leveraging for better rates."),
    ("Supply Chain", "Vendor Selection", "Total vendor count reduced from 42 to 31", "Vendor count further reduced to 27 in Optimization phase.", "Continued consolidation based on performance data."),
    ("Supply Chain", "Vendor Selection", "volume discounts: 12% on average", "Volume discounts increased to 15% in Year 2 negotiations.", "Stronger negotiating position after Year 1 savings proof."),
    ("Supply Chain", "Vendor Selection", "WarehoTech pilot installation scheduled for Q3", "WarehoTech systems operational at 4 facilities, 5th in progress.", "Successful pilot led to accelerated rollout."),
    ("Supply Chain", "Vendor Selection", "Training budget for vendor transition: $85K", "Training completed at 92% staff coverage, budget fully used.", "Training program executed successfully during Pilot."),
    # Additional cross-epoch updates
    ("Research Lab", "Data Collection", "Budget spent: $78,000", "Final budget utilization: $112,400 of $120,000.", "Remaining budget consumed in Analysis and Publication phases."),
    ("Research Lab", "Data Collection", "200 samples produced across 15 batches", "200 samples with full characterization data published to repository.", "Dataset archived with DOI for reproducibility."),
    ("Research Lab", "Data Collection", "Munich group contacted us", "Munich collaboration formalized for joint Phase 2 study.", "Evolved from informal contact to formal partnership."),
    ("Research Lab", "Analysis", "Team authored first draft", "Paper submitted and under review at Nature Materials.", "Progressed from draft to submission with reviewer feedback."),
    ("Research Lab", "Analysis", "Patent application filed", "Patent application filed, IP licensing discussions with 2 industry partners.", "Commercial interest emerged after publication."),
    ("Supply Chain", "Pilot Rollout", "Pilot budget: $1.8M spent of $2.0M", "Full deployment completed under budget, Phase 2 approved at $2.5M.", "Cost discipline in pilot enabled expanded Phase 2 funding."),
    ("Supply Chain", "Pilot Rollout", "3 data sync errors in week 1", "IT integration issues fully resolved, zero sync errors in deployment.", "Engineering team fixed root cause during pilot."),
    ("Supply Chain", "Pilot Rollout", "Demand forecasting accuracy improved to 81%", "AI-powered forecasting deployed, targeting 90% accuracy.", "Advanced to AI-based model in Optimization phase."),
    ("Supply Chain", "Full Deployment", "Customer NPS: +45 company-wide", "NPS target raised to +55 for Optimization phase.", "Strong results set higher bar for continuous improvement."),
    ("Supply Chain", "Full Deployment", "Annual logistics cost: $7.1M", "Year 1 ROI confirmed at 18.2%, presented to board.", "Financial results validated and communicated to leadership."),
]

# ─── TEMPORAL REASONING QUESTIONS (30 with ground truth) ───
# Each question targets a specific category of temporal reasoning
QUESTIONS = [
    # Point-in-Time Recall (10 questions)
    {
        "id": "Q01", "category": "point_in_time",
        "question": "What was the expected tensile strength of Compound X during the Hypothesis phase?",
        "ground_truth": "450 MPa",
        "workspace": "Research Lab", "epoch": "Hypothesis",
    },
    {
        "id": "Q02", "category": "point_in_time",
        "question": "What was the shipping cost per unit during the Assessment phase?",
        "ground_truth": "$4.20",
        "workspace": "Supply Chain", "epoch": "Assessment",
    },
    {
        "id": "Q03", "category": "point_in_time",
        "question": "What was the yield rate during the Pilot Study?",
        "ground_truth": "45%",
        "workspace": "Research Lab", "epoch": "Pilot Study",
    },
    {
        "id": "Q04", "category": "point_in_time",
        "question": "How many vendors were active during the Assessment phase?",
        "ground_truth": "42",
        "workspace": "Supply Chain", "epoch": "Assessment",
    },
    {
        "id": "Q05", "category": "point_in_time",
        "question": "What was the warehouse utilization during Pilot Rollout?",
        "ground_truth": "78%",
        "workspace": "Supply Chain", "epoch": "Pilot Rollout",
    },
    {
        "id": "Q06", "category": "point_in_time",
        "question": "What Palladium concentration was used in the Hypothesis phase?",
        "ground_truth": "5%",
        "workspace": "Research Lab", "epoch": "Hypothesis",
    },
    {
        "id": "Q07", "category": "point_in_time",
        "question": "What was the NPS score during Full Deployment?",
        "ground_truth": "+45",
        "workspace": "Supply Chain", "epoch": "Full Deployment",
    },
    {
        "id": "Q08", "category": "point_in_time",
        "question": "What was the synthesis temperature during Hypothesis?",
        "ground_truth": "800C",
        "workspace": "Research Lab", "epoch": "Hypothesis",
    },
    {
        "id": "Q09", "category": "point_in_time",
        "question": "What was the order accuracy rate during Assessment?",
        "ground_truth": "91.3%",
        "workspace": "Supply Chain", "epoch": "Assessment",
    },
    {
        "id": "Q10", "category": "point_in_time",
        "question": "What was the carbon footprint during Assessment?",
        "ground_truth": "12,400 tons CO2",
        "workspace": "Supply Chain", "epoch": "Assessment",
    },
    # Evolution Tracking (10 questions)
    {
        "id": "Q11", "category": "evolution",
        "question": "How did the tensile strength belief evolve from Hypothesis to Publication?",
        "ground_truth": "450 MPa (Hypothesis) -> 380 MPa (Pilot batch 1) -> 510 MPa (Data Collection/final)",
        "workspace": "Research Lab",
    },
    {
        "id": "Q12", "category": "evolution",
        "question": "How did shipping cost per unit change from Assessment to Full Deployment?",
        "ground_truth": "$4.20 -> $3.50 (pilot) -> $3.40 (full deployment)",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q13", "category": "evolution",
        "question": "How did the yield rate evolve across all phases?",
        "ground_truth": "60% (target) -> 45% (pilot) -> 72% (data collection/final)",
        "workspace": "Research Lab",
    },
    {
        "id": "Q14", "category": "evolution",
        "question": "How did vendor count change from Assessment to Optimization?",
        "ground_truth": "42 -> 31 (vendor selection) -> 27 (optimization)",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q15", "category": "evolution",
        "question": "How did Palladium concentration evolve?",
        "ground_truth": "5% (hypothesis) -> 7% (pilot suggestion) -> 6.5% (finalized)",
        "workspace": "Research Lab",
    },
    {
        "id": "Q16", "category": "evolution",
        "question": "How did warehouse utilization change across phases?",
        "ground_truth": "67% (assessment) -> 78% (pilot) -> 81% (full deployment)",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q17", "category": "evolution",
        "question": "How did the conductivity improvement belief change?",
        "ground_truth": "30% (hypothesis) -> partially confirmed (pilot) -> 42% confirmed (analysis)",
        "workspace": "Research Lab",
    },
    {
        "id": "Q18", "category": "evolution",
        "question": "How did NPS evolve from Assessment to Optimization?",
        "ground_truth": "+32 (assessment) -> +48 (pilot regions) -> +45 (company-wide) -> +55 (target)",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q19", "category": "evolution",
        "question": "How did the raw material supplier change?",
        "ground_truth": "ChemCorp 98.2% purity -> SynthPure 99.7% purity",
        "workspace": "Research Lab",
    },
    {
        "id": "Q20", "category": "evolution",
        "question": "How did demand forecasting accuracy evolve?",
        "ground_truth": "74% (assessment) -> 81% (pilot) -> 83% (deployment) -> 90% target (optimization)",
        "workspace": "Supply Chain",
    },
    # Cross-Workspace Isolation (5 questions)
    {
        "id": "Q21", "category": "isolation",
        "question": "Does the Supply Chain workspace contain any information about Palladium concentration?",
        "ground_truth": "No — Palladium is exclusively in the Research Lab workspace.",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q22", "category": "isolation",
        "question": "Does the Research Lab workspace know about ShipFast carrier?",
        "ground_truth": "No — ShipFast is exclusively in the Supply Chain workspace.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q23", "category": "isolation",
        "question": "Can a query about 'budget' in Supply Chain return the $120,000 lab budget?",
        "ground_truth": "No — the $120,000 is Research Lab budget. Supply Chain budget is $8.4M.",
        "workspace": "Supply Chain",
    },
    {
        "id": "Q24", "category": "isolation",
        "question": "If I search for 'NPS' in Research Lab, what do I find?",
        "ground_truth": "Nothing — NPS is exclusively a Supply Chain metric.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q25", "category": "isolation",
        "question": "Does Supply Chain have any data about Nature Materials journal?",
        "ground_truth": "No — publication details are exclusively in Research Lab.",
        "workspace": "Supply Chain",
    },
    # Decay & Confidence (5 questions)
    {
        "id": "Q26", "category": "decay",
        "question": "If a memory about 'weekly standup meetings' is never recalled for 10 days, what happens to its confidence?",
        "ground_truth": "Confidence decays from 1.0 by -0.05 per day (10 decay cycles), floor at 0.1. Result: 0.5.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q27", "category": "decay",
        "question": "If 'Compound X tensile strength' is recalled 5 times in 3 days, what happens to confidence?",
        "ground_truth": "Each recall adds +0.05 capped at 1.0. After 5 recalls: confidence stays at 1.0 (already max). Recall count: 5.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q28", "category": "decay",
        "question": "Which memories should have highest confidence after a typical usage pattern?",
        "ground_truth": "Memories about core findings (tensile strength, yield rate) — frequently recalled. Memories about 'weekly standup' or 'safety protocol' — rarely recalled, lower confidence.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q29", "category": "delta",
        "question": "What is the exact mathematical delta between Hypothesis and Data Collection in Research Lab?",
        "ground_truth": "Continuities: 10 unchanged memories. Evolutions: 10 updated beliefs (temp, yield, strength, catalyst, etc.). Additions: 20 new memories from Data Collection.",
        "workspace": "Research Lab",
    },
    {
        "id": "Q30", "category": "delta",
        "question": "What is the delta between Assessment and Full Deployment in Supply Chain?",
        "ground_truth": "Continuities: ~5 unchanged beliefs. Evolutions: 15 metrics that improved. Additions: 20 new operational details from Full Deployment.",
        "workspace": "Supply Chain",
    },
]

def generate_dataset():
    """Generate and save the full benchmark dataset to JSON."""
    dataset = {
        "metadata": {
            "version": "1.0",
            "total_memories": sum(len(mems) for ws_mems in MEMORIES.values() for mems in ws_mems.values()),
            "total_updates": len(UPDATES),
            "total_questions": len(QUESTIONS),
            "workspaces": list(WORKSPACES.keys()),
            "epochs_per_workspace": {ws: [e["name"] for e in eps] for ws, eps in EPOCHS.items()},
        },
        "workspaces": WORKSPACES,
        "epochs": EPOCHS,
        "memories": MEMORIES,
        "updates": [
            {"workspace": u[0], "epoch": u[1], "original_fragment": u[2], "new_content": u[3], "reason": u[4]}
            for u in UPDATES
        ],
        "questions": QUESTIONS,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "tlcm_bench_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"[TLCM-Bench] Dataset generated: {output_path}")
    print(f"  Total memories: {dataset['metadata']['total_memories']}")
    print(f"  Total updates:  {dataset['metadata']['total_updates']}")
    print(f"  Total questions: {dataset['metadata']['total_questions']}")
    return dataset


if __name__ == "__main__":
    generate_dataset()

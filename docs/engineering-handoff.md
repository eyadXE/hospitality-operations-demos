Elaf Group — Exology Pioneer Program
Engineering Handoff Document
How We Solved 3 Pain Points: Invoice Extraction, Pilgrim Onboarding, Seasonal Demand Response
This document is the detailed technical handoff for the three pain points assigned to us. Each section covers the full workflow, the architecture, every rule/check the system runs, the diagrams for how it fits together, and what was actually built and tested (not just designed). Written for engineering onboarding — enough detail to pick up the code and continue.
Contents
Part 1 — Invoice & Expense Extraction (Pain Point: manual invoice processing across 9 properties)
Part 2 — Pilgrim Onboarding Agent (Pain Point: paperwork-heavy pilgrim onboarding)
Part 3 — Seasonal Demand Response Plan (Pain Point: seasonal demand swings)
Part 4 — Cross-Cutting Engineering Notes (shared design decisions across all three)

Part 1 — Invoice & Expense Extraction
Pain point: invoices and expenses are processed by hand, and the same work is repeated separately at each of the 9 properties.
1.1 What We Built
A working Streamlit demo that takes a vendor invoice image, runs local OCR, extracts the invoice's entities (header fields, line items, totals), and runs plain-code sanity checks to decide auto-approve vs. human review. Tested end-to-end against 4 synthetic invoices, including two deliberately broken cases (arithmetic mismatch, missing PO number) to prove the check logic actually catches problems, not just the happy path.
1.2 Architecture

Figure 1.1 — Invoice extraction pipeline, from upload to the central invoice DB.
Each stage:
OCR (Tesseract): free, open-source, runs locally — no invoice data sent to any third-party API. Images are upscaled 2x before OCR, which measurably improves accuracy on small text.
Header Field Extraction: regex-based label matching pulls invoice number, vendor, property, PO number, invoice date, due date.
Line-Item Table Extraction: a regex pattern matches each row of the item table (description + qty + unit price + line total), automatically skipping header/total rows since they don't match the 4-column numeric pattern.
Totals Extraction: pulls the printed subtotal, tax, and total due.
Sanity Checks: plain code, not AI — see 1.3 below.
Central Invoice DB: validated invoices land in a schema keyed by property → department → cost center — this is also the seed of the centralized data layer needed for cross-property reporting.
1.3 The 3 Sanity Checks
These are what decide auto-approve vs. human review. All are deterministic arithmetic/presence checks — no model makes this call.
#
 | Check
 | Logic
 | Why It Matters
 | 
1
 | Line items sum to printed subtotal
 | sum(line_total for each item) == printed subtotal (within 1 cent)
 | Catches OCR misreads or a genuinely altered/incorrect invoice where the line items don't add up to what's claimed.
 | 
2
 | Subtotal + tax = printed total
 | subtotal + tax == printed total (within 1 cent)
 | Catches arithmetic errors on the invoice itself — demoed live against a sample with a deliberately wrong total.
 | 
3
 | PO number present
 | po_number field is non-empty and not 'N/A'/'None'
 | Without a PO, a real 3-way match (invoice vs. PO vs. goods-received note) can't run at all — this flags that gap explicitly rather than silently skipping it.
 | 

Figure 1.2 — Decision flow: any single check failure routes to human review with the specific reason, not a generic "needs review" flag.
1.4 Test Results Against the 4 Sample Invoices
Sample Invoice
 | Check 1 (sum)
 | Check 2 (arithmetic)
 | Check 3 (PO)
 | Outcome
 | 
Valid — hotel supplies
 | ✅ pass
 | ✅ pass
 | ✅ pass
 | Auto-approved
 | 
Valid — F&B vendor
 | ✅ pass
 | ✅ pass
 | ✅ pass
 | Auto-approved
 | 
Total mismatch (deliberate)
 | ✅ pass
 | ❌ fail
 | ✅ pass
 | Routed to human review
 | 
Missing PO number (deliberate)
 | ✅ pass
 | ✅ pass
 | ❌ fail
 | Routed to human review
 | 
All extracted values (header fields, every line item, every total) matched the source invoice exactly on all 4 samples — verified by direct comparison, not eyeballing.
1.5 Known Limitation — Be Upfront About This
Extraction is regex-based against a fixed-column line-item table. Real vendor invoices vary wildly in layout (scanned vs. PDF-native, no consistent table structure) — a production version needs a layout-aware document-AI extraction model, not simple regex. There is no invoice equivalent of the passport MRZ (a universal machine-readable fallback), so this gap can't be closed as cleanly as it was for the onboarding agent — worth stating plainly rather than glossing over.

Part 2 — Pilgrim Onboarding Agent
Pain point: pilgrim onboarding carries a lot of paperwork — passports, visas, health certificates, package documents — and people check all of it by hand.
2.1 What We Built
A working Streamlit demo with 4 independent document-check tabs (Passport, Visa, Health Certificate, Booking Confirmation) plus a Cross-Document Summary tab. Each document is OCR'd, its fields extracted, and checked against 5 deterministic rules. Tested against 8 synthetic documents, including 4 deliberately broken cases (one per violated rule) and validated against a real-world-style passport image to prove the extraction generalizes beyond our own synthetic layout.
2.2 Why Rule-Based, Not AI, for the Decision
The validation decision itself is deliberately not an AI/LLM call. Two reasons: (1) pilgrims' personal documents are sensitive — AI/OCR only reads them, a rules engine we control decides pass/fail, so nothing sensitive is sent to a third-party model for a judgment call; (2) a rules engine is deterministic and explainable — when a pilgrim is told their visa doesn't cover their travel dates, that has to be exactly right, not a probabilistic guess.
2.3 System Architecture

Figure 2.1 — End-to-end flow from document upload to hotel check-in.
2.4 What We Extract From Each Document
Document
 | Key Fields Extracted
 | 
Passport
 | Full name, date of birth, nationality, passport number, issue date, expiry date
 | 
Visa
 | Visa number, visa type (Hajj/Umrah/other), holder name, validity start/end date
 | 
Health Certificate
 | Holder name, vaccination type(s), issue date, certificate validity period
 | 
Booking Confirmation
 | Traveler name, package type, trip start/end date
 | 
2.5 The 5 Validation Rules
#
 | Rule
 | Condition Checked
 | Example Violation Message
 | 
1
 | Passport Validity
 | Expiry date is after trip return date + 6-month buffer (configurable, matches common Saudi entry requirement).
 | "Your passport expires within 6 months of your travel date."
 | 
2
 | Visa Validity & Type Match
 | Visa not expired; validity window covers full trip; visa type matches booked package type.
 | "Your visa type does not match your booked Hajj package."
 | 
3
 | Health Certificate Validity
 | Required vaccination present; issued within validity window; issued ≥10 days before travel.
 | "Your health certificate was issued too close to your travel date."
 | 
4
 | Cross-Document Identity Consistency
 | Full name, DOB, nationality, passport number match exactly across all uploaded documents.
 | "The name on your health certificate does not match your passport."
 | 
5
 | Completeness & Extraction Confidence
 | All required documents present; every required field extracted; OCR confidence above threshold.
 | "We couldn't read your visa clearly. Please upload a clearer photo."
 | 

Figure 2.2 — Every rule must pass for auto-approval; failures and low-confidence cases route to distinct outcomes.
2.6 Test Results Against the 8 Sample Documents
Sample
 | Rule Tested
 | Expected
 | Actual Result
 | 
passport_valid.png
 | Rule 1
 | pass
 | ✅ pass — "valid well beyond trip dates"
 | 
passport_expiring_soon.png
 | Rule 1
 | fail
 | ✅ fail — correctly flagged, <6mo buffer
 | 
visa_valid_hajj.png
 | Rule 2
 | pass
 | ✅ pass
 | 
visa_wrong_type.png
 | Rule 2
 | fail
 | ✅ fail — "TOURIST vs booked HAJJ"
 | 
health_valid.png
 | Rule 3
 | pass
 | ✅ pass
 | 
health_issued_too_late.png
 | Rule 3
 | fail
 | ✅ fail — issued 2 days before travel
 | 
health_name_mismatch.png
 | Rule 4
 | fail
 | ✅ fail — "HASSAN" vs "HASAN" caught
 | 
Real-world passport (test upload)
 | MRZ fallback
 | extract correctly
 | ✅ name/DOB/nationality/expiry all matched the printed document exactly
 | 
2.7 Real-World Robustness — the MRZ Fallback
Real passports don't use our demo's "Full Name:" style labels — a real bilingual passport we tested against used "Nom/Surname", "Date de naissance/Date of birth", etc., which the label-matching regex correctly failed to find. Rather than treat this as a dead end, we added a second extraction strategy: parsing the Machine Readable Zone (MRZ) — the two standardized lines at the bottom of every passport worldwide (ICAO Doc 9303, TD3 format). This is used as a fallback whenever label-matching misses a field, and is the right approach for a real system, not just a demo patch — MRZ format is universal regardless of country, language, or template design.
What MRZ parsing recovers: name, date of birth, nationality, expiry date, and (via a secondary plain-text fallback) the passport number.
OCR noise handled: two real issues surfaced and were fixed: misread '<' padding characters showing up as garbage letters in the name (filtered via a repeated-character heuristic), and 'O' misread as '0' inside the 3-letter country code (normalized back).
2.8 Customer Journey — What Changes at the Hotel

Figure 2.3 — Validation happens before arrival; check-in becomes a confirmation, not a document review.
The receptionist currently checks all of this manually at the front desk, exactly when the hotel is busiest. This system moves that checking earlier — before the pilgrim leaves home — so by the time they reach the hotel, the receptionist confirms a known-good status instead of checking for the first time.

Part 3 — Seasonal Demand Response Plan
Pain point: demand swings sharply with the Hajj/Umrah season, which makes staffing, procurement, and finance planning hard to get right.
3.1 What This Is (and Isn't)
This is a structured operational playbook, not a forecasting model — deliberately. It's grounded in how Saudi hospitality operators actually handle Hajj/Umrah demand today (the Ajeer government staffing platform, standard hotel procurement practice), not a predictive system we'd need historical booking data to validate.
3.2 Why This Isn't a Normal Seasonal Pattern
It's lunar, not fixed: The Hijri calendar is ~11 days shorter than the Gregorian year, so Hajj shifts ~11 days earlier every Western-calendar year (Hajj 2026: late May; Hajj 2027: ~May 14-19). A plan tied to fixed Gregorian months goes stale year over year — everything below keys off the Hijri date.
It's several overlapping peaks, not one: Hajj and Ramadan are the two dominant compression periods, with increasingly strong demand extending into surrounding quarters too. This needs a tiered response, not a single on/off switch.
3.3 Demand Tiers

Figure 3.1 — Three fixed tiers, keyed to calendar proximity to Hajj/Ramadan (recalculated each Hijri year).
Tier
 | When
 | Response Level
 | 
Tier 1 — Peak
 | Hajj window (8-13 Dhul Hijjah) and final third of Ramadan
 | Full seasonal staffing via Ajeer; maximum safety stock; centralized procurement; sustained-endurance shift rotations.
 | 
Tier 2 — Elevated
 | Rest of Ramadan; 4-6 weeks either side of the Hajj window
 | Partial seasonal staffing top-up; moderate safety stock increase; vendor peak-readiness confirmed.
 | 
Tier 3 — Baseline
 | Remaining weeks of the year, incl. year-round Umrah flow
 | Core staffing only; standard reorder points; normal procurement per property's usual model.
 | 
3.4 Staffing & Procurement Phase Timeline

Figure 3.2 — Both tracks run on the same Hijri-relative clock, staggered so procurement commitments (contracts, dual-sourcing) lock in before staffing sourcing begins.
3.5 Staffing Response Plan
Phase
 | Timing
 | What Happens
 | 
1. Baseline lock-in
 | 9-12 months ahead
 | Confirm core staffing per property; flag perennially short roles (housekeeping, F&B, front desk).
 | 
2. Temp workforce sourcing
 | 3-6 months ahead
 | Register seasonal headcount via Ajeer; confirm health clearances (meningitis, seasonal flu) and occupational insurance per Saudi MOH requirements before deployment.
 | 
3. Workforce modelling
 | 1-3 months ahead
 | Recalibrate shift rotations per property's demand tier — Makkah/Madinah properties running near-full occupancy for extended stretches need endurance-designed rotations, not spike coverage.
 | 
4. Pre-peak readiness check
 | 2-4 weeks ahead
 | Confirm all temp staff onboarded/trained/cleared; identify roles with no backup coverage.
 | 
5. Peak operation
 | During peak window
 | Daily execution; leadership focus shifts from reactive to anticipatory monitoring.
 | 
6. Wind-down & review
 | 1-2 weeks after
 | Release temp staff per Ajeer terms; capture lessons for next (Hijri-shifted) cycle.
 | 
3.6 Procurement Response Plan
Phase
 | Timing
 | What Happens
 | 
1. Seasonal contract negotiation
 | 6-9 months ahead
 | Lock in seasonal volume terms per critical category — delivery-schedule guarantees during high season, not just price.
 | 
2. Dual-sourcing check
 | 6-9 months ahead
 | Confirm a second qualified supplier exists for every critical SKU, not just a preferred one.
 | 
3. Safety stock build-up
 | 1-2 months ahead
 | Increase reorder points on non-perishables (linens, amenities). Perishable F&B stays on tight replenishment — not stockpiled, to avoid spoilage.
 | 
4. Centralized ordering
 | During peak window
 | Route peak reordering through centralized purchasing across the 9 properties for consistent pricing/delivery priority.
 | 
5. Contingency comms
 | Ongoing during peak
 | Named contact chain per critical vendor for disruptions.
 | 
6. Post-peak reconciliation
 | 1-2 weeks after
 | True-up ordered vs. used volume; feeds next cycle's negotiation leverage.
 | 
3.7 Ownership
Staffing plan: Hotel Operations owns Phases 1, 3-6; HR/People function owns Phase 2 (Ajeer, compliance).
Procurement plan: Finance & Procurement owns all phases; property-level Ops owns local reorder triggers day-to-day.
Demand tiers: Joint Ops + Procurement decision, reviewed once per Hijri year as the calendar shifts.
3.8 What This Deliberately Excludes
No occupancy/demand forecasting model — fixed playbook keyed to the Hijri calendar and demand tiers.
No specific headcount/order-volume numbers — depend on each property's real historical patterns and current-year Hajj/Umrah quota allocations, which Elaf holds and we don't have access to.
No automated triggering — every phase is human-initiated on a calendar-driven schedule.

Part 4 — Cross-Cutting Engineering Notes
4.1 Shared Design Principle Across All Three
In every case where a decision has real consequences for a person or a payment, the AI/OCR component only reads or extracts data — it never makes the pass/fail or approve/reject call. That's always plain, auditable code (rules engine, sanity checks, phase-based playbook). This is intentional and consistent, and worth keeping as a standard across future opportunities too, not just these three.
4.2 Shared Tech Stack (Parts 1 & 2)
OCR: Tesseract — free, open-source, runs entirely locally. No pilgrim or invoice data is ever sent to a third-party API. Both demos upscale images 2x before OCR, which measurably improved accuracy in testing.
UI: Streamlit — both demos are self-contained Python apps (`streamlit run app.py`), no separate frontend/backend split needed for demo purposes.
Extraction strategy: label-based regex as the primary strategy, since both demos' synthetic documents use a consistent layout. Passport extraction additionally falls back to MRZ parsing for real-world robustness — see Part 2.7.
4.3 What's Genuinely Tested vs. What's Designed But Not Built
Pain Point
 | Tested & Working
 | Designed, Not Yet Built
 | 
Invoice Extraction
 | OCR + entity extraction + 3 sanity checks, verified against 4 synthetic invoices incl. 2 broken cases
 | Real 3-way match against actual PO/goods-received data (needs Elaf's procurement system access); layout-aware extraction for non-templated real invoices
 | 
Pilgrim Onboarding
 | OCR + MRZ extraction + 5 rules, verified against 8 synthetic docs + 1 real-world passport image
 | Document classifier as a separate step (currently doc type is manually selected per tab); human review queue is a UI placeholder, not a real ticketing integration
 | 
Seasonal Demand Plan
 | N/A — this is a process document, not code
 | Everything — this phase is entirely a proposed operational playbook pending Elaf's confirmation of actual quota/booking data access
 | 
4.4 Open Questions for the Team
Which OCR/document-AI stack do we standardize on if we move past Tesseract for production accuracy (cloud API vs. a larger self-hosted model)?
For invoices: is there a way to get sample real (anonymized) invoice layouts from Elaf's actual vendors, to stress-test extraction against real-world layout diversity before the meeting?
For onboarding: do we build the document classifier now, or keep manual doc-type selection for the demo and flag it as a fast-follow?
For the seasonal plan: can we get confirmation on whether Joudyan properties (Riyadh/Jeddah) really follow a different seasonality than the Hajj/Ramadan-driven Elaf Hotels portfolio, or if that's an assumption we need Elaf to validate?

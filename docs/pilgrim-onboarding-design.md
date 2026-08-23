Elaf Group — Exology Pioneer Program
Pilgrim Onboarding Agent
OCR → Rule-Based Validation → Human Review — System Design
Goal: the pilgrim uploads their documents before arrival. The system extracts and checks everything a receptionist would normally check by hand. If everything is valid, the only thing left at the hotel is a quick confirmation with the receptionist at check-in — not a paperwork review. If something is wrong, the pilgrim is told exactly what and why, before they ever travel.
1. Why Rule-Based, Not AI Judgment
The validation step itself is deliberately not an AI/LLM decision. Two reasons:
Pilgrims' personal documents (passport numbers, visa data, health data) are sensitive — we don't want to send that data to a third-party AI API just to decide pass/fail. AI extraction is used to read the documents; a rules engine we control decides whether they're valid.
A rules engine is deterministic and explainable. When a pilgrim is told "your visa doesn't cover your travel dates," that has to be exactly right and defensible — not a probabilistic guess.
So the AI component is scoped narrowly: read the document and extract structured fields. Everything after that — the actual validation — is plain code, checkable and auditable.
2. System Architecture

Figure 1 — End-to-end flow from document upload to hotel check-in.
Each box in Figure 1 is a distinct component:
Document Upload Portal: where the pilgrim (or their travel agent) uploads passport, visa, health certificate, and booking confirmation, ideally days before travel.
Document Classifier: identifies which uploaded file is which document type, so the correct extraction template and rules apply to each.
OCR / Document AI: extracts the structured fields we need from each document (see field list in Section 3).
Rules Engine: runs the 5 validation rules (Section 4) against the extracted fields — this is the core of the system, and it is plain rule logic, not an AI model.
Pilgrim Record Store: holds the validated, structured pilgrim record, status-tagged as Ready / Needs Fix / Under Review.
Notification Service: tells the pilgrim immediately if something failed, with the specific reason and what to do.
Human Review Queue: catches the cases the rules engine can't confidently resolve on its own — low OCR confidence or genuinely ambiguous cases — for a staff member to check manually.
Hotel Receptionist view: at check-in, the receptionist sees a pre-verified status instead of re-checking every document from scratch.
3. What We Extract From Each Document
Document
 | Key Fields Extracted
 | 
Passport
 | Full name, date of birth, nationality, passport number, issue date, expiry date
 | 
Visa
 | Visa number, visa type (Hajj / Umrah / other), holder name, validity start date, validity end date
 | 
Health Certificate
 | Holder name, vaccination type(s), vaccination/issue date, certificate validity period
 | 
Booking / Package Confirmation
 | Traveler name, package type, trip start date, trip end date
 | 
4. The 5 Validation Rules
This is the core logic. Each uploaded document set is run through all 5 rules. Any single violation is enough to flag the pilgrim and explain exactly why — we don't just say "review needed," we say what's wrong.
#
 | Rule
 | Condition Checked
 | Example Violation Message
 | 
1
 | Passport Validity
 | Passport expiry date is after the trip return date, with a required buffer (default: 6 months beyond arrival — matches common Saudi entry requirement; configurable).
 | "Your passport expires within 6 months of your travel date. Please renew before uploading again."
 | 
2
 | Visa Validity & Type Match
 | Visa is not expired; visa validity window fully covers the trip dates (visa start ≤ trip start, visa end ≥ trip end); visa type matches the booked package type (Hajj / Umrah / other).
 | "Your visa type does not match your booked Hajj package. Please confirm your visa type."
 | 
3
 | Health Certificate Validity
 | Required vaccination(s) present (e.g. meningitis for Hajj/Umrah); certificate issued within its validity window; issued at least 10 days before travel date so it has taken effect.
 | "Your health certificate was issued too close to your travel date. It must be at least 10 days old."
 | 
4
 | Cross-Document Identity Consistency
 | Full name, date of birth, nationality, and passport number match exactly across passport, visa, health certificate, and booking confirmation.
 | "The name on your health certificate does not match your passport. Please check and re-upload."
 | 
5
 | Completeness & Extraction Confidence
 | All required documents are present; every required field was successfully extracted; OCR confidence score is above threshold on every extracted field.
 | "We couldn't read your visa clearly. Please upload a clearer photo or scan."
 | 
5. Rules Engine Decision Flow

Figure 2 — Every rule must pass for auto-approval; any failure routes to a specific outcome.
Note the three distinct outcomes: a clean pass (auto-approved, no human touches it), a clear violation (pilgrim is notified directly, with the specific rule and reason — this is deterministic, not a maybe), and a low-confidence/edge case (routed to a human, not auto-rejected, because the system genuinely isn't sure and shouldn't guess on someone's travel eligibility).
6. Customer Journey — Before vs. After

Figure 3 — Validation happens before arrival; check-in becomes a confirmation, not a document review.
The entire point of the system: today, the receptionist checks all of this manually at the front desk, at exactly the moment when the hotel is busiest (Hajj/Umrah season, guests arriving in bulk). This system moves that checking earlier — before the pilgrim ever leaves home — so that by the time they reach the hotel, the receptionist is confirming a status that's already known to be correct, not doing the checking for the first time.
7. Failure & Edge Case Handling
Rule violation (clear-cut): Pilgrim is notified directly through their upload channel with the specific rule violated and what to do (e.g. re-upload a clearer scan, renew a passport, contact travel agent about visa type). No human involved — the rule is unambiguous.
Low OCR confidence: If any required field couldn't be extracted with high confidence (blurry scan, unusual document format, damaged document), it goes to Human Review rather than being auto-rejected or auto-approved on a guess.
Genuinely ambiguous case: e.g. a legitimate name spelling variation across documents (common with transliteration from Arabic) — flagged for a human rather than auto-failing on Rule 4, since this is a known false-positive risk worth designing for explicitly.
Re-upload loop: If a pilgrim fixes and re-uploads, the corrected document re-enters the same pipeline from Document Classification — no special-casing needed.
8. Data & Ownership
Data needed: the four document types above, plus the buffer/threshold values (passport validity buffer, health cert issue window, OCR confidence threshold) — these should be configurable, not hardcoded, since Elaf may want to tune them.
Who owns it: Hajj & Umrah Services owns the day-to-day process and the human review queue; someone senior needs to own the specific threshold values (e.g. how many days before travel a health cert becomes invalid) since that's a policy decision, not a technical one.
Privacy note: raw document images/PII should not be sent to any third-party AI service beyond what's needed for OCR extraction, and ideally an OCR provider with a clear data-retention policy (or a self-hosted OCR model) is used given the sensitivity of passport/visa/health data.
9. Open Questions for the Engineering Kickoff
Which OCR/document-AI stack are we standardizing on for the demo — cloud API or local/self-hosted model?
What buffer values do we default to for Rule 1 (passport) and Rule 3 (health cert) in the demo, given we don't have Elaf's actual policy thresholds yet?
How do we simulate the human review queue in the demo — a simple flagged-item list is probably enough to make the point.
Do we build the document classifier as a separate step, or fold classification into the extraction prompt itself for the demo (faster to build, less clean architecturally)?

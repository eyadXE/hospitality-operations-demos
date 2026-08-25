Exology Pioneer Program — AI & Automation Challenge
Hospitality Group
Solution Workflows & Demo Plan (Working Doc for Engineering Kickoff)
This document turns the six identified opportunities into concrete workflows, and — since we don't have access to operator's real invoice, guest-message, or booking data — sets out how each one gets demoed on synthetic/simulated data and public or free-tier APIs. Purpose: align with the engineer on scope and demo approach before we start building.
How the Six Problems Map to Solutions
1
 | Manual invoice processing across 9 properties → OCR + extraction pipeline
 | 
2
 | High-volume multi-channel guest questions → RAG chatbot across email/WhatsApp/web
 | 
3
 | Pilgrim onboarding paperwork → OCR → Validation → Human-review agent pipeline
 | 
4
 | Slow itinerary/package building → Recommendation (IR) system over package inventory
 | 
5
 | Seasonal demand swings → Forecasting model + staffing/procurement plan
 | 
6
 | Inconsistent systems across properties → Centralized data layer (shared foundation)
 | 
1. Invoice & Expense OCR Workflow
Workflow
Invoice arrives (PDF/scan/photo) → uploaded to intake endpoint, tagged with property ID.
OCR + layout model extracts raw text and table structure (vendor, line items, tax, totals, PO number, currency, dates).
LLM extraction pass maps raw OCR output into a structured schema (JSON) — normalizes vendor names, currency, VAT.
3-way match: extracted invoice vs. purchase order vs. goods-received note, where available.
Confidence scoring — high-confidence, matched invoices auto-post; low-confidence or mismatched ones route to a human reviewer queue.
Approved data lands in a central DB, keyed by property → department → cost center (this is also the seed of the centralized data layer in Problem 6).
Demo Plan (no real invoice data available)
Synthetic data: Generate ~15-20 realistic fake invoices (hotel supply vendors, F&B vendors, maintenance contractors) as PDFs — vary formats/templates across the 3 property brands to show the system isn't hardcoded to one layout. Can generate these with an LLM (structured content) rendered into PDF via a simple template, plus 2-3 deliberately messy/scanned-looking ones to show OCR robustness.
APIs/tools: Any OCR API (e.g. Tesseract for a free/local baseline, or a cloud OCR API if budget allows) + an LLM API call for the structured-extraction step. No paid data source needed — this is entirely simulated.
What the demo shows: Upload a batch of fake invoices → live extraction into structured fields → a couple flagged for human review (deliberately ambiguous ones) → clean data landing in a simple dashboard/table view, grouped by property.
What to be upfront about: Real vendor-name normalization and true 3-way matching need operator's actual PO/vendor master data — flag this as a known gap the demo can't fully cover.
2. Multi-Channel Guest Support Chatbot (RAG)
Workflow
Guest message arrives via any channel (WhatsApp, email, web chat) → normalized into a common message format.
Query goes to a RAG pipeline: embed the question, retrieve relevant chunks from a knowledge base (hotel policies, FAQs, booking info, Hajj/Umrah service info).
LLM generates an answer grounded in retrieved content, in the guest's language.
Confidence/intent check — if the model isn't confident, or the query touches billing/complaints/anything sensitive, escalate to a human agent with the conversation context attached.
Response sent back through the original channel; conversation logged for QA and for expanding the knowledge base over time.
Demo Plan (no real guest data available)
Synthetic data: Build a small fake knowledge base (10-15 documents): hotel policies, check-in/check-out rules, a sample of Hajj/Umrah package FAQs, cancellation policy — written to sound like real hotel-group content, not copied from operator's site verbatim.
Simulated channels: Since we can't hook into operator's real WhatsApp Business account, simulate multi-channel with a simple chat UI that lets you pick 'channel: WhatsApp / Email / Web' — same backend, different presentation, to make the point that the RAG core is channel-agnostic.
APIs/tools: Any embedding + vector store (open-source, e.g. a local vector DB) + an LLM API for generation. WhatsApp Business API integration itself can be mocked/described rather than built for the demo.
What the demo shows: A guest asks a routine question (answered correctly from the knowledge base), then asks something out of scope or sensitive (correctly escalates instead of guessing).
What to be upfront about: Real knowledge base content and multilingual coverage (Arabic/English at minimum) depend on the operator providing source material — flag as a data dependency.
3. Pilgrim Onboarding Agent (OCR → Validation → Human Review)
Workflow
Pilgrim/agent uploads documents: passport, visa, health certificate, package confirmation.
Document classification step identifies which document is which (so the pipeline knows what rules apply).
OCR/Document AI extracts key fields per document type (passport number, expiry date, visa type/validity, vaccination/health cert dates, names matching across documents).
Validation rules run automatically: passport expiry vs. travel dates, visa type matches package type, health cert within validity window, name consistency across all documents.
Anything that fails a rule, or has low OCR confidence, routes to a human reviewer with the specific issue flagged (not just 'review this').
Approved pilgrim record is marked complete and released downstream to transport/package coordination.
Demo Plan (no real pilgrim documents available)
Synthetic data: Generate a set of fake passport/visa/health-cert mockups (clearly labeled as sample/fake documents) with a deliberate mix: some fully valid, some with an expired passport, some with mismatched names, some with poor scan quality — to show the validation logic actually catching real classes of problems, not just a happy path.
APIs/tools: Same OCR + LLM extraction stack as Problem 1, plus a small rules engine (can be plain code — this doesn't need to be an LLM decision, which also makes it easier to defend to non-technical reviewers).
What the demo shows: Run 4-5 sample pilgrim document sets through the pipeline live — most auto-approve, one or two get flagged with a specific, explainable reason (e.g. 'passport expires before return date').
What to be upfront about: This is the strongest demo of the six since the logic is mostly deterministic and explainable — worth positioning as the flagship/lead demo in the meeting.
4. Itinerary & Package Recommendation System
Workflow
Client (or travel agent on their behalf) provides constraints: dates, budget, group size, destination mix, religious/leisure balance.
System searches a package/inventory catalog (hotels, transport, tour add-ons) and retrieves candidates matching hard constraints (dates, budget ceiling).
Ranking step scores candidates against soft preferences (property brand, star rating, past client patterns if available) — this is closer to semantic search/matching over structured inventory than classic collaborative filtering, given limited per-client transaction history.
Top 2-3 ranked options returned with a short natural-language rationale for each; travel agent reviews and finalizes with the client — the agent stays in the loop, this doesn't auto-book.
Demo Plan (no real package/inventory data available)
Synthetic data: Build a fake catalog of ~30-40 packages spanning the three brand tiers (Makkah-Madinah property portfolio, Joudyan, premium loyalty perks) with varied price points, durations, and inclusions — enough variety to make ranking visibly non-trivial.
APIs/tools: A simple structured filter/search over the fake catalog + an LLM call to rank and generate the rationale text. No external API needed.
What the demo shows: Enter a client brief in plain language ('family of 5, Umrah package, 10 days, mid-range budget') and get 3 ranked options with reasoning, versus manually scrolling a package list.
What to be upfront about: This is the one where the underlying method is least settled — call it out as a prototype of the interaction, not a finished ranking algorithm, since real ranking needs real booking history to validate against.
5. Seasonal Demand Forecasting & Staffing/Procurement Plan
Workflow
Pick one target to forecast first rather than 'demand' broadly — recommend starting with occupancy/room-nights per property, since staffing and procurement both derive from it.
Model inputs: historical occupancy, booking lead times, and the Hajj/Umrah calendar — which is Hijri (lunar), so seasonality shifts ~11 days earlier each Gregorian year and can't use a fixed calendar-based seasonality assumption.
Forecast produces expected occupancy by property/week, translated into a staffing plan (housekeeping/F&B headcount) and a procurement plan (supply order volumes) with lead time built in.
Output is a planning dashboard, not an autonomous action — Ops and Procurement teams review and adjust before committing.
Demo Plan (no real booking history available)
Synthetic data: Generate a fake multi-year occupancy time series with realistic Hajj/Umrah seasonal spikes (using real Hijri calendar dates to place the spikes correctly — this detail alone demonstrates domain understanding) plus normal-season noise.
APIs/tools: A standard forecasting approach (e.g. a simple time-series model) run against the synthetic series; no external API needed beyond a Hijri-to-Gregorian date conversion, which is a solved, freely available calculation.
What the demo shows: Forecasted occupancy curve correctly spiking around simulated Hajj dates, with a derived staffing/procurement estimate underneath it.
What to be upfront about: This is the hardest one to make credible without operator's real historical data — the demo proves the modeling approach and the Hijri-awareness, not real predictive accuracy. Say this plainly in the meeting.
6. Centralized Data Layer
Workflow
This isn't a standalone AI feature — it's the shared foundation the other five lean on (invoice DB, chatbot's guest/booking context, pilgrim records, package inventory, occupancy history all need one consistent source of truth across properties).
Define a common schema per entity (invoice, guest, pilgrim, package, booking) that all 9 properties map into, regardless of what system each property runs today.
Each property-specific system feeds into this layer via connectors/ETL rather than being replaced outright — lower-risk, incremental adoption path.
Reporting and reconciliation queries run against the centralized layer instead of manually stitching together 9 separate exports.
Demo Plan
Approach: Rather than a standalone demo, show this as the connective tissue underneath the Problem 1 (invoice) and Problem 5 (occupancy) demos — e.g. invoices from 'different fake properties' with slightly different original formats all landing in one consistent schema, and occupancy data addressable by property in a single query.
What to be upfront about: This is a data engineering / governance recommendation more than an AI one — worth naming clearly as a prerequisite for several other recommendations to work at full value, not a sixth AI feature.
Cross-Cutting Notes for the Kickoff Meeting
Every demo above runs on synthetic or generated data — none of it should be presented as validated against operator's real operations. Say this explicitly, up front, in the meeting.
Suggested demo order: Pilgrim Onboarding (3) first — most deterministic and easiest to explain — then Invoice OCR (1), then Chatbot (2), then Itinerary (4), then Forecasting (5), with the Data Layer (6) shown as underlying both 1 and 5.
Before building, agree with the engineer on: which OCR/embedding/LLM stack to standardize on across all demos (reuse the same extraction pipeline for Problems 1 and 3 rather than building two), and how much time to spend on UI polish vs. backend logic given the meeting is a working demo, not a final product.

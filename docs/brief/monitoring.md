AI-Powered Transaction Monitoring &
Financial Crime Detection
The Challenge
How might we build an AI system that detects money laundering, fraud, and
suspicious trading patterns in real-time while dramatically reducing false
positives?
The Problem
Financial crime teams are drowning in alerts. Rule-based systems flag thousands of
transactions daily. Analysts manually review each one, pulling context from 5+ different systems,
documenting decisions, and closing 95% as false positives. Real criminals slip through while
analysts burn out.
"We get 2,000 alerts per week. I spend my day clicking through accounts, checking if
that $5,000 deposit is suspicious. Most aren't. The real fraud hides in the noise."
"Client deposits $500, trades for 10 minutes with $0.01 profit, then withdraws. That's not
trading - that's laundering. But our rules didn't catch it because the amounts were
'normal.'"
"By the time we reconstruct a fraud timeline manually - pulling trades, deposits, IP logs,
device IDs - the money is gone and the account is abandoned."
The core issue is high-volume noise from rigid rules, slow manual investigation, and reactive
detection that's always one step behind sophisticated criminals.
Why This Matters Now
Deriv processes millions of transactions monthly across deposits, trades, and withdrawals.
Financial crime risks include:
● Money laundering: Fake trades, rapid deposit-withdrawal cycles, layering through
multiple accounts
● Payment fraud: Stolen cards, chargebacks, coordinated fraud rings
● Market abuse: Opposite trading, insider trading, manipulation attempts
● Regulatory requirements: Must file SARs/STRs for suspicious activity within tight
deadlines
Current rule-based systems generate alert fatigue. The compliance team needs AI that finds
needles in haystacks and explains why something is suspicious.
The Opportunity
Build an AI-powered transaction monitoring system that:
● Behavioural anomaly detection: ML models that learn normal patterns per customer and
flag deviations

● Network analysis: Graph algorithms that identify coordinated fraud rings (shared IPs,
devices, cards, timing patterns)
● Contextual scoring: Risk scores that consider transaction history, trading behaviour,
deposit/withdrawal patterns, KYC data
● Automated evidence collection: When flagged, automatically pulls relevant logs, trades,
communications, and timeline
● False positive reduction: Learns from analyst decisions to reduce noise over time
● Real-time intervention: Flags suspicious withdrawals before funds leave, not 3 days later
● SAR preparation: Auto-generates suspicious activity report drafts with evidence and
narrative
The system should turn 2,000 alerts into 50 high-confidence cases with full investigation packs
ready for review.

Constraints
Constraint Rationale
Must demo live No slide decks. Show us working software.
AI must add value This is an AI hackathon. GenAI must be core to your solution.
Minimise false positives Alert fatigue damages analyst effectiveness. Noise kills

productivity.

Explainable decisions Analysts and regulators need to understand why activity is

flagged.

Real-time processing Detection must happen during transactions, not days later.
Questions Worth Considering
● How do you balance catching sophisticated fraud vs. not flagging legitimate high-volume
traders?
● What graph analysis techniques best reveal coordinated fraud networks?
● Should the system prioritise certain fraud types (laundering vs. card fraud vs. trading
abuse)?
● How do you handle the cold-start problem with new customers who have no behavioural
history?
● Can you generate regulator-ready narratives explaining suspicious activity?
● What makes an alert actionable vs. just noise?
● How do you explain complex network relationships to non-technical compliance officers?
What Would Blow Our Minds
● Unsupervised learning that discovers entirely new fraud typologies not in the training
data
● Temporal pattern recognition: "This account's behaviour changed dramatically 72 hours
after KYC approval"
● Network effect analysis: "This fraud ring has 47 linked accounts we didn't know about"
● Predictive flagging: Score accounts as high-risk before they commit fraud based on early
signals

● Automated SAR generation that meets regulatory quality standards with minimal human
editing
● Something that turns 2,000 weekly alerts into 50 high-confidence cases
● A system that catches the $0.01 profit laundering that rules completely miss
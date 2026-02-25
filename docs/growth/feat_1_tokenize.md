# PRD — Survey-to-Earn Social Network (Hybrid Reward + Stablecoin Payout)

## 1. Document Info
- **Project Name:** [PLACEHOLDER_PROJECT_NAME]
- **Version:** v0.1 (MVP Draft)
- **Prepared By:** Arif / Team
- **Date:** 2026-02-25
- **Status:** Draft for Architecture & Compliance Review

---

## 2. Executive Summary

This project is a **social survey platform** where users can:
- Join free or paid surveys
- Earn rewards based on participation quality and engagement rules
- Receive ecosystem rewards (token-based utility/reputation)
- Optionally withdraw eligible earnings via **stablecoin payout** and later convert to fiat using supported financial apps/providers

The platform is designed as a **hybrid system**:
- **Off-chain application layer** for social features, survey logic, scoring, anti-fraud
- **On-chain token layer** for utility/reputation and selected reward distribution events
- **Payout abstraction layer** for stablecoin and/or fiat-compatible payout providers

### Core Principle
> The system should be designed as a **utility + reward platform**, not as an investment product.

---

## 3. Problem Statement

Traditional survey/reward platforms often suffer from:
- Low trust in reward distribution
- Opaque scoring and payout rules
- Fraud / bot / multi-account abuse
- Poor cross-border payout experience
- Lack of user-owned portable reward assets

This project aims to solve these by combining:
- Transparent reward rules
- Portable wallet-based reward layer
- Stablecoin-compatible payouts
- Anti-fraud controls
- Ecosystem utility token for non-cash value and platform participation

---

## 4. Goals (MVP)

### Business Goals
1. Launch an MVP that validates **survey participation + reward payout** flow
2. Support cross-border users with **wallet-based payouts (USDC preferred)**
3. Introduce a platform token as **utility/reputation**, not primary cash compensation
4. Enable sponsor-funded survey campaigns

### Product Goals
1. Smooth onboarding (email/social login + optional wallet connect)
2. Simple survey participation UX
3. Clear reward display:
   - Pending
   - Approved
   - Paid
4. Fraud-resistant participation scoring
5. Withdrawal request + payout tracking

### Technical Goals
1. Hybrid architecture (off-chain logic + on-chain token interactions)
2. Scalable backend APIs and event-driven reward processing
3. Chain-agnostic payout abstraction (provider swappable)
4. Audit-friendly reward ledger

---

## 5. Non-Goals (MVP)

The following are **out of scope for MVP**:
- Token price speculation features
- Revenue share promises tied to token appreciation
- CEX listing workflows
- Full on-chain survey execution
- Advanced DAO governance
- Algorithmic market making
- Margin/leverage/trading features
- Guaranteed returns / investment claims

---

## 6. Target Users

### Primary User Segments
1. **Survey Participants**
   - Want to earn rewards for valid participation
   - Need transparent payout status
   - Prefer easy withdrawal options

2. **Survey Sponsors / Brands**
   - Need targeted responses
   - Want fraud-resistant participants
   - Need campaign budget controls and analytics

3. **Platform Operators / Admins**
   - Need moderation, fraud review, payout controls
   - Need audit logs and exception handling
   - Need configurable reward rules

---

## 7. Product Value Proposition

### For Participants
- Earn rewards from real survey campaigns
- Track rewards transparently
- Withdraw in a modern digital payout format (e.g., stablecoin)
- Build on-platform reputation

### For Sponsors
- Better quality responses via anti-fraud and reputation scoring
- Configurable campaign rewards
- Transparent reporting and payout usage

### For Platform
- Portable token-based ecosystem utility
- Stronger trust with recorded reward actions
- Flexible payout integrations by country/provider

---

## 8. Core Product Design Principles

1. **Compliance-aware language**
   - No "investment", "guaranteed profit", "passive income" language
   - Rewards are based on platform participation and sponsor-funded campaigns

2. **Separation of concerns**
   - Token utility/reputation != cash payout
   - Cash payout comes from reward pools / sponsor budgets

3. **Fraud resistance first**
   - Multi-account and bot prevention is critical from MVP

4. **Provider abstraction**
   - Payout provider can change by region without breaking core platform

5. **Clear user trust**
   - Users see exactly why rewards were approved/reduced/rejected

---

## 9. MVP Feature Scope

## 9.1 User & Identity
- Sign up / Login (email + OTP or social login)
- Optional wallet connect (EVM wallet)
- User profile
- Country selection
- Basic KYC status flag (if payout provider requires)

## 9.2 Survey Discovery & Participation
- Survey feed
- Survey details page
- Eligibility checks (country, profile, quota)
- Participation form flow
- Submission confirmation
- Duplicate participation prevention

## 9.3 Reward Engine (Off-chain)
- Reward rules per campaign:
  - fixed reward
  - variable reward by quality score
  - bonus by campaign milestones/popularity brackets
- Pending reward calculation
- Fraud review queue
- Approval / rejection actions
- Reward ledger entries

## 9.4 Ecosystem Token (On-chain + App Utility)
- ERC-20 token (utility/reputation)
- Non-cash utility examples:
  - access to premium surveys
  - reduced fees for sponsors
  - anti-spam staking for survey creation
  - reputation amplification (bounded)
  - governance-ready (future)
- Token transfer visibility in app
- Wallet balance sync

## 9.5 Payouts (MVP)
- Withdrawal request flow
- Payout method selection:
  - wallet (USDC on supported chain)
  - future: provider-linked fiat payout
- Payout status tracking:
  - Requested
  - In Review
  - Approved
  - Processing
  - Completed
  - Failed
- Payout history

## 9.6 Admin Panel (MVP)
- User management
- Survey campaign management
- Reward review queue
- Fraud flags & risk signals
- Payout approval queue
- Audit logs

## 9.7 Sponsor/Brand Panel (Lite MVP)
- Create survey campaign
- Set budget and reward model
- Monitor participation count
- View basic analytics
- Pause/Resume campaign

---

## 10. Reward Model (MVP Recommendation)

### Reward Types
1. **Cash-equivalent reward (Primary)**
   - Paid from sponsor-funded campaign budget
   - Denominated in platform ledger and paid via stablecoin (e.g., USDC)

2. **Ecosystem token reward (Secondary)**
   - Utility/reputation/engagement incentive
   - Non-guaranteed cash value
   - Can be used inside platform

### Important Constraint
> Do NOT define user compensation as "token price increase sharing".
> Instead, define compensation as campaign-funded rewards + optional ecosystem incentives.

### Popularity-Based Incentives (Safer Alternative)
Instead of "token value increases with popularity":
- Use **campaign popularity score** to unlock:
  - bonus reward pools
  - sponsor-funded milestone bonuses
  - platform token bonuses
- Keep bonus logic tied to **platform activity**, not investment return expectations

---

## 11. High-Level User Flows

## 11.1 Participant Earn Flow
1. User signs up
2. User completes profile and wallet connect (optional but recommended)
3. User joins eligible survey
4. Submission is scored and fraud-checked
5. Reward appears as **Pending**
6. Admin/system approves
7. Reward becomes **Available**
8. User requests payout (USDC wallet)
9. Payout is processed and status updated

## 11.2 Sponsor Survey Campaign Flow
1. Sponsor creates survey campaign
2. Defines target users, reward budget, duration
3. Campaign goes live after review
4. Users participate
5. Sponsor views results and budget usage
6. Campaign closes automatically/manual

## 11.3 Ecosystem Token Utility Flow
1. User earns utility tokens via engagement/reputation rules
2. User uses token to unlock premium surveys / perks
3. Sponsor stakes tokens to reduce spam and improve trust level
4. Token acts as ecosystem layer, not guaranteed cash claim

---

## 12. Compliance-Aware Product Language (Required)

### Allowed Language Examples
- "Rewards"
- "Participation incentives"
- "Campaign-funded payouts"
- "Utility token"
- "Ecosystem token"
- "Reputation score"
- "Eligibility-based payout"

### Avoid / Restricted Language Examples
- "Investment"
- "Guaranteed profit"
- "Passive income"
- "Dividend"
- "Revenue share from token appreciation"
- "Guaranteed token price increase"

---

## 13. Risks & Mitigations (MVP)

### Risk 1 — Fraud / Bot Participation
- **Mitigation:** device fingerprinting, rate limiting, wallet reputation, duplicate checks, manual review queue

### Risk 2 — Regulatory Misinterpretation
- **Mitigation:** utility-focused token design, no profit promises, legal review before public launch

### Risk 3 — Payout Provider Constraints by Country
- **Mitigation:** payout abstraction layer, region-based provider routing, fallback to wallet payout

### Risk 4 — Token Speculation Overshadowing Product Utility
- **Mitigation:** token utility-first design, separate reward pool accounting from token market price

### Risk 5 — Sponsor Abuse / Low-quality Surveys
- **Mitigation:** campaign review workflow, quality policies, minimum standards

---

## 14. Success Metrics (MVP)

### User Metrics
- Sign-up conversion rate
- Survey completion rate
- Reward approval rate
- Withdrawal completion rate
- 30-day retention

### Fraud Metrics
- Duplicate participation rate
- Flagged accounts rate
- Rejected submissions rate
- Chargeback/dispute rates (if applicable)

### Sponsor Metrics
- Campaign completion rate
- Cost per valid response
- Repeat sponsor rate
- Budget utilization efficiency

### Platform Metrics
- Payout success rate
- Reward processing latency
- Token utility feature usage rate
- Support ticket rate per 1,000 users

---

## 15. MVP Rollout Plan

### Phase 1 — Closed Alpha
- Internal team + invited testers
- Wallet payout only (USDC)
- Manual admin review for rewards and payouts

### Phase 2 — Private Beta
- Limited real sponsors
- Rule-based fraud scoring
- Pilot payout provider integration (optional)

### Phase 3 — Public MVP
- Broader region rollout
- Provider abstraction enabled
- Token utility features expanded

---

## 16. Open Questions (To Resolve Before Build)
1. Which countries are in initial rollout scope?
2. Will wallet be mandatory for withdrawals?
3. What minimum payout threshold should be used?
4. Which chain will be used for token + USDC payouts (Base recommended)?
5. Will the token have fixed supply or governed mint schedule?
6. What legal/compliance review coverage is required for target geographies?
7. Which payout provider(s) are available via API/partnership?

---

## 17. Appendix — Initial Product Positioning Statement (Draft)

[PROJECT_NAME] is a survey and engagement platform that rewards valid participation through campaign-funded incentives and ecosystem utility features. The platform combines a modern social participation experience, transparent reward tracking, and digital payout options while maintaining a utility-first token design.
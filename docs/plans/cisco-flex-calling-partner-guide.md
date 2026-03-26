# Cisco Collaboration Flex Plan — Partner Guide

**Audience:** Cisco Partners / VARs / MSPs
**Focus:** Flex Calling Plans, True Forward, Purchasing, and Change Management
**Last Updated:** March 2026

---

## Table of Contents

1. [What Is the Flex Plan?](#1-what-is-the-flex-plan)
2. [Flex Calling License Tiers](#2-flex-calling-license-tiers)
3. [Buying Models — EA vs Named User](#3-buying-models--ea-vs-named-user)
4. [True Forward — How It Works](#4-true-forward--how-it-works)
5. [Purchasing Flow for Partners](#5-purchasing-flow-for-partners)
6. [Who Signs What](#6-who-signs-what)
7. [Change / Modify / Grow](#7-change--modify--grow)
8. [Renewals](#8-renewals)
9. [Quick Reference: Pricing](#9-quick-reference-pricing)
10. [Key Documents & Where to Find Them](#10-key-documents--where-to-find-them)
11. [Common Partner Questions](#11-common-partner-questions)

---

## 1. What Is the Flex Plan?

The **Cisco Collaboration Flex Plan 3.0** is Cisco's subscription licensing model for their entire collaboration portfolio. It converts traditional capex (perpetual licenses + SmartNet) into predictable opex with monthly per-user pricing.

### What It Covers

| Product Area | Deployment Options |
|---|---|
| **Webex Calling** | Multi-tenant cloud |
| **Dedicated Instance** | Cloud-hosted UCM (add-on to Webex Calling) |
| **On-Premises Calling** | CUCM / BE6K / BE7K subscription |
| **Webex Meetings** | Cloud |
| **Webex Suite** | Calling + Meetings + Messaging + Events (bundle) |
| **Contact Center** | UCCX / PCCE / Webex Contact Center |
| **Customer Assist** | Contact center-lite for Webex Calling |

**Key point for partners:** Customers can purchase individual products (just Calling, just Meetings) or bundles (Webex Suite). They can also run cloud and on-premises calling simultaneously during a migration — Cisco offers an 18-month transition license for this.

---

## 2. Flex Calling License Tiers

### Cloud Calling Licenses

| | Professional | Standard | Common Area / Workspace |
|---|---|---|---|
| **SKU** | A-FLEX-NUCL-P | A-FLEX-NUCL-S | A-FLEX-NUCL-E |
| **MSRP** | ~$12.50/user/mo | ~$10.65/user/mo | ~$7.50/device/mo |
| **Devices** | Up to 5 (all softclients = 1) | 1 only (phone OR softclient) | 1 |
| **Shared Lines** | Yes (up to 35) | No | No |
| **Virtual Lines** | Yes (1:1 per license) | No | No |
| **Voicemail** | Yes | Yes | No |
| **Call Recording** | Yes | Yes | No |
| **Call Queues** | Yes (agent eligible) | No | Yes (basic) |
| **Hunt Groups** | Yes | Yes | Yes |
| **Executive/Assistant** | Yes | No | No |
| **Hot Desking** | Yes (user + guest) | No | No |
| **AI Assistant** | Yes | No | No |
| **MS Teams Integration** | Yes | Yes | No |
| **Webex Go (mobile)** | Included | No | No |
| **Customer Assist eligible** | Yes | No | No |

### On-Premises Calling Licenses

| | Professional (On-Prem) | Enhanced (On-Prem) |
|---|---|---|
| **SKU** | A-FLEX-NUPL-P | A-FLEX-NUPL-E |
| **MSRP** | ~$8.75/user/mo | ~$4.75/user/mo |
| **Covers** | CUCM, Unity Connection, Jabber, Expressway | Same, reduced feature set |

### Add-Ons (Separate Purchase)

| Add-On | Notes |
|---|---|
| **PSTN / Cisco Calling Plan** | Starting ~$3.50/user/mo. Not included in Flex. Options: Cisco Calling Plan, Cloud Connected PSTN, or Local Gateway. |
| **Customer Assist** | Includes Professional Calling license. Adds screen pop, skill-based routing, supervisor tools, wrap-up codes. |
| **Device Subscription** | Per-device subscription for phones, video, headsets. Includes cloud registration + software updates. |
| **Transition License** | 18-month dual-environment license for CUCM-to-Webex migrations. |
| **Dedicated Instance** | Cloud-hosted UCM. Add-on to Webex Calling. |

### What's Included at No Extra Cost (Location-Level)

Auto attendant, call pickup groups, voice portal, basic call queues, DECT networks, voicemail groups, hunt groups, call park, paging groups, music on hold.

---

## 3. Buying Models — EA vs Named User

There are two primary buying models for Flex Calling. The right choice depends on customer size and deployment scope.

### Enterprise Agreement (EA)

| Aspect | Details |
|---|---|
| **Who it's for** | Organizations licensing ALL Knowledge Workers |
| **Minimum** | 250 Knowledge Workers |
| **Pricing** | Per-user/month, volume tiered |
| **Growth Allowance** | 15% above committed quantity (no extra charge) |
| **True Forward** | Yes — annual reconciliation (see Section 4) |
| **Common Area** | Included: 50% of Knowledge Worker count at no extra charge |
| **Can reduce mid-term?** | No |
| **Value Shift** | Unused licenses in one product offset overage in another within the same suite |

**When to recommend EA:** Customer has 250+ users, wants enterprise-wide coverage, values the growth buffer and value-shift flexibility.

### Named User (NU)

| Aspect | Details |
|---|---|
| **Who it's for** | Departments, teams, or smaller deployments |
| **Minimum** | No minimum for Calling (5 users for Webex Suite NU) |
| **Pricing** | Per-user/month, you pay for each named user |
| **Growth Allowance** | None — you pay for what you order |
| **True Forward** | No — not applicable to Named User |
| **Can reduce mid-term?** | No (committed for term length) |

**When to recommend NU:** Customer wants to license specific users/departments, has fewer than 250 users, or doesn't want to commit to org-wide licensing.

### Volume Tiers (Both Models)

| Tier | User Count |
|---|---|
| Tier 1 | 250 – 1,999 |
| Tier 2 | 2,000 – 9,999 |
| Tier 3 | 10,000+ |

Higher tiers = deeper discounts. Multi-year terms (3 or 5 years) provide additional incentives.

---

## 4. True Forward — How It Works

True Forward is the mechanism Cisco uses to reconcile usage in Enterprise Agreement subscriptions. **It only applies to the EA buying model** — Named User customers simply order the quantities they need.

### The Core Concept

```
Traditional True-Up:    "You used more → pay us for the past overage"
Cisco True Forward:     "You used more → your new baseline goes up going forward"
```

**The key difference:** There is NO retroactive billing. If a customer exceeds their committed quantity during the year, they consumed those extra licenses for free. At the anniversary, the subscription simply adjusts upward.

### Timeline

```
Year 1 Start          Year 1 Anniversary       Year 2 Anniversary
    |                        |                        |
    |   Customer grows       |   True Forward          |   True Forward
    |   beyond committed     |   evaluated             |   evaluated
    |   quantity             |                        |
    |   (no extra charge     |   New baseline =        |   New baseline =
    |    during the year)    |   actual consumption    |   actual consumption
    |                        |   (if above committed)  |   (if above committed)
```

### Step by Step

1. **Customer signs EA** for 500 Webex Calling Professional licenses
2. **Growth allowance kicks in** — customer can use up to 575 licenses (500 + 15%) without triggering True Forward
3. **During the year**, customer grows to 600 users (exceeds the 575 growth buffer)
4. **~30 days before anniversary**, Cisco's automated system in CCW compares Control Hub consumption data against entitlements
5. **At the anniversary (True Forward Anniversary Date / TFAD)**:
   - Overconsumption detected: 600 actual vs 575 allowed
   - New committed quantity = 600
   - Customer pays: `Unit Price × 25 additional users × Remaining months in term`
6. **New growth allowance** recalculates: 600 + 15% = 690 users before next True Forward

### What If They DON'T Exceed the Buffer?

If the customer grows from 500 to 560 users (within the 15% / 575 buffer), **nothing happens**. No True Forward event. No additional charges. The committed quantity stays at 500.

### Can the Customer Ever Go DOWN?

**No.** The entitlement can only increase. Even if the customer drops from 600 back to 400 users, they remain committed to the 600-user baseline through the end of the term. This is not negotiable mid-term.

### Intra-Suite Value Shift

If the customer has a Webex Suite EA (Calling + Meetings + Messaging) and they're:
- **Over** on Calling licenses
- **Under** on Meetings licenses

The residual value of unused Meetings licenses automatically offsets the Calling overage. This happens automatically — no partner action needed. Value shift is calculated on purchase value, not license count, and only works within the same suite.

### How to Monitor

| Tool | What It Shows |
|---|---|
| **Control Hub** → True Forward Reports | Current consumption vs entitlements, health status |
| **Enterprise Agreement Workspace (EAWS)** | Most accurate real-time consumption view |
| **CCW** | Subscription details, upcoming True Forward events |

Partners with external admin access to the customer's Control Hub can view consumption directly.

---

## 5. Purchasing Flow for Partners

### Prerequisites

- Partner must be **SaaS Subscription Resale** certified
- Access to **Cisco Commerce Workspace (CCW)**
- Familiarity with CCW Annuity platform

### Step-by-Step Ordering

```
Step 1: A2Q Review
    ↓
Step 2: Create Estimate in CCW
    ↓
Step 3: Build Configuration
    ↓
Step 4: Generate Quote
    ↓
Step 5: Attach Required Documents
    ↓
Step 6: Submit for Approval
    ↓
Step 7: Convert to Order
    ↓
Step 8: Provisioning Begins
```

#### Step 1 — A2Q (Approval to Quote)

Before creating any order configuration, submit an **Approval to Quote (A2Q)** request through the A2Q portal. This is required for:
- Initial Flex Plan purchases
- Design changes during the subscription term
- Adding new suites or products

**Do not skip this step.** Orders created without A2Q approval may be delayed or rejected.

#### Step 2 — Create Estimate in CCW

Navigate to CCW and start a new Collaboration Flex Plan estimate. The guided selling flow uses the single top-level SKU **A-FLEX** and dynamically generates options based on your selections:
- Buying model (EA or Named User)
- Products (Calling, Meetings, Suite, etc.)
- License tiers (Professional, Standard, Common Area)
- Term length (1, 3, or 5 years)
- Billing frequency (prepaid, annual, quarterly, monthly)

#### Step 3 — Build Configuration

Select specific quantities, add-ons (PSTN, devices, Customer Assist), and any applicable promotions or incentives. For EA, define the Knowledge Worker count.

#### Step 4 — Generate Quote

CCW applies any push promotion discounts. At this stage you can choose incentives (OIP hunting/teaming) via "Create a Deal."

#### Step 5 — Attach Required Documents

**Critical:** Attach all required documents to the order. Documents attached to the quote do NOT flow through to the order — you must re-attach at order time. Required documents include:
- Completed and signed **End User Information Form (EUIF)**
- Any A2Q approval documentation

#### Step 6 — Submit for Approval

Submit the configured order for Cisco approval.

#### Step 7 — Convert to Order

Once approved, convert the quote to a live order in CCW.

#### Step 8 — Provisioning

After order processing, the customer's Webex organization is provisioned (or updated) with the purchased licenses. Licenses appear in Control Hub.

---

## 6. Who Signs What

### Document Stack

| Document | Who Signs/Acknowledges | Purpose |
|---|---|---|
| **Cisco General Terms** | Customer (acceptance at purchase) | Overarching terms for all Cisco software/cloud services |
| **EA Program Terms** | Customer (acknowledgment at order) | Governs the Enterprise Agreement relationship (EA only) |
| **Flex Plan Offer Description** | Reference (no signature) | Defines what's included, usage rights, restrictions |
| **Buying Program Offer Description** | Reference (no signature) | Supplemental terms for the Flex Plan portfolio |
| **End User Information Form (EUIF)** | Customer's authorized representative (signature required) | Basis for price quote; defines Knowledge Worker count for EA |

### Key Points

- The **EUIF** is the primary document requiring a customer signature — it must be completed by the customer's authorized representative
- For **EA purchases**, the customer must acknowledge the EA Program Terms at order time
- The **Partner** is the ordering entity in CCW and facilitates the process, but the customer is the end user on the agreement
- **Cisco General Terms** are accepted as part of the purchasing process (not a separate signing ceremony)
- The Offer Description and Buying Program Description are reference documents that define the terms — they don't require separate signatures but are incorporated by reference

---

## 7. Change / Modify / Grow

### Mid-Term Additions (Most Common)

When a customer needs more licenses during the subscription term:

1. **Partner** opens "Modify My Subscription" in CCW
2. Select the active subscription to modify
3. Add quantities (new users, new license tiers, new add-ons)
4. New licenses are **co-terminated** with the original order by default
5. Customer pays the prorated amount for the remaining term
6. An **A2Q post-sale review** may be required for significant design changes

### What You CAN Change Mid-Term

| Change | Allowed? |
|---|---|
| Add more licenses (same tier) | Yes |
| Add a new license tier (e.g., add Standard to existing Professional) | Yes |
| Add new products (e.g., add Meetings to existing Calling) | Yes |
| Add new add-ons (PSTN, devices, Customer Assist) | Yes |
| Upgrade buying model (NU → EA) | Yes |

### What You CANNOT Change Mid-Term

| Change | Allowed? |
|---|---|
| Reduce committed license quantities | No |
| Downgrade buying model (EA → NU) | No |
| Downgrade license tier (Professional → Standard) | No |
| Cancel the subscription | No (committed for term) |

### Co-Termination Rules

- All mid-term additions **automatically co-terminate** with the initial order
- If **less than 12 months remain** on the current term, a new separate purchase is required (cannot co-terminate)
- You can opt out of co-termination for a new suite, but this creates a separate subscription with its own term and True Forward cycle

### Buying Model Upgrades

During the subscription, you can upgrade (but never downgrade) the buying model:

```
Named User  →  Enterprise Agreement     ✓
Named User  →  Active User (Meetings)   ✓
Active User →  Enterprise Agreement     ✓
EA          →  Named User               ✗
```

---

## 8. Renewals

### Auto-Renewal

Flex Plan subscriptions **auto-renew** unless the customer or partner provides written notice to their Approved Source at least **45 days before** the end of the current Use Term.

### Renewal Process

1. Use "Renew Your Subscription" in CCW
2. Changes (quantities, billing frequency, added products) take effect for the new term
3. Cisco will notify of any fee changes reasonably in advance of renewal

### What Can Change at Renewal

| Change | Allowed at Renewal? |
|---|---|
| Adjust quantities (increase) | Yes |
| Change billing frequency | Yes (prepaid, annual, quarterly, monthly) |
| Add new products or tiers | Yes |
| Change term length | Yes |
| Adjust quantities (decrease) | Consult your Cisco account team — not explicitly documented for renewals |

### Term Length Options

| Term | Notes |
|---|---|
| 1 year | Minimum term (no trade-in credits) |
| 2 years | Minimum if using perpetual license trade-in credits |
| 3 years | Standard multi-year term, additional discounts |
| 5 years | Maximum standard term, deepest discounts |

---

## 9. Quick Reference: Pricing

> **Note:** All prices are approximate MSRP (Manufacturer's Suggested Retail Price) for reference. Actual partner pricing is available through CCW and varies by deal, volume tier, term length, and applicable promotions. Cisco does not publish official list prices publicly.

### Cloud Calling

| License | MSRP (per user/month) |
|---|---|
| Professional | ~$12.50 |
| Standard | ~$10.65 |
| Common Area / Workspace | ~$7.50 |

### On-Premises Calling

| License | MSRP (per user/month) |
|---|---|
| Professional (CUCM) | ~$8.75 |
| Enhanced (CUCM) | ~$4.75 |

### Add-Ons

| Add-On | MSRP (per user/month) |
|---|---|
| Cisco Calling Plan (PSTN) | Starting ~$3.50 |
| Device Subscription | Varies by device type |
| Customer Assist | Not publicly listed (includes Professional calling) |
| Dedicated Instance | Not publicly listed |
| Transition License (18-mo) | Not publicly listed |

### Volume Discount Tiers

| Tier | User Count | Discount Level |
|---|---|---|
| Tier 1 | 250 – 1,999 | Standard |
| Tier 2 | 2,000 – 9,999 | Enhanced |
| Tier 3 | 10,000+ | Enterprise |

---

## 10. Key Documents & Where to Find Them

### Cisco Official Documents

| Document | Location |
|---|---|
| **Flex Plan 3.0 Data Sheet** | [cisco.com — Collaboration Flex Plan Data Sheet](https://www.cisco.com/c/en/us/products/collateral/unified-communications/cisco-collaboration-flex-plan/collaboration-flex-plan3-data-sheet.html) |
| **Offer Description** | [cisco.com — Offer Descriptions](https://www.cisco.com/c/dam/en_us/about/doing_business/legal/OfferDescriptions/cisco_collaboration_flex_plan.pdf) |
| **EA Program Terms** | [cisco.com — Buying Programs](https://www.cisco.com/c/dam/en_us/about/doing_business/legal/buying-programs/EA-Program-Terms-for-Collab-Flex-End-Users.pdf) |
| **Buying Program Offer Description** | [cisco.com — Buying Programs](https://www.cisco.com/c/dam/en_us/about/doing_business/legal/buying-programs/BP-Offer-Description-Collab-Flex-Plan.pdf) |
| **Feature Comparison by License** | [help.webex.com — Features by License Type](https://help.webex.com/en-us/article/n1qbbp7/) |
| **True Forward FAQ** | [cisco.com — EA Q&A](https://www.cisco.com/c/en/us/products/collateral/software/enterprise-agreement/q-and-a-c67-743368.html) |
| **Ordering Guides** | [cisco.com — Collaboration Ordering Guides](https://www.cisco.com/c/en/us/partners/tools/collaboration-ordering-guides.html) (partner login required) |
| **All Data Sheets** | [cisco.com — Flex Plan Data Sheet Listing](https://www.cisco.com/c/en/us/products/unified-communications/collaboration-flex-plan/datasheet-listing.html) |

### Monitoring Tools

| Tool | Purpose |
|---|---|
| **Control Hub** | True Forward reports, consumption health, license usage |
| **EA Workspace (EAWS)** | Real-time consumption vs entitlements |
| **CCW** | Subscription management, change/renew orders |

---

## 11. Common Partner Questions

**Q: Does the customer need PSTN separately?**
A: Yes. Flex Calling licenses do NOT include PSTN. The customer needs one of: Cisco Calling Plan (~$3.50/user/mo), Cloud Connected PSTN (third-party), or Local Gateway (customer-owned SBC).

**Q: Can a customer mix Professional and Standard licenses?**
A: Yes. You can have Professional users and Standard users in the same org. Standard users cannot use shared lines, virtual lines, call queues, or executive/assistant features.

**Q: What happens if a customer with EA shrinks below their committed count?**
A: They still pay for the committed count. EA commitments can only go up, never down, during the term.

**Q: How does the 15% growth allowance work exactly?**
A: If the customer commits to 1,000 users, they can use up to 1,150 users (1,000 + 15%) without triggering a True Forward event. If they exceed 1,150, a True Forward adjusts them to their actual count at the anniversary. The growth allowance buffer kicks in after the first 6 months.

**Q: Is there a penalty for exceeding the growth buffer?**
A: No penalty. They just start paying for the additional users going forward from the anniversary date. The overconsumption during the year is not billed retroactively.

**Q: Can we move from Named User to EA mid-term?**
A: Yes. Named User → EA is an allowed upgrade path. The reverse (EA → Named User) is not.

**Q: What's the minimum commitment for Flex Calling?**
A: Named User has no minimum for calling. EA requires 250 Knowledge Workers minimum.

**Q: How do Common Area licenses work under EA?**
A: EA includes Common Area licenses equal to 50% of the Knowledge Worker count at no extra charge. For example, 1,000 KW EA = 500 Common Area licenses included.

**Q: What if the customer wants to cancel mid-term?**
A: They can't. The subscription is committed for the full term. They can stop using the licenses, but payment continues.

**Q: Does Customer Assist require a separate Calling license?**
A: No. Customer Assist includes a Professional Calling license. It's not an add-on to Professional — it replaces it at a higher price point.

---

*This guide is based on publicly available Cisco documentation as of March 2026. Partner-confidential pricing, promotions, and ordering details are available through CCW and your Cisco account team. Always verify current terms against the latest Offer Description and EA Program Terms before presenting to customers.*

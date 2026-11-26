import { KnowledgeArticle, CannedMacro } from '../types';

export const KNOWLEDGE_BASE_ARTICLES: KnowledgeArticle[] = [
  {
    id: 'kb-billing-double-charge',
    title: 'Resolving Duplicate Authorizations & Overcharges',
    category: 'Billing',
    relevance: 98,
    summary: 'Procedures for immediately clearing temporary pending authorizations vs posted duplicate charges.',
    snippet: 'When a customer sees dual charges, verify pending pre-authorizations in Stripe Ledger. If settled twice, initiate instant reversal without requiring bank statements if under $250.',
    actionSteps: [
      'Check payment gateway transaction IDs for duplicate order references.',
      'If authorization is PENDING: explain bank holding period (2-5 business days) and offer an official release letter.',
      'If charges are SETTLED: execute immediate 1-click refund to original payment method.',
      'Apply standard courtesy credit of $15-$25 for inconvenience when customer expressed distress.'
    ],
    policyExceptions: [
      'Frontline agents authorized to issue refunds up to $300 without supervisor approval.',
      'Same-day express release authorization can be faxed/emailed to customer bank directly.'
    ],
    lastUpdated: 'Updated 2 days ago'
  },
  {
    id: 'kb-cancellation-retention',
    title: 'Customer Cancellation & Subscription Retention Protocol',
    category: 'Policy',
    relevance: 92,
    summary: 'Guidelines for handling subscription cancellation threats, churn prevention, and grace period extensions.',
    snippet: 'Listen actively without arguing. Acknowledge frustration, address the root blocker, and deploy tiered retention incentives before processing final termination.',
    actionSteps: [
      'Validate customer grievances: never say "policy forbids refunds" on initial response.',
      'Offer 1-month pause or 30% loyalty discount for the next 3 billing cycles.',
      'If customer insists on cancellation, process smoothly with zero penalty and confirm data export.'
    ],
    policyExceptions: [
      'VIP enterprise accounts qualify for dedicated CS account manager review within 2 hours.',
      'Pro-rated refunds permitted within 14 days of automatic yearly renewals.'
    ],
    lastUpdated: 'Updated 1 week ago'
  },
  {
    id: 'kb-service-outage-sla',
    title: 'Enterprise Service Disruption & SLA Breach Escalation',
    category: 'Technical',
    relevance: 95,
    summary: 'Operational runbook for severe outages affecting production workloads, API degradation, and SLA credits.',
    snippet: 'For P1 critical incidents, provide incident ticket # and link to status.service.io. Agents must provide updates every 15 minutes until resolution.',
    actionSteps: [
      'Confirm tenant cluster ID and verify ongoing incident in OpsGenie/PagerDuty.',
      'Provide current status update: "Engineering team is actively rolling back release v4.12".',
      'Provide SLA compensation calculator: Tier 1 customers receive 10% monthly credit for every 30min outage.'
    ],
    policyExceptions: [
      'Emergency standby bridge link can be provided to Enterprise accounts with premium SLA.',
      'Supervisor warm-handoff mandatory if customer mentions legal counsel or contractual liquidated damages.'
    ],
    lastUpdated: 'Updated yesterday'
  },
  {
    id: 'kb-hardware-defective-expedite',
    title: 'Defective Equipment Replacement & Advanced Hardware Exchange',
    category: 'Hardware',
    relevance: 88,
    summary: 'Handling DOA (Dead on Arrival) units, return shipping waivers, and priority overnight dispatch.',
    snippet: 'If a customer received broken hardware or failed delivery, bypass standard 14-day return inspection. Authorize cross-shipping replacement immediately.',
    actionSteps: [
      'Request serial number or photos only if readily available; do not stall if customer is distressed.',
      'Generate prepaid FedEx Priority Overnight return label.',
      'Trigger warehouse dispatch for advanced replacement unit before old unit is received.',
      'Waive $35 restocking and expedite fees unconditionally.'
    ],
    policyExceptions: [
      'Advanced hardware swap is normally restricted to Warranty Plus, but frontline can override for escalated complaints.'
    ],
    lastUpdated: 'Updated 3 days ago'
  },
  {
    id: 'kb-account-lockout-security',
    title: 'MFA Lockout & Urgent Account Recovery Verification',
    category: 'Account Security',
    relevance: 84,
    summary: 'Secure verification workflow for locked enterprise admins and lost authenticator devices.',
    snippet: 'Verify identity through registered secondary phone or corporate domain DNS challenge. Never send temporary passwords via unsecured plain text.',
    actionSteps: [
      'Send one-time cryptographic push verification to registered mobile number.',
      'Check for recent suspicious IP logins or brute-force lockouts.',
      'Reset MFA seeds and provide 15-minute emergency bypass token.'
    ],
    policyExceptions: [
      'Single-sign on bypass requires approval from company account administrator.'
    ],
    lastUpdated: 'Updated 4 days ago'
  }
];

export const CANNED_MACROS: CannedMacro[] = [
  {
    id: 'macro-empathy-apology',
    title: 'Sincere Apology & Accountability',
    shortcut: '/apology',
    category: 'Empathy',
    text: 'I truly apologize for this frustrating experience, {customer_name}. You have every right to expect seamless service, and I am personally taking ownership of this right now to make it right for you.'
  },
  {
    id: 'macro-duplicate-refund',
    title: 'Duplicate Charge Reversal Confirmation',
    shortcut: '/duprefund',
    category: 'Billing',
    text: 'I have investigated your ledger and can confirm the duplicate transaction of {amount}. I have just issued an immediate reversal directly back to your card. You will see this reflected in 2-3 business days, and I have waived next month\'s fee as our apology.'
  },
  {
    id: 'macro-investigating',
    title: 'Action-First Investigation Hold',
    shortcut: '/hold',
    category: 'Communication',
    text: 'I am pulling up your server logs and payment records right now. Please allow me about 90 seconds while I examine the exact error traces. I will stay right here with you.'
  },
  {
    id: 'macro-supervisor-warm-transfer',
    title: 'Supervisor Warm Introduction',
    shortcut: '/escalate',
    category: 'De-escalation',
    text: 'Because this issue deserves our highest level of review, I have briefed my Senior Support Lead, {supervisor_name}, with full details of our conversation so you won\'t have to repeat yourself. She is ready to join us now.'
  },
  {
    id: 'macro-resolution-wrapup',
    title: 'Confirmed Resolution & Direct Extension',
    shortcut: '/resolved',
    category: 'Closing',
    text: 'Everything has now been corrected on our end. I have sent a written confirmation to {email} alongside your direct reference ID #{ticket_id}. Is there anything else at all I can verify for you today?'
  }
];


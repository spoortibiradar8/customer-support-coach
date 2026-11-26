# Knowledge Recommendation Agent & Panel

## Overview
This module implements the **Knowledge Recommendation Agent** and the interactive **Knowledge & Policy UI Panel** for the live customer support console. It automatically tracks the live conversation context and dynamically recommends relevant troubleshooting runbooks, step-by-step resolution guides, frontline policy exception limits, and 1-click canned macros.

## Components Included in this Module
1. **Agent Engine**: `src/agents/knowledgeAgent.ts`
   - Keyword and semantic context matching across turn exchanges.
   - Dynamic relevance scoring (0–100%) for runbook ranking.
   - Contextual macro suggestion engine.
2. **Knowledge Base Repository**: `src/data/knowledgeBaseData.ts`
   - Structured runbooks (Billing duplicate charges, SaaS SLA outages, Defective hardware swaps, MFA lockouts).
   - Step-by-step resolution operating procedures.
   - Authorized policy overrides and frontline exception rules.
   - Canned macros with variable interpolation (`/apology`, `/duprefund`, `/hold`, `/escalate`, `/resolved`).
3. **UI Recommendation Panel**: `src/components/KnowledgePanel.tsx`
   - 3-tab layout: **Runbooks**, **Macros**, and **CRM Account Overview**.
   - Real-time search filter across articles and macros.
   - 1-click **"Insert Snippet into Draft"** integration.
   - Frontline courtesy concession budget tracking.

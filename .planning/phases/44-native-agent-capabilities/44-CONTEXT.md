# Phase 44: Native Agent Capabilities - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent narrates its work in first-person co-founder voice via a narrate() tool and generates end-user documentation natively via a document() tool — replacing both NarrationService and DocGenerationService. Both deleted services are fully removed with zero remaining references. No new agent capabilities beyond narration and documentation.

</domain>

<decisions>
## Implementation Decisions

### Narration voice & style
- Confident builder personality — "I'm setting up auth with Clerk because your brief specified enterprise-grade security." Direct, explains reasoning, sounds like a senior engineer partner
- Each narration includes WHAT the agent is doing AND WHY — ties decisions back to the founder's original brief/answers when relevant
- Narrate at significant actions only — phase/task boundaries and major decisions. Skip individual file writes, grep calls, small edits. ~1 narration per significant step
- Agent's system prompt includes narration guidance: "Narrate significant actions in first-person co-founder voice. Reference the founder's brief when relevant." The agent decides when and what to narrate — narrate() is a passthrough, not a validator

### Documentation structure
- Agent writes doc sections progressively as it builds — "I just built auth, let me document how login works." Docs reflect the actual implementation
- 4 sections: overview, features, getting_started, faq — matches existing Redis hash structure in job:{id}:docs
- Documentation written for end-users of the built product — "To sign up, click Create Account..." The founder can hand these to their users
- Separate document() tool distinct from narrate() — document(section='getting_started', content='...'). Writes to job:{id}:docs Redis hash

### Narration delivery timing
- Each narrate() call emits an SSE event immediately — founder sees updates in real time as the agent works
- Narration API calls count toward the token budget — honest cost accounting, can trigger sleep if budget consumed
- Reuse existing narration SSE event type — frontend already handles it, zero UI changes needed
- Narrations persist to the job:{id}:logs Redis stream — late-connecting founders can replay all past narrations

### Service deletion & tool integration
- Full deletion of NarrationService and DocGenerationService — delete files, remove all imports, delete their tests, remove route references. grep for zero remaining references
- narrate() and document() tools added to existing tool dispatch system alongside read_file, write_file, etc. — no separate dispatcher or registry
- Write dedicated tests for narrate() and document() tools — verify SSE emission, Redis persistence, budget tracking. Replace deleted NarrationService tests

### Claude's Discretion
- Exact SSE event type name to reuse (inspect existing NarrationService SSE events)
- How narrate() and document() are registered in the tool dispatch system (tool definition format)
- System prompt wording for narration guidance
- Whether document() also emits SSE events or only writes to Redis

</decisions>

<specifics>
## Specific Ideas

- Narrations should feel like a co-founder giving a standup update, not a robot reporting status
- Reference the founder's brief/answers when it adds value — "because you mentioned wanting enterprise security" makes the founder feel heard
- Documentation should be something the founder can hand directly to their end-users — practical, not architectural

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 44-native-agent-capabilities*
*Context gathered: 2026-02-27*

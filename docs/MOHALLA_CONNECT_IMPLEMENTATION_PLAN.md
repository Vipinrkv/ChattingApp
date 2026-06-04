# Mohalla Connect Implementation Plan

## Purpose

This implementation plan translates the Mohalla Connect architecture into a practical delivery sequence. It is designed for execution by a development team building a Supabase/PostGIS-backed mobile-first hyperlocal social network.

## Scope

Included in this plan:

- Supabase schema and PostGIS location data
- Row Level Security (RLS) for society portal content
- Proximity-based public feed and merchant discovery
- Mobile-first Expo React Native screens and flows
- Secure neighbor chat session invitations
- Merchant onboarding and announcement publication
- Audit logging and spam protection for local content

## Phase 1: Planning and foundation

1. Review and finalize `docs/MOHALLA_CONNECT_ARCHITECTURE.md`.
2. Add Supabase folders and baseline migration files under `backend/supabase/`.
3. Establish PostGIS extensions and schema for posts, merchants, societies, memberships, threads, and help directory.
4. Add audit logging and spam reporting tables.
5. Define RLS policy files for society portal and merchant visibility.
6. Create proximity function for nearby post queries.
7. Validate schema in Supabase local development or staging schema preview.

## Phase 2: Core backend implementation

1. Implement Supabase functions and RPC endpoints for:
   - nearby posts
   - verified merchant discovery
   - society membership checks
   - thread and comment retrieval
2. Add backend support for audit logging and spam reports.
3. Define Supabase policies to enforce resident-only access for society content.
4. Add merchant ownership controls and approval workflow.
5. Create secure session flow for "I'm Available" chat invites.
6. Test RLS and proximity rules using Supabase auth and row-level policies.

## Phase 3: Mobile UI and user flows

1. Set up an Expo React Native project with NativeWind.
2. Create screen prototypes for:
   - HomeFeedScreen
   - BusinessHubScreen
   - SocietyPortalScreen
   - MerchantPostFormScreen
   - NeighborChatScreen
   - OnboardingScreen
3. Implement geolocation permission handling and nearest feed loading.
4. Build feed cards with distance badges, category chips, and urgency signals.
5. Add merchant announcement cards and `New Openings` carousel.
6. Implement society thread creation and help directory listing.
7. Add the secure "I'm Available" button and chat invite flow.

## Phase 4: Verification, moderation, and safety

1. Add audit logging for merchants, society actions, and thread events.
2. Add spam report submission for posts, merchants, and alerts.
3. Implement client-side rate limits and server-side throttling for urgent announcements.
4. Add UI feedback for verification status and moderation outcomes.
5. Validate privacy: neighbor chat invitations must never reveal phone numbers.
6. Create moderation and review workflows for merchant verification.

## Phase 5: Release readiness

1. Add documentation links to `README.md` and `docs/README.md`.
2. Verify Supabase migrations, policy files, and RPC functions.
3. Add tests for RLS policies, proximity queries, and chat invite flows.
4. Review the Mohalla Connect plan with stakeholders.
5. Add update notes to `WorkProgress.md`.

## Execution checklist

- [x] Architecture planning documented in `docs/MOHALLA_CONNECT_ARCHITECTURE.md`
- [x] Supabase schema file created
- [x] RLS policy files created
- [x] Nearby posts proximity function created
- [ ] Expo mobile app screens and flows implemented
- [ ] Audit logging and spam reports integrated
- [ ] Rate limiting and moderation workflows created
- [ ] Documentation and release notes updated

## Notes

- Treat the current plan as a phase-1 delivery roadmap.
- A separate repository or monorepo package can be created for the Expo app if needed.
- The schema and RLS designs are ready for iterative implementation and testing.

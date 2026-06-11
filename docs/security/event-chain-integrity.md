# ChattingApp - Tamper-Evident Event Chain Integrity

To enforce immutable logging of critical social, moderation, and security events without relying on a slow, expensive public blockchain, ChattingApp implements a self-contained, hash-linked cryptographic event chain.

---

## 1. Hash-Linked Cryptographic Chain Architecture

The event log behaves like a private blockchain, where each event entry (block) contains a pointer to the hash of the immediately preceding event.

### 1.1 Structural Diagram

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ Event Block N - 1       │     │ Event Block N           │     │ Event Block N + 1       │
├─────────────────────────┤     ├─────────────────────────┤     ├─────────────────────────┤
│ ID: UUID                │     │ ID: UUID                │     │ ID: UUID                │
│ Type: "CREATE_POST"     │     │ Type: "BAN_USER"        │     │ Type: "UPDATE_PROFILE"  │
│ User ID: ...            │     │ User ID: ...            │     │ User ID: ...            │
│ Payload: JSON           │     │ Payload: JSON           │     │ Payload: JSON           │
│ Timestamp: ...          │     │ Timestamp: ...          │     │ Timestamp: ...          │
│ Previous Hash: 0x9f...  │     │ Previous Hash: 0x2a... ◄┼─────┤ Previous Hash: 0x5e...  │
│ Hash: 0x2a1d... ────────┼────►│ Hash: 0x5e3c...         │     │ Hash: 0x7b4a...         │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

If any single byte of a historical event block is modified, its hash changes. This breaks the `previous_hash` match on all subsequent blocks, immediately invalidating the chain verification.

---

## 2. Deterministic Hash Formula

For every event, the current hash is computed deterministically using SHA-256:

$$\text{Input} = \text{id} \parallel \text{event\_type} \parallel \text{event\_id} \parallel \text{user\_id} \parallel \text{timestamp.isoformat()} \parallel \text{json.dumps(payload, sort\_keys=True)} \parallel \text{previous\_hash}$$

$$\text{Current Hash} = \text{SHA-256}(\text{Input})$$

---

## 3. Auto-Verification & Detection Routine

The platform runs a background audit task (`verify_chain`) that scans the `feed_event_chain` table:
1. Fetch all events ordered by `timestamp ASC, id ASC`.
2. For each event, recalculate the hash using the deterministic formula.
3. Compare the recalculated hash against the stored `hash`.
4. Validate that `event.previous_hash` exactly matches the hash of the preceding event in the sequence.
5. If any mismatch is found, an alert is raised to the observability system (Sentry, Prometheus) and the audit panel flags a security breach.

---

## 4. Moderation & Audit Log Coverage

The event chain records:
- **Moderation Actions:** User bans, suspensions, muted accounts, report resolutions.
- **Feed Integrity:** Post creations, feed event publications.
- **Security Triggers:** Password resets, MFA modifications, session revocations.

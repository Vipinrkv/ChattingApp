# Accessibility (a11y) Design & Audit Report

This report presents accessibility compliance benchmarks, keyboard layouts, and focus state standards.

---

## 1. Focus State Standards
*   **Visible Outline Ring**: Interactive elements (inputs, buttons, anchor links, textareas) use high-contrast `:focus-visible` styling (`outline: 2px solid var(--accent)`).
*   **Keyboard Navigation Flow**: Tabs, forms, conversation lists, and dropdown triggers support sequential keyboard traversal.

---

## 2. Screen Reader Compatibility
We added ARIA attributes to ensure screen readers can navigate and interpret the app:
*   **Aria-Live announcements**: Live indicators like "Typing..." and connection state transitions ("Connected", "Disconnected") use `aria-live="polite"` and `role="status"`.
*   **Interactive labels**: Elements like floating action buttons, attachments triggers, and closing buttons use descriptive `aria-label` tags.
*   **Semantics**: Structured section tags (`<aside>`, `<section>`, `<header>`, `<article>`) organize page layout blocks.

---

## 3. High-Contrast Ratios
*   **Contrast Compliance**: Text elements use WCAG AA compliant contrast ratios relative to their background panels (4.5:1 ratio for regular body content, 3:1 for large headers).
*   **Color-Mix Styling**: Badges use a combination of opacity mixes and high-contrast text tones to ensure readability under both light and dark modes.

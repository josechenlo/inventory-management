---
name: vue-component-audit
description: Analyzes Vue component structure under client/src for performance issues and code-reuse opportunities, and reports prioritized, file/line-specific findings. Use when the user asks to review, audit, or optimize Vue components/views, or before a large refactor of client/src.
---

# Vue Component Audit

Read-only analysis skill. Produce a prioritized findings report — do not edit files unless the user explicitly asks you to apply the fixes afterward.

## Scope

Scan `client/src/views/*.vue`, `client/src/components/*.vue`, and `client/src/composables/*.js`. If the user names specific files, scope to those instead of the whole tree.

## Codebase conventions to check compliance with first

These are established, intentional patterns in this repo (see `CLAUDE.md` and existing files like `Demand.vue`, `Orders.vue`). Flag deviations as findings, not just style opinions:

- **No `<script setup>`** — every component uses `export default { name, setup() {...}, return {...} }`. A file using `<script setup>` is a convention violation, not a valid alternative.
- **Singleton composables** (`useFilters.js`, `useI18n.js`) hold shared state at module scope, not via provide/inject. New shared state should follow the same pattern, not introduce a new mechanism.
- **Global unscoped styles** live in `App.vue` (`.card`, `.stats-grid`, `.stat-card`, `.table-container`, table styles, `.badge.*`, `.loading`, `.error`, `.page-header`). A component redefining these instead of reusing them is a reuse-category finding.
- **i18n**: all user-facing strings go through `t('section.key')`; every key must exist in both `client/src/locales/en.js` and `ja.js`.

## Performance checks

For each component, look for:

1. **`v-for` keys** — index used as `:key` instead of a stable field (`sku`, `id`, `order_number`). Causes incorrect DOM reuse on reorder/insert/delete.
2. **Method calls in templates for derived data** — `{{ calculateX() }}` re-runs on every render instead of being cached via `computed()`. Flag any template expression calling a function that does filtering/reducing/sorting over a list.
3. **Watchers without debouncing on high-frequency inputs** — e.g. a `<input type="range">` or text search bound via `v-model` with a `watch()` that fires an API call on every tick. `Restocking.vue`'s 150ms `setTimeout`/`clearTimeout` debounce on the budget slider is the reference pattern; flag any new rapid-fire input lacking the same treatment.
4. **Full-page loading flicker on incremental refresh** — toggling the same `loading` ref for both the initial mount and subsequent small updates (filter change, slider drag) causes the whole view to flash to a loading skeleton. Check whether a lighter `refreshing` flag (or no flag at all) would be more correct, per `Restocking.vue`'s comment on why it doesn't toggle `loading` on debounced reloads.
5. **Sequential awaits that could be parallel** — multiple independent `api.get*()` calls awaited one after another instead of `Promise.all([...])` (see `Demand.vue`'s `loadForecasts` for the correct pattern).
6. **Unbounded list rendering** — a `v-for` over a list with no pagination/virtualization/`.slice()` cap where the list could grow large (compare to `Demand.vue`'s `.slice(0, 5)` + "+N more" pattern for trend cards).
7. **Reactive wrapping of values that are never mutated** — `ref()`/`reactive()` used for constants or props-derived read-only values that should be `computed()` or plain values.

## Code-reuse checks

1. **Duplicated loading/error/content skeleton** — every view repeats `v-if="loading" / v-else-if="error" / v-else`. This is accepted repo convention (not a finding on its own), but flag it if a *new* view invents a different shape for the same thing.
2. **Duplicated helper functions across files** — `formatDate`, `getOrderStatusClass`, the `currencySymbol` computed (`currentCurrency.value === 'JPY' ? '¥' : '$'`), `translateProductName`/`translateCustomerName` usage, etc. appear near-identically in multiple views (`Orders.vue`, `Demand.vue`, `Restocking.vue`). When a third or later view needs the same helper, that's a signal to extract it into a new composable under `client/src/composables/` (e.g. `useFormatting.js`) rather than re-pasting it — name the specific files and line ranges that duplicate the logic.
3. **Duplicated scoped CSS** — styles re-declared in `<style scoped>` blocks across files that are identical or near-identical to something already unscoped in `App.vue`, or repeated verbatim across 2+ view files (candidate to hoist into `App.vue`'s global block).
4. **Duplicated template markup** for the same visual unit (e.g. a stat card, a status badge, a details/summary dropdown) appearing in 3+ places — candidate for extraction into `client/src/components/`.
5. **Prop-drilling vs. composable** — data threaded through 2+ component levels via props/emits that could instead read directly from a shared composable, if it's genuinely cross-cutting state (not component-local).

## Report format

For each finding:

```
[Performance|Reuse] <short title>
File: client/src/views/X.vue:L123
Issue: <what's wrong, concretely>
Suggestion: <specific fix — code shape, not just "optimize this">
Priority: High|Medium|Low
```

Group findings by file, order files by finding count descending. End with a short summary: total findings by category, and the single highest-priority recommendation.

Do not flag: the standard loading/error/content skeleton, standard `export default { setup() {...} }` boilerplate, or scoped CSS with no evident duplicate elsewhere — these are intentional repo conventions, not issues.

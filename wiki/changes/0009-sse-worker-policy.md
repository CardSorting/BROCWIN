# 0009 — Preserve the existing SSE policy across Workers

[Wiki](../README.md) · [Execution](../execution.md) · [Threads](../threads-memory.md) · [Acceptance](../acceptance-session.md)

Date: 2026-10-11. Contributor: Codex /root; no delegated agents. Scope: existing client execution affecting BRC-004 revival and BRC-002 input acceptance. Native servers, SQL implementation, original game instructions, assets and UI remain unchanged.

## Observation and cause

Historical [092157](../../reports/browser/20261011T092157Z/review.json) fails independent revival. A bounded [102018 profile](../../reports/browser/20261011T102018Z/execution-cost-diagnosis.json) identifies the original D3DX x87 matrix loop among hot blocks while the application leaves the existing SSE option disabled. Instruction counts are not time percentages. The original DLL already selects an SSE implementation under this option; no replacement math is needed.

Source inspection exposes a concrete omission: `host.js` records `set_cpu_sse`, but the shared [Worker inheritance table](../../tools/wine-assembly/lib/worker-imports.js) excludes it. The [preserved control](../../reports/browser/sse-policy-20261011T105000Z/inheritance-control-v2.json) fails all four cooperative/real-Worker initial-value checks. Changing only application policy would leave spawned instances inconsistent.

## Implementation and references

Add `set_cpu_sse` / `get_cpu_sse` next to MMX in the existing table. [main.js](../../browser/main.js) enables `client.cpuSSE` before initialization. Explicit recorded zero retains precedence over the getter. [test_worker_sse.cjs](../../browser/test_worker_sse.cjs) checks actual compiled Wasm in cooperative and real Workers, including zero overrides. [prepare.py](../../browser/prepare.py) includes that test in frozen integration identities. The [candidate delta](../../reports/browser/sse-policy-20261011T105000Z/candidate-delta.patch) preserves the exact change. No WAT, JIT variant or server protocol changes.

Original x86 D3DX SHA-256 is `0b28546be22c71834501f7d7185ede5d79742457331c7ee09efc14490dd64f5f`. The [64-bit local native reference](../../reports/browser/sse-policy-20261011T105000Z/native-reference.json) uses recovered original skeleton matrices; the x86 probe compares 320 results under both policies. Its test-only initialization export is separate from production. [Provenance](../../reports/browser/sse-policy-20261011T105000Z/provenance.json) retains helpers and identities.

## Verification

[Validation](../../reports/browser/sse-policy-20261011T105000Z/validation.json): old inheritance control fails; candidate passes eight checks and the existing 73-setter test. Runtime, 21 skinning cases/4,869 vertices, 128 MOVHLPS cases and 144 scalar-SSE assertions pass. Scalar initialization alone uses existing XP winmine because upstream notepad is absent; the unavailable invocation and initial control path mistake remain recorded. Both SSE policies pass all 320 original-D3DX comparisons.

The Node matrix workload median changes from 65.175ms to 16.874ms/10,000 calls; this is not a browser speed claim. Canonical build, prepare and pin checks pass. Final [105626 audit](../../reports/browser/20261011T105626Z/source-audit.json) matches 247 identities. Main Wasm `8db3a988…` and compatibility `d9cf8048…` are unchanged; patch is `c88abb6d3aa26b5391adfa88c01539c5d648ed97ea76b9ef420eac647237b389`. [Acceptance](../acceptance-session.md) supplies full identities and launch commands.

## Integrated result and remaining dependency

**BLOCKED.** [105626](../../reports/browser/20261011T105626Z/review.json) reviews 106 images over 3,537.063 seconds/4,621 presentations. Original login/selection/town, both dungeon entries, basic attacks, Flame Geyser, Roll, Tree's first internal transition and both returns are observed. Native totals are two failed attempts, zero wins and zero stones; saved gains are 807 EXP/12 ED. No current victory or second successful cycle.

Two deaths with different ordinary Z durations still fail revival. Unlike 092157, initialization becomes 1; countdown then stops near ten seconds with disabled policy and no accepted revival. Exact ordering within sample gaps is unresolved. [Diagnosis](../../reports/browser/20261011T105626Z/revival-failure.json) excludes post-teardown reads and separates historical event-201 caller evidence from current observations. CPU profiles end before death; no breakpoints or gameplay writes. Combat remains approximately 1fps.

The unresolved dependency is timely original continue input/update before encounter closure; the exact client operation is not isolated. No event/timer/server bypass. Input/focus and visible effects remain open; prior loading verification is preserved. Updated [matrix](../compatibility.md), [issues](../issues.md), [graphics](../graphics.md), [changelog](../CHANGELOG.md) and [chair briefing](../chair-briefing.md) distinguish earlier wins.

Tools/attribution: existing Node/WATX, Edge/Playwright, Python, native references and read-only server/SQL tools; original game/fork, Wine-Assembly/WATX/platform and prior maintenance contributions remain credited.

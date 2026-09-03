# Motion route

Load this only when animation or interaction behavior is requested or is essential to communicating state.

## Escalation ladder

1. CSS or the framework's native animation for hover, focus, disclosure, and small state changes.
2. The project's existing motion library.
3. `beui` or Fluid Functionalism references for reusable React interaction patterns.
4. GSAP for coordinated timelines, scroll-linked storytelling, SVG morphing, motion paths, or complex sequencing.
5. ThreeUI/WebGL only for an explicitly justified 3D experience.

## Skill routing

- Start with `find-animation-opportunities` when the right places to animate are unclear.
- Use `animate` for a new interaction, `review-animations` for a bounded review, and `improve-animations` for a codebase-wide improvement plan.
- For GSAP, use only the matching Skill: `gsap-core`, `gsap-timeline`, `gsap-scrolltrigger`, `gsap-plugins`, `gsap-utils`, `gsap-react`, `gsap-frameworks`, or `gsap-performance`.

## Quality bar

- Every motion choice must have a purpose and an interruptible end state.
- Avoid scroll hijacking, gratuitous parallax, delayed primary actions, and layout-thrashing properties.
- Provide a reduced-motion path and a usable static fallback.
- Measure load cost, main-thread work, mobile behavior, and route teardown; do not judge only by a desktop recording.
- GSAP runtime uses the [Webflow Standard “No Charge” License](https://gsap.com/community/standard-license/), not MIT. Check the current terms for the intended product; the separate Agent Skills repository is MIT-licensed.

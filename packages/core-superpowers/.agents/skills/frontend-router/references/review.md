# Cross-framework review route

Run framework correctness and accessibility checks before aesthetic review. Use one broad review lens by default, not every review Skill.

## Choose the reviewer

- Use `hallmark` for a broad anti-slop audit, a structurally distinct redesign, or design-DNA study. Prefer `hallmark audit` when the user requested findings without edits.
- Use `design-taste-frontend` for an opinionated web design review, especially landing pages and portfolios. Its current v2 guidance is experimental; do not apply it blindly to dense dashboards, Streamlit widgets, or native SwiftUI.
- Use `21st-ui-review` for React/shadcn implementation fit and `review-animations` for motion-specific issues.
- Use `swiftui-pro` for native SwiftUI correctness; visual taste must not override platform behavior.

## Review order

1. Broken behavior, framework misuse, accessibility, and responsive/device failures.
2. Information architecture and product-type fit.
3. Hierarchy, typography, spacing, density, color, and component consistency.
4. Motion purpose, timing, reduced-motion behavior, and performance.
5. Generic AI patterns, unnecessary decoration, and visual sameness.

Keep audit and implementation distinct. If the user asked only for review, provide evidence-backed findings without modifying the project.

Sources: [Hallmark](https://github.com/Nutlope/hallmark), [Taste Skill](https://github.com/Leonxlnx/taste-skill)

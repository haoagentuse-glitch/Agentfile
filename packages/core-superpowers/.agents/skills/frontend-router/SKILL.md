---
name: frontend-router
description: Route frontend creation, redesign, theming, motion, and UI review by framework and product type. Use when the user wants to build, adopt, modify, or visually improve a frontend in Streamlit, React, Next.js, shadcn/ui, or SwiftUI, especially when they say they want to use Streamlit. Do not use for backend-only work, architecture diagrams, or standalone image generation.
---

# Frontend Router

Choose the smallest useful route. Do not load every reference or invoke every installed Skill.

## 1. Establish the route

Honor an explicitly chosen framework. Otherwise inspect the repository before asking:

- Streamlit: Python imports, `streamlit` dependency, `.streamlit/`, or `streamlit run`.
- React web: React/Next.js/Vite and `package.json`; identify Tailwind or shadcn/ui separately.
- SwiftUI: `SwiftUI` imports, `.xcodeproj`, `.xcworkspace`, or `Package.swift` for an Apple app.
- Unknown: infer from the product type below. Ask one focused question only when the framework choice materially changes the result.

Then classify the page as landing/marketing, SaaS/product, dashboard/data explorer, AI chat/agent, portfolio/creative, or native mobile.

## 2. Load only the matching branch

| Need | Required reference | Add only when needed |
| --- | --- | --- |
| Streamlit | [framework-streamlit.md](references/framework-streamlit.md) | design-system, motion, review |
| React/Next.js/shadcn | [framework-react-web.md](references/framework-react-web.md) | design-system, motion, review |
| SwiftUI | [framework-swiftui.md](references/framework-swiftui.md) | motion, review |
| Theme or brand system | Chosen framework first | [design-system.md](references/design-system.md) |
| Animation or interaction | Chosen framework first | [motion.md](references/motion.md) |
| Audit, redesign, or “remove the AI look” | Chosen framework first | [review.md](references/review.md) |

For dependency status and source provenance, read [dependencies.md](references/dependencies.md). Archify and Mono Color are intentionally out of scope.

## 3. Apply shared constraints

- Preserve the repository's framework, component system, design tokens, and dependency conventions unless the user asks to replace them.
- Prefer native framework capabilities, then an existing project dependency, then an installed Skill or external reference.
- Treat galleries and websites as structural inspiration. Do not copy protected assets, paid templates, or another brand's tokens.
- Keep one source of truth for design tokens.
- Add motion only when it explains state, hierarchy, causality, or spatial continuity.
- Keep accessibility, reduced motion, responsive behavior, loading, empty, error, and focus states in scope.
- If a routed Skill is missing, do not silently fetch or update it. Report the missing dependency and ask before changing the bundled or project installation.

## 4. Verify the result

Run the project's real lint, test, build, preview, or app command in proportion to the change. Inspect the rendered interface when tools permit. Report what was actually run and any unverified visual or device states.

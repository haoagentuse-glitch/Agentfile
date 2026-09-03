# Dependency catalog

These Agent Skills are bundled with this Agentfile profile for routing. Load only the subset required by the selected branch.

Snapshot vendored 2026-09-03: this router plus 32 routed dependencies; all 33 passed Codex's `quick_validate.py`. Exact upstream commits and licenses are recorded in the profile's `docs/THIRD_PARTY_LICENSES.md`.

| Route | Installed Skills | Source |
| --- | --- | --- |
| Streamlit | `developing-with-streamlit`, `streamlit-custom-style` | [Streamlit](https://github.com/streamlit/streamlit), [Paldom](https://github.com/Paldom/streamlit-custom-style) |
| React structure/components | `21st-cli-use`, `21st-ai`, `21st-registry`, `21st-design-sync`, `21st-ui-build`, `21st-ui-explore`, `21st-ui-review`, `beui` | [21st.dev](https://github.com/21st-dev/skill), [beUI](https://github.com/starc007/ui-components) |
| Motion | Emil Kowalski's animation Skills and the eight `gsap-*` Skills | [Emil Skills](https://github.com/emilkowalski/skills), [GSAP Skills](https://github.com/greensock/gsap-skills) |
| SwiftUI | `swiftui-pro`, `write-swift`, `apple-design`, relevant motion Skills | [SwiftUI Pro](https://github.com/twostraws/SwiftUI-Agent-Skill), [Emil Skills](https://github.com/emilkowalski/skills) |
| Mobile research | `appllama-usage` | [Appllama Skills](https://github.com/Appllama/appllama-skills) |
| Cross-framework review | `hallmark`, `design-taste-frontend` | [Hallmark](https://github.com/Nutlope/hallmark), [Taste Skill](https://github.com/Leonxlnx/taste-skill) |

The bundled set is a local snapshot. Never auto-update it during frontend work. If a Skill is missing or an update is needed, report the source and ask before changing the Agentfile source or copied project.

Four upstream frontmatter files needed compatibility-only normalization for Codex: angle-bracket removal in `21st-ai`; unsupported `disable-model-invocation` translated to `agents/openai.yaml` policy for `review-animations` and `pick-ui-library`; Hallmark's top-level version moved under `metadata`. Their instruction bodies were not changed.

The following are runtime libraries or reference sites, not Agent Skills: `streamlit-shadcn-ui`, `st_yled`, GSAP runtime, ThreeUI, HeroUI Pro, Watermelon UI, Fluid Functionalism, tweakcn, and getdesign.md. Recommend or install them only after checking the active project's stack, license, and maintenance tradeoff.

Archify and Mono Color are excluded by design.

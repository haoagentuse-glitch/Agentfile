# Design-system route

Load this only when the task includes theming, branding, visual consistency, design extraction, or token work.

## Authority order

1. Existing project design system and tokens.
2. Framework-native theming: Streamlit theme TOML, CSS custom properties/Tailwind config, or SwiftUI assets and semantic colors.
3. A concise project `DESIGN.md` when a durable human-and-agent contract will reduce repeated decisions.

Do not create a second token source. If `DESIGN.md` exists, link to executable token files instead of duplicating exact values.

## Minimum useful contract

- Semantic colors with light/dark/high-contrast behavior.
- Type roles and a restrained size/weight scale.
- Spacing, radius, border, elevation, and container rules.
- Component and chart-state colors: default, hover, focus, active, disabled, loading, empty, error, and success.
- Motion durations/easings plus a reduced-motion rule.
- A short description of the intended visual character and explicit anti-patterns.

Use [getdesign.md](https://getdesign.md/) only as an extraction aid and verify its output against the source. Do not import another organization's brand or protected assets. Use [tweakcn](https://tweakcn.com/) only for shadcn/Tailwind projects.

Check text and non-text contrast, focus visibility, color-independent meaning, long/localized labels, zoom, and narrow layouts.

# Streamlit route

Use this route whenever Streamlit is explicit or detected. It is optimized for data apps, dashboards, reports, forms, and AI chat tools—not pixel-identical marketing sites.

## Skills

1. Always invoke `developing-with-streamlit`. This is Streamlit's first-party Agent Skill and the implementation authority.
2. Invoke `streamlit-custom-style` only for branding, theme work, custom fonts, sidebar styling, chart palettes, or narrowly scoped CSS.

## Styling order

1. Use `.streamlit/config.toml` or a reusable theme TOML for colors, typography, borders, sidebar variants, dark mode, and native chart palettes.
2. Centralize `st.set_page_config()`, `st.logo()`, and shared setup in one page bootstrap.
3. Prefer native widgets and layouts. Use `layout="wide"` only when the information density calls for it.
4. If theme configuration cannot express a component variant, target user-controlled `.st-key-*` classes with minimal CSS.
5. Avoid hashed DOM classes, broad selectors, and blanket HTML injection. Pin Streamlit and regression-test any CSS escape hatch.
6. Use Components v2 for genuinely custom interface elements.

## Packages to recommend, not Skills to auto-install

- [`streamlit-shadcn-ui`](https://github.com/ObservedObserver/streamlit-shadcn-ui): consider when shadcn-like components materially improve an existing Streamlit app.
- [`st_yled`](https://github.com/LovesWorking/styled): consider when declarative per-element styling is worth another runtime dependency.

Do not add either package until the repository constraints and maintenance tradeoff have been checked.

## Verification

Run the real app and exercise reruns, session state, forms, sidebar navigation, loading/error/empty states, light and dark themes, and the narrowest supported viewport. Prefer `streamlit.testing.v1.AppTest` for stable flows.

Sources: [official Skill](https://github.com/streamlit/streamlit/tree/develop/lib/streamlit/.agents/skills/developing-with-streamlit), [custom-style Skill](https://github.com/Paldom/streamlit-custom-style), [theming docs](https://docs.streamlit.io/develop/concepts/configuration/theming), [Components v2](https://docs.streamlit.io/develop/concepts/custom-components/intro)

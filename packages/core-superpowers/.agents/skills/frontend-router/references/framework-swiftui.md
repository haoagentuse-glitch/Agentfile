# SwiftUI route

Use this route for native Apple interfaces written in SwiftUI.

## Skills

1. Use `swiftui-pro` as the implementation and audit authority for SwiftUI API usage, state, navigation, layout, performance, and accessibility.
2. Use `write-swift` for Swift language, concurrency, performance, or Swift Testing decisions.
3. Use `apple-design` for Apple-style interaction and motion principles.
4. Add `animate`, `find-animation-opportunities`, `review-animations`, or `improve-animations` only when motion is in scope.
5. Use `appllama-usage` only when category or competitor research is needed and the Appllama connector is available. It may require a paid account and consumes credits.

`appllama-app-design-skill` targets Expo/React Native, so do not route SwiftUI implementation through it.

## Constraints

- Inspect the project's deployment target, Xcode/Swift version, navigation architecture, state model, and design system before following modern-API advice.
- Project constraints override a Skill's assumed iOS or Swift version.
- Prefer semantic colors, Dynamic Type, native controls, appropriate presentation styles, and platform navigation behavior.
- Respect Reduce Motion, VoiceOver, localization, safe areas, and content-size extremes.

## Verification

Build the actual scheme. Run relevant tests and previews, then verify on a simulator or device when available. Check VoiceOver labels/order, Dynamic Type, light/dark appearance, Reduce Motion, navigation back behavior, and performance hotspots.

Sources: [SwiftUI Pro](https://github.com/twostraws/SwiftUI-Agent-Skill), [Emil Kowalski Skills](https://github.com/emilkowalski/skills), [Appllama Skills](https://github.com/Appllama/appllama-skills)

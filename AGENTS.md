## Frontend Design

Before modifying frontend UI:

1. Read `docs/DESIGN.md`.
2. Follow the existing design system.
3. Do not introduce a new visual style unless explicitly requested.
4. Reuse existing components and design tokens.
5. Avoid generic AI-generated UI patterns.
6. Preserve visual consistency across pages.



## Coding Rules
- 优先修改现有实现，不重复创建功能相同的组件。
- 不为了小改动引入新的第三方依赖。
- 保持现有 API 命名和目录结构。
- 新增公共函数必须有类型标注。
- 不使用 `any` 规避 TypeScript 类型错误
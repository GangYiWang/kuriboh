# UI Design System

## Overall Style

Professional web application.

Keywords:

- clean
- restrained
- information-focused
- desktop-first
- modern but not futuristic

Avoid:

- AI-generated landing page aesthetics
- excessive gradients
- glassmorphism
- excessive cards
- excessive rounded corners
- oversized headings
- unnecessary illustrations
- decorative icons

## Layout

Desktop max width: 1280px
Page horizontal padding: 24px
Section spacing: 32px
Component spacing: 16px

## Radius

Small: 4px
Default: 6px
Large: 8px

Avoid radius > 12px unless necessary.

## Visual hierarchy

Prefer:

1. typography
2. whitespace
3. border
4. background contrast

Do NOT rely on shadows for hierarchy.

## Cards

Do not wrap every section in a card.

Cards should only be used when the content represents
an independent semantic unit.

## Buttons

Primary actions should be visually obvious.
Secondary actions should be restrained.

Avoid pill buttons unless appropriate.

## Tables

Tables should feel compact and data-oriented.

Avoid large row heights.
Avoid excessive borders.
Use subtle hover states.

## Match Rows

- When the available page width is sufficient, player nicknames must be displayed in full. Do not truncate them merely to preserve unused whitespace elsewhere in the row.
- Lay out head-to-head players as three symmetric columns: `player A | VS | player B`. The two player columns must have equal width, and `VS` must stay at their geometric center regardless of nickname length or winner/seed labels.
- Keep player A right-aligned and player B left-aligned so both names visually anchor to `VS`.
- At narrow breakpoints, prefer wrapping player content while preserving the centered `VS`; do not silently introduce nickname ellipsis.

## Administrative Result Resolution

- Swiss and playoff administration must use the same winner-first interaction. Expose one row action (`处理未提交`, `处理冲突`, or `纠正赛果`), then let the administrator select the winning player in an inline form.
- Always summarize the complete outcome as `winner 胜 / loser 负` before confirmation. Do not mix winner-selection controls in one stage with loser-selection controls in another.
- The resolution reason is optional for unsubmitted matches, conflicts, and corrections. Keep the field available for audit context, but do not block confirmation when it is blank unless later product feedback explicitly changes this rule.
- Keep the inline editor compact instead of stretching it across the full match row. Show winner choices and confirmation actions together, and keep the optional reason collapsed behind an explicit toggle until the administrator requests it.

## Administrative Confirmations

- Use the shared in-page confirmation dialog when publishing Swiss rounds. Playoff pairings are fixed by seed and must be generated and published atomically without a preview or separate confirmation step.
- Keep the action title, consequence description, cancel action, and primary confirmation action consistent across competition stages.
- Ending a tournament is an explicit exception: `结束赛事并锁定结果` executes immediately without a confirmation dialog or cancel step. Keep the button disabled while the request is in progress and surface API success or failure in the page.

## Player Match Lists

- On player-facing match pages, use one reverse-chronological match list under the existing page title. Do not split the same data into separate `current match` and `match history` sections.
- Keep unfinished matches in the same list and place their submission state and result actions inside the corresponding match card. When the match completes, the card stays in place and changes to the confirmed outcome.
- Sort elimination matches before Swiss matches, then by round descending. A newly published round therefore appears at the top without special empty-state branches for non-qualified, eliminated, or finished players.

## Tournament Results

- Player-facing and administrator-facing results pages use the same `Swiss | Playoff` stage navigation and the same shared playoff Bracket tree.
- The player-facing results tab uses the full content width. Do not reserve a registration sidebar beside rankings or the Bracket tree.
- Player deck uploads live in a dedicated top-level `卡组` tab immediately after `赛果`, not inside either results stage. Show this tab after the tournament ends for authenticated users, use the full content width, and explain clearly when the current player is not eligible to upload.

## Administrative Deck Review

- Returning a deck screenshot for re-upload does not require a reason. The client sends an empty `reason` string and the API accepts and records it without blocking the action.
- For pending screenshots, place `预览` immediately before `审核通过`. Open the existing image at its natural readable size in an in-page modal, with a visible close action and Escape-key support; previewing must not change review state.
- Use final-stage titles consistently across player upload, administrator review, and weekly reports: placement `1` is `冠军`, placement `2` is `亚军`, and placements `3` and `4` are both `四强`. Numeric placement may remain internal for stable ordering, but the UI must not distinguish third from fourth place.

## Weekly Reports

- After all four deck screenshots are approved, the administrator uses one `生成周报` action that generates and publishes the immutable report atomically. Do not expose a draft preview, a separate publish action, or administrator editing controls.
- A weekly report contains only the tournament summary and the four finalist deck cards. Do not render Swiss standings or playoff match results in the report; those remain available in the tournament results module.
- Deck cards emphasize only `冠军`, `亚军`, and `四强`. Do not display numeric placements `1`, `2`, `3`, or `4`, and do not distinguish the two semifinalists.

## Audit Logs

- Keep audit action codes in English in storage and API responses, but translate the primary action title into Chinese in every administrator-facing audit list.
- Reuse one shared action-label mapping for tournament and platform audit pages. Unknown future action codes must display the Chinese fallback `其他系统操作` instead of exposing raw English as the title.

## Production Home Page

- Keep the public home page focused on the product value and navigation. Do not expose development-stage labels, version markers such as `V1`, backend connection status, implementation notes, or third-party product branding in promotional headings.

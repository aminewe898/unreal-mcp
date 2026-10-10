# Project instructions

Use Context7 to fetch current documentation for libraries, frameworks, SDKs,
APIs and CLI tools. Resolve the library ID first, then query the relevant
concept. Prefer installed Unreal headers and implementation when verifying
the actual engine build. General business logic and mechanical refactoring
do not require documentation lookup.

The user requests routine work be delegated to Gemini 3.8 through `agy`.
Use `gemini-3.8-flash-medium` for simple coding and
`gemini-3.8-flash-low` for mechanical edits/documentation, with
`--mode accept-edits --print`. Verify available models before changing them.
Give each job explicit file ownership and acceptance criteria. Do not grant
unrestricted permission bypasses. Do not have concurrent agents modify the
same files. Review all generated changes and run relevant checks yourself.
The lead engineer handles architecture, Unreal API investigation, C++
integration, safety decisions and live debugging.

Use the isolated AmineMCPHost for acceptance tests. Never change engine
source or test in an unrelated user's dirty editor. Write assets only under
/Game, save only explicit targets and delete only exact, validated objects.
Report live validation separately from static tests and compilation.

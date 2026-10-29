# Chat and check-ins — 0.1.0-preview.2

Juno remains a native Mac application. PostgreSQL owns her records and application code owns permissions, state transitions, revision checks and the interview. A configurable local model supplies conversational answers; a separate dedicated reasoning model is not required to begin.

## Connect LM Studio

1. Start LM Studio's local server on the same Mac as Juno.
2. In Juno, select **Model connection** and use `http://127.0.0.1:1234/v1` (or the local port you configured).
3. Select **Find models**, choose a chat model, and **Save connection**.
4. Open **Chat**. Send with the button or Command-Return.

The connection uses LM Studio's local compatibility API. Official server setup: https://lmstudio.ai/docs/developer/core/server . No model weights are included in the installer. The laptop needs its own local model server; this preview does not connect through the desktop or silently fall back to a cloud service. Authentication-required model servers and remote endpoints are not supported yet.

The desktop's standard `qwen3.6-35b-a3b` answered a fictional memory question successfully. This establishes a working connection, not that the same model fits the laptop's memory or that all planning judgments are correct.

## Persistent chat

Conversations and messages persist across quits/restarts. The context includes a bounded recent history, up to five canonical memories selected using simple keyword overlap/recency, and up to three confirmed diary entries. Embedding/semantic retrieval is not implemented yet. Replies record the selected model and meeting mode.

Memory and diary revisions are checked again before publishing a reply. If a source changes during generation, the reply is withheld and can be retried. Correcting or deleting a memory, or editing a referenced diary, redacts derived assistant replies from stored history and excludes those replies from future prompts. This is conservative: a reply can be invalidated even if it did not explicitly quote the changed source. Raw user messages and original check-in answers remain separate source records; deleting a memory does not delete those originals.

Retries use a persisted request ID to avoid duplicate user messages after an uncertain connection result. Interrupted pending replies become retryable when the app restarts. Model failures remain visible and never become invented answers. The service does not execute model tool calls or send external messages.

Meeting mode requests a professional tone. Private-mode assistant replies are hidden while meeting mode is enabled, including replies that arrive after a mode change. This is not a general-purpose screen privacy filter: user messages and other work remain visible.

## Daily check-in and diary

The guided interview works without a model. It asks one question at a time about accomplishments, interruptions, blockers, employee contributions and tomorrow. It saves answers as you continue and resumes at the first unanswered question. A skip is recorded as missing information, never as evidence that nothing happened.

After the questions, review/edit the structured diary draft. Save it as a draft or confirm it. Only confirmed diaries are supplied to chat context. Existing entries can be opened by date and their diary text corrected. Sources are not connected yet, so the interface explicitly says these entries are based on your answers, not automatic observation.

Unsent chat and check-in drafts are stored locally in macOS preferences; they are not credentials and are not synchronized between Macs. Conversation history and saved answers live in PostgreSQL. Keep using fictional information while data-handling approvals remain unresolved.

## Upgrade and current limits

Preview 2 retains the same installed bundle identity and data folder as preview 1. Before changing an existing schema, the local helper creates a private PostgreSQL dump and checks that its table of contents is readable. A migration/backup failure stops startup rather than resetting the database. Backups remain local in `~/Library/Application Support/Juno/backups`; no automatic expiry or restore UI is implemented yet.

This is still a local internal preview: no live TaskDock/Calendar reads, time planning, shared-service deployment, cross-device synchronization, scheduled reminders or automatic missed-day entries. The app is ad hoc signed and the package is unsigned/not notarized. Actual M5 laptop installation remains pending. HumanLab's browser instrument still cannot exercise the native SwiftUI interface.

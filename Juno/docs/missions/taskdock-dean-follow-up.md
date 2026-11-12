# TaskDock mission — create reviewed Dean follow-ups from Juno

Juno reviews meeting notes and saves the requests the user confirms. TaskDock owns task creation and lifecycle. Give Juno a way to create the confirmed requests as native cards in **Weekly Meetings with the Dean**.

- Add an opt-in local write capability with a dedicated grant limited to native task creation in one configured workspace and status column. Keep the existing Juno read credential read-only. Require stable IDs for workspace and status, and deny a missing or changed target.
- Accept a reviewed action title, optional notes and due date, and a stable request ID per card. Create cards using TaskDock’s normal validation and history. Retrying the same ID and payload returns the existing card. Reusing the ID with different data returns a conflict. Return the saved task ID and status so Juno can link the request and refresh its copy.
- Use Juno’s review screen to show the target and selected cards before submitting. Send the approved card fields. Keep meeting notes and supporting quotes in Juno unless the user includes them in the card.
- Verify a revoked grant, wrong workspace or column, duplicate retry, and an interrupted batch. Existing cards remain readable through Juno’s current integration. No upstream source write is needed.

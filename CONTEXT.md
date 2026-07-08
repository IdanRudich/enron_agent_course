# Context

## Glossary

### Challenge Question
A graded task given to a student agent. Each challenge question has a correct answer, a point value, and one or more accepted evidence Message-IDs.

### Student Agent Submission
The answer returned by a student's agent for a challenge question. A valid submission includes the final answer and the Message-ID evidence used to support it.

### Golden Answer
The official student-visible answer for a challenge question. It includes the accepted answer value, accepted evidence Message-IDs, and the points awarded for a correct submission.

### Evidence Message-ID
An email Message-ID that supports a golden answer or student submission.

### Fixed Challenge Points
The 1-10 point value assigned to a challenge question. The value is fixed per question rather than calculated from partial-credit components.

### Point Band
The score range associated with a difficulty level: Easy uses 1-3 points, Medium uses 4-7 points, and Hard uses 8-10 points.

### Evidence-Gated Correctness
A grading rule where a student submission must include accepted Message-ID evidence to receive the challenge question's points.

### Easy Challenge
A challenge question whose answer can be verified from one known Message-ID.

### Exact Email Lookup Challenge
An easy challenge where the prompt gives a Message-ID and the student agent must retrieve an atomic fact from that email.

### Message-ID Discovery Challenge
An easy challenge where the prompt gives exact clues about one email and the student agent must return that email's Message-ID.

### Header Field Extraction Challenge
An easy challenge where the student agent must extract a sender, recipient, cc, bcc, subject, or date from one email.

### Attachment Mention Challenge
An easy challenge where the student agent must identify whether an email mentions an attachment or name the attachment mentioned.

### Latest-Vs-Quoted Sender Challenge
An easy challenge where the student agent must distinguish the current email's author from senders in quoted email history.

### Date Normalization Challenge
An easy challenge where the student agent must convert an email date into the requested standard answer format.

### Recipient Role Challenge
An easy challenge where the student agent must distinguish between To, Cc, and Bcc recipients.

### Body Fact Extraction Challenge
An easy challenge where the student agent must extract one explicit fact from the body of a single email.

### Medium Challenge
A challenge question whose answer requires a bounded wide search across emails, usually constrained by a person, topic, date range, or mailbox.

### Bounded Work Summary Challenge
A medium challenge where the student agent must identify what a person worked on within explicit bounds such as dates, mailbox, or topic.

### Search Aggregate Challenge
A medium challenge where the student agent must compute a deterministic count or grouped count from a bounded set of emails.

### Earliest-Latest Challenge
A medium challenge where the student agent must find the earliest or latest email matching explicit criteria.

### Participant List Challenge
A medium challenge where the student agent must return the people involved in a bounded topic, thread, or time window.

### Topic Participation Challenge
A medium challenge where the student agent must determine whether or how a person participated in a bounded topic.

### Hard Challenge
A deterministic challenge question whose answer requires synthesizing evidence from multiple emails, either across a broad set of messages or through a connected email thread.

### Thread Reconstruction Challenge
A hard challenge where the student agent must follow a connected email chain and reconstruct the ordered sequence or final outcome.

### Cross-Mailbox Corroboration Challenge
A hard challenge where the student agent must combine evidence from multiple mailboxes to support one answer.

### Timeline Synthesis Challenge
A hard challenge where the student agent must combine multiple emails into a deterministic sequence of events.

### Contradiction-Resolution Challenge
A hard challenge where the student agent must compare emails that appear to conflict and identify the resolved answer supported by later or stronger evidence.

### Negative Evidence Challenge
A challenge where the student agent must show that no email matching explicit criteria exists within a bounded scope.

### Forwarded-Copy Challenge
A challenge where the student agent must distinguish the current email from quoted, forwarded, or near-duplicate copies of related content.

### Entity Disambiguation Challenge
A challenge where the student agent must distinguish between similarly named people, aliases, email addresses, or organizational identities.

### Mailbox Hygiene Challenge
A challenge where the student agent must handle mailbox structure correctly, including folders, sent mail, deleted items, repeated folder copies, and duplicate-looking messages.

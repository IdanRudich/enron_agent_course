# Golden Set Count/Aggregate Evidence Expectations

Date: 2026-07-09

## Question

What does the current Golden Set expect for count/aggregate-like questions, especially answer values and Evidence Message-IDs?

## Primary Sources Used

- Golden challenge records: `student_dataset/golden_set/golden_set.json`
- Value normalization rules: `student_dataset/NORMALIZATION.md`
- Dataset/evidence contract: `student_dataset/DATASET_CONTRACT.md`
- Student-facing grading summary: `student_dataset/README.md`
- Validator and reports: `student_dataset/validation/validate_dataset.py`, `student_dataset/validation/validation_report.md`, `student_dataset/validation/_validation_result.json`
- Packaged mail used for spot checks: `student_dataset/mail/packs/`

## Short Answer

The count/aggregate-like surface is concentrated in all 10 Medium challenges. Eight are deterministic structured aggregates: four numeric counts (`medium-001`, `medium-002`, `medium-009`, `medium-010`), two date extrema (`medium-003`, `medium-004`), and two distinct-set tasks (`medium-005`, `medium-006`). Two more are bounded pack summaries/frequency judgments (`medium-007`, `medium-008`), where the answer is textual but the prompt asks the agent to infer from a pack-level pattern.

For the deterministic extrema tasks, the expected Evidence Message-ID is the actual extremal row and remains fixed with `evidence_mode: "all"`. The broader count, distinct, sender, participant, frequency, and bounded-summary Medium tasks now use `evidence_mode: "predicate"`: the listed `evidence_message_ids` remain curated examples/anchors, while `golden_answer.evidence_predicate` defines the broader accepted evidence rule.

This resolves the earlier mismatch where several Medium `grading_notes` said "any in-scope" evidence was acceptable but the JSON only listed one or two accepted IDs. Predicate mode accepts at least one submitted Message-ID satisfying the structured predicate and ignores extra non-matching evidence for evidence scoring.

## Evidence Rules That Govern These Tasks

`student_dataset/DATASET_CONTRACT.md` says `evidence_mode: "all"` means every listed id is required, `evidence_mode: "any"` means any one listed id suffices, and `evidence_mode: "predicate"` means at least one submitted id must satisfy `golden_answer.evidence_predicate`. It also says a correct answer without accepted evidence scores zero. `student_dataset/README.md` repeats this student-facing rule. These claims apply to every challenge below because each record sets `requires_evidence_message_ids: true` in `student_dataset/golden_set/golden_set.json`.

`student_dataset/NORMALIZATION.md` says aggregate/count scopes must be explicit and limited to the named mailbox, folder, pack, or union. That matches the Medium prompts in `student_dataset/golden_set/golden_set.json`: every aggregate-like prompt names a single Medium pack.

`student_dataset/validation/validate_dataset.py` validates that listed Evidence Message-IDs resolve inside the prompt-bounded raw mail. For predicate-mode records, it also validates the predicate object shape and confirms the curated example IDs satisfy their own predicates. It still does not validate aggregate answer values.

## Challenge Inventory

### `medium-001`

Source: `student_dataset/golden_set/golden_set.json` (`medium-001`); packaged mail spot check under `student_dataset/mail/packs/symes-k__power_marketer/`.

Prompt: "Count the total number of email messages packaged in the Medium pack 'symes-k__power_marketer' (Kate Symes's power_marketer folder). Count every packaged message file in that pack exactly once, including replies/forwards and any near-duplicates. Report a single integer."

- Expected answer: `136`; aliases: `"136 emails"`.
- Expected evidence_message_ids: `<28841806.1075841866914.JavaMail.evans@thyme>`, `<266694.1075841873502.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: count every packaged file in the pack once; replies/forwards and near-duplicates are included; the two listed IDs are earliest/latest pack messages.
- Evidence kind: boundary/anchor examples, not the counted set.
- Natural SQLite findability: answer is naturally findable with `COUNT(*) WHERE pack='symes-k__power_marketer'`. The listed evidence is findable if the tool also returns first/last pack rows, but a plain count query would not naturally produce those IDs.

### `medium-002`

Source: `student_dataset/golden_set/golden_set.json` (`medium-002`); packaged mail spot check under `student_dataset/mail/packs/steffes-j__credit_issues/`.

Prompt: "Within the Medium pack 'steffes-j__credit_issues' (James Steffes's credit_issues folder), count how many packaged emails are replies or forwards, defined as messages whose Subject line begins (case-insensitively) with 'Re:', 'Fw:', or 'Fwd:'. Count each such message once across the whole pack. Report a single integer."

- Expected answer: `51`; aliases: `"51 emails"`, `"51 replies/forwards"`.
- Expected evidence_message_ids: `<303482.1075855211200.JavaMail.evans@thyme>`, `<30933191.1075855211314.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: count top-level Subject values with trimmed case-insensitive prefixes `re:`, `fw:`, or `fwd:` across the pack; answer must be 51.
- Evidence kind: representative counted examples, not the full counted set.
- Natural SQLite findability: answer is naturally findable with a subject-prefix count. A deterministic tool could return many qualifying IDs; it would not reliably cite one of the two listed IDs unless it returned canonical examples or the grader accepted any qualifying reply/forward ID as the notes imply.

### `medium-003`

Source: `student_dataset/golden_set/golden_set.json` (`medium-003`); packaged mail spot check under `student_dataset/mail/packs/kean-s__ferc/`.

Prompt: "Look only inside the Medium pack 'kean-s__ferc' (Steven Kean's ferc folder). Find the earliest email in that pack by its top-level Date header. Report that email's date (ISO 8601) and cite its Message-ID as evidence."

- Expected answer: `2000-03-15T07:37:00-08:00`; aliases: `"2000-03-15"`, `"2000-03-15T15:37:00Z"`, `"March 15, 2000"`.
- Expected evidence_message_ids: `<26816706.1075846346223.JavaMail.evans@thyme>`.
- evidence_mode: `all`.
- Grading notes summary: sort all pack messages by top-level Date ascending; this Message-ID is the earliest email.
- Evidence kind: actual extremal row.
- Natural SQLite findability: yes. A deterministic `ORDER BY date_iso ASC LIMIT 1` query naturally returns both answer and evidence.

### `medium-004`

Source: `student_dataset/golden_set/golden_set.json` (`medium-004`); packaged mail spot check under `student_dataset/mail/packs/symes-k__scheduling/`.

Prompt: "Look only inside the Medium pack 'symes-k__scheduling' (Kate Symes's scheduling folder). Find the latest (most recent) email in that pack by its top-level Date header. Report that email's date (ISO 8601) and cite its Message-ID as evidence."

- Expected answer: `2001-05-01T07:45:00-07:00`; aliases: `"2001-05-01"`, `"2001-05-01T14:45:00Z"`, `"May 1, 2001"`.
- Expected evidence_message_ids: `<6822417.1075841878775.JavaMail.evans@thyme>`.
- evidence_mode: `all`.
- Grading notes summary: sort all pack messages by top-level Date descending; this Message-ID is the latest email.
- Evidence kind: actual extremal row.
- Natural SQLite findability: yes. A deterministic `ORDER BY date_iso DESC LIMIT 1` query naturally returns both answer and evidence.

### `medium-005`

Source: `student_dataset/golden_set/golden_set.json` (`medium-005`); packaged mail spot check under `student_dataset/mail/packs/williams-w3__rt_strat/`.

Prompt: "List every distinct person who participated in the Medium pack 'williams-w3__rt_strat' (Bill Williams III's rt_strat folder, West real-time trading strategy). A participant is any address that appears in the top-level From, To, or Cc header of any packaged email in the pack. Return the complete set of participant email addresses (lowercased)."

- Expected answer: 19-address set: `bill.iii@enron.com`, `chris.mallory@enron.com`, `chris.stokley@enron.com`, `david.porter@enron.com`, `david.poston@enron.com`, `geir.solberg@enron.com`, `holden.salisbury@enron.com`, `jeff.richter@enron.com`, `jeremy.morris@enron.com`, `jesse.bryson@enron.com`, `kourtney.nelson@enron.com`, `lester.rawson@enron.com`, `michael.tully@enron.com`, `phillip.platter@enron.com`, `portland.desk@enron.com`, `portland.shift@enron.com`, `ryan.slinger@enron.com`, `shift.portland@enron.com`, `volume_management_portland@enron.com`; aliases: none.
- Expected evidence_message_ids: `<16022517.1075839947691.JavaMail.evans@thyme>`, `<9883409.1075839947656.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: compute the union of top-level From, To, and Cc addresses across all 18 pack messages; compare as an exact set.
- Evidence kind: arbitrary/representative in-scope pack anchors, not per-address proof and not the full contributing set.
- Natural SQLite findability: the answer is naturally findable with `DISTINCT` over normalized header address roles. The listed evidence is not a deterministic consequence of that aggregate; a tool could cite a different in-scope message that contributed to the union.

### `medium-006`

Source: `student_dataset/golden_set/golden_set.json` (`medium-006`); packaged mail spot check under `student_dataset/mail/packs/symes-k__scheduling/`.

Prompt: "List every distinct sender (top-level From address) across all packaged emails in the Medium pack 'symes-k__scheduling' (Kate Symes's scheduling folder). Return the complete set of sender email addresses (lowercased)."

- Expected answer: 6-address set: `bill.iii@enron.com`, `cara.semperger@enron.com`, `kourtney.nelson@enron.com`, `kroum.kroumov@enron.com`, `lester.rawson@enron.com`, `phillip.platter@enron.com`; aliases: none.
- Expected evidence_message_ids: `<14054298.1075841877964.JavaMail.evans@thyme>`, `<30484554.1075841878060.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: compute distinct top-level From addresses across the pack; compare as an exact case-insensitive set.
- Evidence kind: representative messages from two high-volume senders, not per-sender proof and not the full contributing set.
- Natural SQLite findability: the answer is naturally findable with `SELECT DISTINCT from_addr ...`. The listed evidence is not naturally guaranteed unless the tool returns chosen representative sender rows.

### `medium-007`

Source: `student_dataset/golden_set/golden_set.json` (`medium-007`); packaged mail spot check under `student_dataset/mail/packs/symes-k__power_marketer/`.

Prompt: "Skim the Medium pack 'symes-k__power_marketer' (Kate Symes's power_marketer folder), which is made up of external market-news emails. Name the single recurring daily publication that dominates this folder (the report title that appears in the large majority of the messages)."

- Expected answer: `"PowerMarketers.com Daily Power Report"`; aliases: `"Daily Power Report"`, `"PowerMarketers.com daily power report"`, `"PowerMarketers Daily Power Report"`.
- Expected evidence_message_ids: `<28841806.1075841866914.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: identify the dominant recurring publication; notes say the title heads 99 of 136 packaged emails.
- Evidence kind: representative Daily Power Report example, not the full counted majority.
- Natural SQLite findability: mostly yes if the tool can group or count subject/title prefixes and return an exemplar. If a tool returns a different Daily Power Report example, that is natural but not represented in the current JSON evidence list.
- Spot-check note: a case-sensitive prefix count for `PowerMarketers.com Daily Power Report` found 98 messages, while a case-insensitive `daily power report` subject count found 99 because one subject uses `Powermarketers.com`. The answer remains unambiguous, but the grading note should clarify that the 99 count is case-insensitive.

### `medium-008`

Source: `student_dataset/golden_set/golden_set.json` (`medium-008`); packaged mail spot check under `student_dataset/mail/packs/symes-k__confirms/`.

Prompt: "Based only on the Medium pack 'symes-k__confirms' (Kate Symes's confirms folder), summarize in a short phrase what kind of documents/work this folder is about. Answer with the specific type of business document being handled."

- Expected answer: `"power trade confirmations"`; aliases: `"trade confirmations"`, `"confirmations"`, `"power trade confirms"`, `"confirming power trades"`, `"trade confirms"`.
- Expected evidence_message_ids: `<2377120.1075841710011.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: identify the pack as power trade confirmation correspondence; free-form wording is accepted if it clearly names trade confirmations.
- Evidence kind: representative confirmation message.
- Natural SQLite findability: the summary requires semantic inspection more than deterministic aggregation. A SQLite agent could group subjects/body terms and cite a representative confirmation message, but it may not pick the one listed in JSON.

### `medium-009`

Source: `student_dataset/golden_set/golden_set.json` (`medium-009`); packaged mail spot check under `student_dataset/mail/packs/kean-s__enrononline/`.

Prompt: "Within the Medium pack 'kean-s__enrononline' (Steven Kean's enrononline folder about the EnronOnline trading platform), determine how Leonardo Pacheco (leonardo.pacheco@enron.com) participated: count how many emails in the pack he SENT (was the top-level From). Report a single integer."

- Expected answer: `24`; aliases: `"24 emails"`, `"sent 24"`.
- Expected evidence_message_ids: `<30869027.1075846339788.JavaMail.evans@thyme>`, `<5156685.1075846339760.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: count pack messages whose top-level From is `leonardo.pacheco@enron.com`; answer must be 24.
- Evidence kind: representative counted examples sent by the named person.
- Natural SQLite findability: answer is naturally findable with a structured `from_addr` count. Evidence is naturally findable if the count tool returns sample matching rows; otherwise an agent could cite a different Pacheco-sent message.

### `medium-010`

Source: `student_dataset/golden_set/golden_set.json` (`medium-010`); packaged mail spot check under `student_dataset/mail/packs/dasovich-j__pg_e_hydro_sale/`.

Prompt: "Within the Medium pack 'dasovich-j__pg_e_hydro_sale' (Jeff Dasovich's pg_e_hydro_sale folder about the proposed sale of PG&E hydro assets), determine how Mona Petrochko (mona.petrochko@enron.com) participated: count how many emails in the pack she SENT (was the top-level From). Report a single integer."

- Expected answer: `8`; aliases: `"8 emails"`, `"sent 8"`.
- Expected evidence_message_ids: `<22175853.1075843183671.JavaMail.evans@thyme>`, `<14534080.1075843183503.JavaMail.evans@thyme>`.
- evidence_mode: `predicate`.
- Grading notes summary: count pack messages whose top-level From is `mona.petrochko@enron.com`; answer must be 8.
- Evidence kind: representative counted examples sent by the named person.
- Natural SQLite findability: answer is naturally findable with a structured `from_addr` count. Evidence is naturally findable if the count tool returns sample matching rows; otherwise an agent could cite a different Petrochko-sent message.

## Fairness And Findability Concerns

1. Predicate evidence now covers the Medium records whose grading notes accept any in-scope or qualifying evidence. `medium-001`, `medium-002`, `medium-005`, `medium-006`, `medium-007`, `medium-008`, `medium-009`, and `medium-010` use structured `evidence_predicate` rules, so a strict JSON grader no longer has to treat the curated examples as an exhaustive evidence list.

2. Count and distinct tasks often do not have a single natural evidence row. `medium-001`, `medium-002`, `medium-005`, `medium-006`, `medium-009`, and `medium-010` can be answered deterministically from aggregate SQL, but their listed evidence is representative or anchoring. Without reading `golden_answer`, an agent is more likely to cite rows returned by its own query than the curated examples.

3. Participant-list evidence is especially weak as proof. `medium-005` has a 19-address union over 18 messages but accepts one of two arbitrary pack anchors; `medium-006` has a 6-sender set but accepts one of two high-volume-sender examples. These IDs do not prove completeness of the distinct set.

4. `medium-007` has a minor documentation precision issue. The current pack supports the dominant Daily Power Report answer, but the stated "99 of 136" count is case-insensitive over the title; an exact case-sensitive subject prefix count is 98 because one message uses `Powermarketers.com`.

## Recommended Design/Docs Changes

1. Implemented: aggregate evidence is predicate-based where curated fixed lists were too narrow. The schema now uses explicit predicate types such as `message_in_pack`, `subject_prefix`, `from_address`, and `address_in_headers`.

2. For deterministic aggregate tools, return proof anchors with the aggregate result. Examples: `count`, `sample_message_ids`, `first_message_id`, `last_message_id`, and `matching_message_id_sample`. This lets a SQLite-based agent cite evidence without seeing `golden_answer`.

3. For distinct participant tasks, consider accepting either all contributing Message-IDs or a machine-checkable aggregate proof instead of one arbitrary anchor. At minimum, document that the evidence is only an anchor and not a proof of completeness.

4. Clarify `medium-007`'s 99-count wording as case-insensitive title counting, or avoid publishing the internal count in the note if it is not part of the graded answer.

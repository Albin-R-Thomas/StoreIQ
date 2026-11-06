# Store IQ: TV associate WhatsApp and website flows

## What we are building

One WhatsApp number that helps an associate sell the right TV for the customer's home. The associate talks to the customer. Store IQ gives the next useful question or line to say.

The store visits showed three gaps: too few questions about the home, price coming too early, and weak follow-up. These flows address those gaps.

**Main journey:** Shift brief → Understand the home → Clear doubts → Explain features → Pick 3 TVs → Show the difference → Full cost → Offer and payment → Delivery and installation → Follow-up → Review.

This is a proposed conversation plan, not a description of features already built.

## WhatsApp and website work together

- WhatsApp handles quick questions, voice notes, photos and short replies. The website handles stock browsing, detailed comparisons, PDF summaries and history.
- The website also has a chat with text, voice, photo and the same customer actions as WhatsApp. Customer flows work in either place; practice runs in a separate website training section.
- Both use the same customer records, messages, current step, selected TVs and tasks. Starting on WhatsApp and continuing on the website resumes the same conversation.
- A website link opens the matching customer and screen after login. Opening a page does not mark a demo, sale or task complete.

### Login and website pages

Enter a WhatsApp number to log in. For the contest, use pre-approved test associate and admin numbers. The number's saved role decides the view; typing an admin number must not grant admin access on its own. Before real use, verify ownership of the number with an OTP.

| Page | What the associate can do | What the admin can do |
|---|---|---|
| Home | See own work summary, active customers, practice and pending tasks. | See all associates' work summaries; filter by associate and date. |
| TV stock | Browse TVs by brand; filter by size, price, availability and features; open full specs. | See the same stock view. |
| Customers | Filter own numbered customer list by Today, Yesterday or a date range; resume a customer. | Use the same date filters plus an associate filter. |
| Training | Practise TV questions; see attempts, accuracy, progress and topics to revisit. | Filter training progress by associate and date. |
| Chat | Run all WhatsApp flows for the selected customer. | Review the selected associate's chat; replies and assignments show who acted. |
| Comparison | Compare up to 3 TVs and see why each fits the customer's home. | Review the same comparison. |
| Summary | Preview the customer summary, generate/download its PDF and prepare sharing. | Review summaries for the selected associate. |
| History | Read own customer conversations, dates, decisions and task updates. | Filter history by associate, customer, date and status. |
| Expert requests | Ask questions, track admin requests and read replies. | Get new-request notifications; assign, answer or route requests. |
| Notifications | See admin replies linked to the matching customer chat. | See incoming requests and associate follow-ups, with unread counts. |

### Customer names, numbers and resuming

- Each associate's WhatsApp number owns a separate customer list. Website login with that number opens the same list.
- Give each new customer a permanent serial number within that associate's list: `1`, `2`, `3`... Never renumber when sorting, filtering or adding customers.
- Use the name when given: `1. Rahul`. For another customer with the same name, use `2. Rahul 2`, then `Rahul 3`. Do not merge customers just because their names match.
- Without a name, use `Customer [timestamp]`, for example `3. Customer 2026-11-01 14:35:20`. The serial number still identifies the record if timestamps match.
- If a voice note mentions an existing name, ask `Resume existing` or `Create new`. If several match, show their serial numbers and last visit details; let the associate choose.
- "Customer list", "My customers" or the website Customers page opens the same list with the date filters below. Example WhatsApp result:

> 1. Rahul - comparing TVs
> 2. Rahul 2 - installation pending
> 3. Customer 2026-11-01 14:35:20 - home questions

- Show up to 3 entries per message. Buttons: `Previous` moves back a page, `Next` moves forward, `New customer` starts a new record. Omit unavailable navigation buttons.
- After showing the list, "Type the customer serial number to continue." Typing `2` opens customer 2's saved messages and next pending step. Numbers inside normal chat remain answers to the current question unless the associate is selecting from a list.
- On the website, click the matching customer row to do the same thing. An admin sees the associate name/number beside the serial number, since different associates can each have a customer 2.
- Resuming a customer shows recent messages and offers `Continue flow` (next pending step), `View history` (full conversation), and `Open summary` (website summary). In website history, `Back to chat` returns to that customer.

### Customer list date filters

**Trigger:** "Customer list", "My customers", or opening Customers on the website.

**WhatsApp:** Ask "Which customers would you like to see?" with these buttons:

| Button | What it does |
|---|---|
| `Today` | List customers with a conversation or visit activity today. |
| `Yesterday` | List customers with a conversation or visit activity yesterday. |
| `Date range` | Ask for start and end dates, for example `01/11/2026 to 05/11/2026`, then show matching customers. |

- Dates use the store's local time (IST for this demo), with both start and end dates included. Match customer conversation/visit activity in the period, not just the date the record was created. Automated reminders alone do not count as a visit.
- A returning customer appears once in the results with their original serial number. Resuming opens their full conversation, including messages outside the filter dates.
- Accept direct requests such as "Customers yesterday" or "Customers from 1 Nov 2026 to 5 Nov 2026". Ask for clarification if the dates are unclear, invalid or the end is before the start.
- Show the chosen dates above the results, newest activity first. Keep the same filter while paging. Type "Change dates" to reopen the filter choices or "All customers" to clear the date filter.
- If there are no matches, say so and show `Today`, `Yesterday`, `Date range` again. Never start a new customer record because a search is empty.
- On the website, use the same three filters with date inputs and `Apply` (load results), `Clear filters` (show all permitted customers). Admins can combine dates with an associate filter. Filtering never changes customer ownership or serial numbers.

## Rules for every flow

- Voice notes and photos first; typing and buttons also work.
- Each bot message: at most 3 lines and 3 buttons. Longer details open in the next message when asked.
- First reply within 5 seconds. If a lookup takes longer: "Checking the latest details."
- Ask one missing question at a time. Remember answers already given.
- Every suggestion has a short reason tied to this customer.
- The associate chooses the starting range and final recommendation. Never judge budget from appearance.
- Use only supplied data for specs, prices, stock, offers, charges and finance. If missing, say "Not confirmed" and offer an expert check.
- All examples below use test customers. Model A/B/C and bracketed values must be filled from test data, not invented.
- During the contest, use only the test WhatsApp number and test data. Customer messages are simulated; never send to a real customer.

## 1. Before the shift

**Trigger:** Associate sends "Start shift". A scheduled brief can be added for associates who have enabled it.

**Bot:**
> Which department are you working in today?
> TV is available for now.

**Button:** `TV` selects the department and opens the TV shift brief.

**Bot after TV selection:**
> TV today: [stock changes]. Offers changed: [verified changes].
> View stock by brand, specifications and features on the website.
> Want a quick practice before serving customers?

| Button | What it does |
|---|---|
| `View stock` | Opens the website's TV stock page. Pick a brand, browse its TVs, filter features and open model details. `Compare selected` opens up to 3 selected TVs side by side. `Back to chat` returns to the shift conversation. |
| `Start practice` | Opens the separate website Training section after login, with this associate's saved progress. |
| `Skip practice today` | Records the skip for today and shows `New customer`, `Customer list`, `View stock`. The associate can type "Practice" later to start it. |

**Website practice loop:** Show a short TV video when available, then one question at a time. Example: "A customer wants a living-room TV. What would you ask first?"

| Answer | Feedback |
|---|---|
| `Viewing distance` | Mark correct and explain why distance helps assess screen size. |
| `Brand choice` | Explain that brand preference helps, but home needs should come first; show the correct answer. |
| `Lowest price` | Explain that price alone does not tell us which TV fits; show the correct answer. |

After each answer, show short feedback and `Next question`. Continue for as long as the associate wants, rotating through home questions, features, doubts, demonstrations, full cost and follow-up. Avoid repeats until the available set is exhausted.

| Website button | What it does |
|---|---|
| `Next question` | Save the answer and feedback, then show another question. |
| `Finish practice` | Save progress and show attempts, accuracy and topics to revisit; an unanswered question is not marked wrong. Available at any time. |
| `Start customer` | Save practice progress and open a new customer in website chat. Use test customers during the contest. |
| `Return to WhatsApp` | Save progress and open the Store IQ WhatsApp conversation. Keep its existing customer context; do not create a customer automatically. |
| `Repeat practice` | Restart the available question set when exhausted; retain previous results. |

Keep practice attempts and results in Training history, separate from customer chats and customer scores. Leaving the page saves progress; reopening Training allows the associate to resume. Typing "Practice" on WhatsApp returns the Training link, not training questions. If all questions are used, offer repeat or finish. If a video or training data is missing, say so and use only available verified content.

## 2. Start a customer conversation

**Trigger:** Associate taps `New customer` or sends a voice note about a new TV customer.

**Associate:** "Customer wants a TV for the living room. Mostly cricket and movies."

**Bot:**
> Living room; cricket and movies. Got it.
> Ask: "How far is your sofa from the TV?"
> Tell me the answer by voice or text.

**Next:** Create a customer record using the naming and numbering rules above. If the voice note includes a name, save it. Otherwise use `Customer [timestamp]`. Save the known details and ask only what is missing. `New customer` saves the current conversation before opening a fresh one; it never deletes the old conversation.

## 3. Understand the home

**Trigger:** Associate shares the customer's answers.

Ask these one at a time, skipping anything already answered:

| What is missing? | Line for the associate to ask |
|---|---|
| Viewing distance | "How far is the sofa from the TV?" |
| Room light | "Does sunlight fall on the screen during the day?" |
| Main use | "Mostly regular channels, sports, movies or gaming?" |
| Seating | "Does everyone sit in front, or also on the sides?" |
| Current problem | "What would you like to improve over your current TV?" |
| Placement | "Will it go on a wall or a table? Any space limit?" |
| Spending comfort | "What range would you like us to stay within?" |

**Bot, once enough is known:**
> Home: [distance], [room light], [seating], [wall/table].
> Use: [main use]. Wants: [improvement]. Range: [stated range/unknown].
> Is this right?

**Buttons:** `Correct` | `Edit` | `Ask customer`

**Next:** Associate confirms the home details before recommendations. If the customer does not know something, record "Unknown" and explain any limit it creates. Do not keep asking it.

## 4. Handle a customer belief or doubt

**Trigger:** Associate sends "Customer says..." at any point.

**Associate:** "Customer says every 4K TV gives the same picture."

**Bot:**
> Say: "4K tells us the resolution. Brightness, contrast and reflections can still differ."
> "Since you watch in daylight, let's compare how these two handle reflections."
> Use the same clip on both TVs.

**Buttons:** `Show comparison` | `Ask an expert`

**Next:** Return to the current step. Confirm the correct part politely; explain the difference without attacking a brand. Use verified specs for any model claim.

## 5. Explain a label in simple words

**Trigger:** Associate sends a TV label photo or model number.

**Bot:**
> Found: [verified model and feature].
> Say: "[What this feature means for this customer's viewing]."
> Show: [one visible difference to check].

**Buttons:** `Compare` | `Explain another` | `Wrong model`

**Example:** If the model data confirms a wide viewing angle: "Your family sits on the sides too. Let's check whether the picture still looks good from those seats."

**If the photo is unclear:** "I can't read the model number. Send a closer photo or type it." Do not guess the model or its features.

## 6. Recommend 3 TVs

**Trigger:** Home details are confirmed and the associate asks for options.

**Bot:**
> A: [model] - [reason it fits the home].
> B: [model] - [useful improvement over A].
> C: [model] - [reason to consider it and main trade-off].

**Buttons:** `Demo A/B` | `Change options` | `Stock details`

**Next:** Associate picks which TVs to show. Rank by home fit and the chosen range, using current stock. If only one or two suitable TVs exist, show those and explain why there are fewer.

**Change options:** Accept "lower range", "other brand", "smaller size" or a new need. Update the home details and recommendations.

## 7. Show the difference

**Trigger:** Associate picks TVs to compare.

**Bot:**
> Show [A] and [B] with the same clip and comparable picture settings.
> For this home, check [reflections / sports motion / side seating / dialogue].
> Ask: "Which looks or sounds better to you?"

**Buttons:** `Demo done` | `Need another demo` | `Demo unavailable`

**Next:** On `Demo done`, ask "Which TV did they prefer, and why?" Save the answer and chosen model. Do not mark a demo complete just because instructions were sent.

**If unavailable:** Explain what could not be shown. Offer another display TV or an expert. Keep the demo marked incomplete.

## 8. Build the full solution and cost

**Trigger:** Customer has a preferred TV.

**Bot:**
> TV: [price]. Delivery: [charge]. Installation: [charge].
> Mount/stand: [charge]. Other required items: [itemised charges].
> Required total: [total]. Optional extras are separate.

**Buttons:** `Optional extras` | `Site check` | `Continue`

**Optional extras:** Show soundbar, protection plan or other items only when relevant. Explain the need, price and coverage separately. Recalculate the total only after the customer chooses them.

**Site check:** Confirm wall/table placement, available space, mount needs, power point, connected devices and access restrictions. Flag site work or charges that need confirmation before giving a final total.

**If a charge is unknown:** Show the known subtotal and "Final total pending [charge]". Offer `Ask an expert` to check approved facts, then `Ask admin` if the charge remains unconfirmed; do not describe the subtotal as all-inclusive.

## 9. Offer and payment

**Trigger:** Home assessment and actual demo are complete; associate asks to close.

**Bot:**
> [Model] fits because [customer's need and demo preference].
> Eligible offer: [offer, conditions and expiry from data].
> Final payable: [itemised total after applicable offer].

**Buttons:** `Pay in full` | `Finance` | `Save for later`

**Finance reply:** "Upfront [amount] + [number] EMIs of [amount] + fees [amount] = total [amount]; interest/APR [value], subject to [eligibility]." Use confirmed terms and disclose any missing terms before proceeding.

**If price is asked early:** Give the verified current price plainly, then ask the next home question. Unlock promotional offers only after assessment and demonstration. Never invent urgency, discounts or "last piece" claims.

**If the demo is incomplete:** Explain that the offer step is pending the demo. Let the associate save the conversation or arrange a demo.

## 10. Customer needs time or stock is unavailable

**Trigger:** Associate says "They will decide later" or the selected TV is unavailable.

**Bot:**
> What is pending: family decision, price, stock or another doubt?
> I can save the selected TV and agreed next step.
> Ask: "May we follow up? If yes, when?"

**Buttons:** `Save follow-up` | `Other TV` | `End visit`

**Next:** Record consent, agreed time, reason and associate owner. For unavailable stock, show only confirmed alternatives or confirmed availability dates. Reconfirm price and offers when the customer returns.

## 11. Delivery and installation handover

**Trigger:** Associate confirms the sale in the test flow.

**Bot:**
> Confirm [TV], [chosen items] and [final total].
> Installation: [wall/table], [site needs], [confirmed slot or pending].
> May we send the customer a summary and updates?

**Buttons:** `Consent given` | `No consent` | `Edit details`

**Next:** With consent, prepare a test customer summary: selected TV, charges, delivery/installation status, site needs and contact owner. Without consent, keep the handover internal.

Create separate delivery and installation tasks, each with an owner, due time and status. A requested slot stays "Pending" until confirmed. The summary is split into short messages when needed.

## 12. Follow through until the TV works

**Trigger:** Delivery/installation update arrives, a task becomes overdue, or the associate reports an issue.

**Bot:**
> [Customer session]: [delivery / installation / working check] is pending.
> Owner: [person/team]. Next action: [action] by [time].
> Update the status.

**Buttons:** `Completed` | `Problem` | `Ask an expert`

**If there is a problem:** Capture the issue, assign an owner and agree the next update time. An unanswered or cancelled installation task stays open for resolution.

**After installation:** Prompt the associate to confirm picture, sound, connected devices and customer satisfaction. Close only after the working check is confirmed; otherwise keep a follow-up task.

## 13. Review the conversation

**Trigger:** Associate ends the visit or completes a follow-up.

**Bot:**
> Visit score: [earned]/[applicable points]; pending steps: [steps].
> Done well: [one action supported by the conversation].
> Next time: [one specific action to improve].

**Buttons:** `See score` | `Add voice note` | `New customer`

**See score:** Validate, Assess, Translate, Demonstrate, Complete, Close and Follow through; each scored 0-2, maximum 14. Proposed scoring: 0 = missed, 1 = partly done, 2 = done with recorded evidence. Mark steps not yet due as pending; show a final score out of 14 once all apply. This is our coaching score, not a claim about the judges' exact rubric.

## 14. Useful actions from any step

| Trigger | Bot action | What happens next |
|---|---|---|
| "Hindi" or "Marathi" | Switch coaching language; keep model names and amounts unchanged. | Continue the same conversation. |
| "Ask an expert" | Accept a typed or spoken question; search approved facts using hybrid retrieval. | Show a grounded answer or "Not enough facts present", then `Resolved`, `Ask admin`, `Ask follow-up`. |
| "Customer left" | Save the current step and any agreed follow-up. | Resume from the saved step when they return. |
| "New customer" during a visit | Save the current visit and open a fresh customer record. | Keep customer sessions separate; show the new serial number. |
| Unclear voice note | Repeat the part understood and ask for the missing part. | Continue after clarification. |
| "Visit note" + voice | Save what was tried, the customer's response and next action. | Attach it to the current visit. |
| Manager opens their view | Show pending tasks, owners, overdue installation issues and coaching gaps. | Manager can assign help and review progress. |

## What comparison and Ask an expert do

### Comparison

`Show comparison` and `Compare` open the website comparison screen for the active customer. If TVs have not been selected, first ask the associate to choose up to 3 from stock. A general doubt can get a short explanation immediately; product claims wait until models are selected.

The screen shows model, brand, size, verified specs/features, stock, current price, what each difference means for this home, and missing information. Highlight the differences that matter for the customer's use. Offers stay locked until assessment and demo are complete.

- `Change TVs`: replace the selected models.
- `Select this TV`: save a preferred option; does not record a sale.
- `Start demo`: return to chat with instructions for a physical comparison.
- `Back to chat`: resume the current conversation without changing its step.

In WhatsApp, also give a short comparison so the associate can continue without opening the website. Reading a comparison is different from showing the actual TV; only the associate's demo confirmation completes that step.

### Ask an expert

The associate can tap `Ask an expert`, type a question or send a voice note. Use the current customer, home details and selected TV as context. If no question is included, ask what they need help with.

**First, check the facts:** Use hybrid retrieval: BM25 keyword search plus semantic/vector search over approved documents. Combine the results and use only passages that support the answer for the relevant model. A search match alone is not proof.

- Ground every factual claim in the retrieved sources. Show a short source reference in chat; the website can show the supporting passage and document details.
- If the answer is missing, unsupported or sources conflict, say exactly: **"Not enough facts present."** State briefly what could not be confirmed. Do not guess or fill gaps from general knowledge.
- If only part is supported, answer that part with its source and use the same fallback for the rest.
- Prices, stock, offers, charges and finance come from the approved structured data. RAG can explain approved manuals, features and procedures, but cannot invent or override those values. Missing structured values also get the fallback.

**Supported answer example:**
> From Store IQ knowledge: [short answer supported by the facts].
> Source: [document/model reference].

**Missing answer example:**
> Not enough facts present.
> I could not confirm [specific detail] for [model].

After either response, show these 3 buttons:

| Button | What it does |
|---|---|
| `Resolved` | Mark this question resolved by the associate and return to the saved customer step. Does not mark a sale or installation task complete. |
| `Ask admin` | Create a tracked admin request with the question, associate, customer serial number, selected TV, relevant photos, retrieved sources and the answer or missing facts. Notify the admin on the website. Repeated clicks do not create duplicate open requests for the same question. |
| `Ask follow-up` | Accept another text or voice question in the same thread, keeping context; run the same fact check again. If an admin request is already open, also add the follow-up to that request and notify its owner. |

### Admin request, notifications and replies

1. On `Ask admin`, show the request number and status: `Waiting for assignment` or `Assigned to [owner]`. Keep the current customer flow saved. Do not promise a response time that has not been agreed.
2. The admin website shows an unread notification and a request in the queue. Include associate name/number, customer serial/name, question, time and status. `Open request` opens the matching question, sources and customer context; `Assign` selects an owner; `Reply` opens the response box.
3. The admin writes an answer and uses `Send reply` to publish it, or `Cancel` to discard the draft. Label the published message **"Answered by [admin name]"**. For unverified details, the admin must identify what remains unconfirmed. Never silently replace the RAG answer.
4. Deliver the admin reply to the requesting associate on **both WhatsApp and the website customer chat**, under the same customer and request. Also show an unread website notification; clicking it opens that thread. If the associate has switched customers, include the original customer serial/name and do not change their active customer automatically.
5. The associate can use `Resolved`, `Ask admin` (reopen the same request if more admin help is needed), or `Ask follow-up`. A follow-up or other reply in the request thread appears in website history and notifies the assigned admin. Replies entered through either associate channel stay visible in both chat histories.
6. Admin replying changes the request to `Answered`; the associate choosing `Resolved` changes it to `Resolved`. Unanswered questions stay pending. Save sender, time, sources and status changes in the request history.

Keep WhatsApp replies within 3 lines and 3 buttons; put a longer explanation in the website thread and include its link. Track delivery failures and retry without duplicating the saved reply; never label a failed WhatsApp delivery as delivered. Website read status is separate from WhatsApp delivery status.

### If the admin takes too long

The associate can continue other questions, comparisons and demos while the request stays pending. Never present an unanswered question as a confirmed fact.

| When | What happens |
|---|---|
| Immediately after `Ask admin` | Say: "Request sent. You can continue with other questions." Show `Continue flow`, `View request`, `Save follow-up`. |
| After 2 minutes without an answer | Send a website reminder to the assigned admin. If unassigned, remind the admin queue. Keep the request pending. |
| After 5 minutes without an answer | Escalate to another available admin or the department manager with the question, elapsed time and current owner. If nobody is available, show "Waiting for assignment" and retain the request in the admin queue. |
| Customer wants to leave | Ask permission to follow up, record an agreed update time and owner, and save the pending question with the visit. Do not promise that the answer will arrive by that time. |
| Agreed update time arrives without an answer | Remind the follow-up owner to give a status update through the consented channel, even if the answer is still pending. |
| Answer arrives later | Save it against the original customer/request and notify the associate on WhatsApp and the website. Do not switch the associate away from their active customer or automatically message the customer. |

The 2-minute and 5-minute timings are configurable demo defaults, not promised response times. Count from request creation, including time waiting for assignment. Send each reminder/escalation once per unanswered request cycle; assignment alone does not stop the timer. An admin answer stops the timers. A reopened request starts a new cycle; viewing it or adding detail does not reset the wait.

| Button | What it does |
|---|---|
| `Continue flow` | Resume the customer's next step while preserving the pending request. |
| `View request` | Open the website thread with question, owner, wait time, escalation status and replies; give a short status in WhatsApp too. |
| `Save follow-up` | Ask for consent, agreed update time and owner; create a linked follow-up task without closing the admin request. If consent is declined, keep the task internal. |

If the missing answer affects compatibility, installation cost or finance, keep that decision or amount unconfirmed and hold the affected finalisation step. The associate can continue unaffected steps or offer a verified alternative. A pending price or charge must never be shown as zero or included in a claimed final total.

Use test associate/admin accounts and simulated or approved test WhatsApp delivery in the contest. Admin answers enter the knowledge base only after review; they are not automatically treated as approved facts for future questions.

## Other buttons: exact action

The buttons above already have their actions beside them. This table defines the remaining buttons in the main journey. Show only the buttons relevant to the current step, with no more than 3 in a WhatsApp message.

| Flow | Button | Action |
|---|---|---|
| Home details | `Correct` | Confirm the home card and move to recommendations or the next unresolved doubt. |
| Home details | `Edit` | Ask which detail to change, save the correction and refresh the home card. |
| Home details | `Ask customer` | Give the next missing question to ask aloud; wait for the associate's answer. |
| Label | `Explain another` | Ask for another label photo, model number or feature to explain. |
| Label | `Wrong model` | Discard the detected model selection and ask for a clearer photo or typed model. |
| Recommendations | `Demo A/B` | Save A and B as the demo pair and send the physical demo instructions. |
| Recommendations | `Change options` | Ask what to change, update the preferences and regenerate suitable options. |
| Recommendations | `Stock details` | Open website stock for the recommended models; also give a short availability reply in chat. |
| Demo | `Demo done` | Ask which TV the customer preferred and why; save the answer before completing the demo step. |
| Demo | `Need another demo` | Ask which difference still needs checking and give another relevant demo. |
| Demo | `Demo unavailable` | Record the reason and offer an alternative display model or expert help; keep the demo incomplete. |
| Full cost | `Optional extras` | Open relevant extras on the website with individual prices; chat can add or remove an item by name. `Add`/`Remove` changes the selection; `Done` saves it and refreshes the total. |
| Full cost | `Site check` | Ask the installation questions one at a time; save answers and flag unknown charges. |
| Full cost | `Continue` | Check assessment, demo and cost completeness; open offers if ready, otherwise explain what remains. |
| Payment | `Pay in full` | Record the payment preference and show the verified payable amount. This does not take payment or mark a sale complete. |
| Payment | `Finance` | Open available plans and full costs on the website; give the selected plan's cost in chat. `Select plan` saves the preference, not a finance approval. |
| Payment | `Save for later` | Save the current quote and ask the reason and follow-up permission. |
| Follow-up | `Save follow-up` | Collect consent, agreed time and owner; create a task. |
| Follow-up | `Other TV` | Return to recommendations with the existing home details. |
| Follow-up | `End visit` | Save the visit, keep pending tasks and show the coaching review. |
| Handover | `Confirm sale` | Record the associate's test sale confirmation and start delivery/installation handover. Available after the payment preference is recorded; never triggered just by opening a page. |
| Handover | `Consent given` | Save consent for the agreed summary/updates and prepare the customer summary. |
| Handover | `No consent` | Save the choice and keep the summary and tasks internal. |
| Handover | `Edit details` | Change selected items, cost or installation details; refresh the summary and reconfirm changed amounts. |
| Tasks | `Completed` | Ask what was completed and record confirmation for that task only. Installation completion still leaves the working check pending. |
| Tasks | `Problem` | Capture the problem and create/update an owned task with the next update time. |
| Review | `See score` | Show step-by-step scores in chat; open the website for supporting conversation details. |
| Review | `Add voice note` | Wait for a voice note, then save it against this customer and visit. |

After a payment preference is recorded, offer `Confirm sale`, `Save for later`, `Open summary`. These keep the sale confirmation explicit.

## Customer summary and PDF

**Trigger:** "Summary", `Open summary`, or finishing the handover. Open the website summary for the active customer; give a short recap in WhatsApp too.

Include the same customer serial number/name, associate, home needs, compared TVs, chosen model and reason, confirmed charges, optional items, offer/payment terms, pending details, delivery/installation status and contact owner. Label a pre-sale summary as a quote; do not show it as a completed purchase.

| Button | What it does |
|---|---|
| `Generate PDF` | Build a PDF from the current saved summary. Missing amounts remain "Not confirmed". |
| `Download PDF` | Download the generated PDF on the website. |
| `Share summary` | Check consent, show the intended recipient and preview the summary/PDF before sharing. In the contest, simulate delivery to a test recipient only. |
| `Confirm share` | Complete the previewed test share and record the recipient, time and PDF version. |
| `Cancel` | Cancel the share and return to the summary. |
| `Back to chat` | Resume the same customer conversation. |

Show these actions in groups of no more than 3 on WhatsApp. If the saved details change after PDF generation, mark it outdated and ask to regenerate before sharing.

## 10-minute TV demo story

1. Start shift, select TV, open stock by brand and complete or skip quick practice.
2. Send a voice note: living-room TV, cricket and movies, bright room, family sits on the sides.
3. Answer the missing home questions and confirm the home details.
4. Handle "all 4K TVs are the same", then scan a TV label for a simple explanation.
5. Get 3 options, open the website comparison, perform the physical demo and record the customer's preference.
6. Show itemised cost, optional extras, eligible offer and full finance cost.
7. Capture consent, generate the summary PDF and simulate sharing; create delivery/installation tasks.
8. Resume the same customer serial number from the website and WhatsApp list. Show a test expert request, installation delay, working check and coaching score. Open the admin summary filtered by associate.

## Source documents

- `6_Reliance_Digital_Store_IQ_Contest_28Oct2026.pdf`, pages 1-2: required journey, WhatsApp limits, data rules, judging and extra points.
- `Store_Visit_Findings_Reference_27Oct2026 (1).pdf`, pages 1-2: home questions, early price talk, explanation, demonstrations, full charges and installation follow-up gaps.

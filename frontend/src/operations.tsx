import { useEffect, useState } from "react";
import { RecordFields } from "./record-fields";
import { CustomerActivity } from "./customer-activity";
import {
  ArrowUpRight,
  ArrowRight,
  Clock,
  UserRound,
  CheckCircle2,
  Check,
  Send,
  RefreshCw,
  BookOpen,
  LoaderCircle,
} from "lucide-react";
import { api, date, money } from "./api";
import { Badge, Button, Empty, Heading, Sources } from "./ui";

export function Tasks({ data, run, refresh, open }: any) {
  const [editing, setEditing] = useState<any>(null),
    [status, setStatus] = useState("open");
  const tasks = data.tasks.filter(
    (t: any) =>
      status === "all" ||
      (status === "open" ? t.status !== "completed" : t.status === "completed"),
  );
  return (
    <>
      <Heading
        eyebrow="UNTIL IT WORKS AT HOME"
        title="Follow-through, with an owner."
        subtitle="Separate delivery, installation and working checks. Requested slots stay pending until confirmed."
      />
      <div className="brand-tabs task-tabs">
        {["open", "completed", "all"].map((s) => (
          <button
            key={s}
            className={s === status ? "active" : ""}
            onClick={() => setStatus(s)}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="task-grid">
        {tasks.map((t: any) => (
          <section className="panel task-card" key={t.id}>
            <div className="section-header">
              <Badge
                tone={
                  t.status === "problem"
                    ? "orange"
                    : t.status === "completed"
                      ? "green"
                      : "neutral"
                }
              >
                {t.status}
              </Badge>
              <span className="hint">{date(t.due_at)} IST</span>
            </div>
            <h3>{t.kind.replaceAll("_", " ")}</h3>
            <button
              className="text-button"
              onClick={() =>
                open(data.customers.find((c: any) => c.id === t.customer_id))
              }
            >
              {t.customer_name} <ArrowUpRight size={14} />
            </button>
            <p>{t.detail}</p>
            <div className="task-owner">
              <UserRound size={15} />
              {t.assigned_to}
              {t.kind === "followup" && !t.consent && (
                <Badge tone="neutral">Internal only</Badge>
              )}
            </div>
            {new Date(t.due_at) < new Date() && t.status !== "completed" && (
              <p className="overdue">
                <Clock size={14} />
                Overdue · agree the next update
              </p>
            )}
            <Button secondary onClick={() => setEditing(t)}>
              Update task <ArrowRight size={15} />
            </Button>
          </section>
        ))}
      </div>
      {!tasks.length && (
        <Empty title="No tasks in this view">
          Tasks appear after a test sale or an agreed follow-up.
        </Empty>
      )}
      {editing && (
        <div className="modal-backdrop">
          <form
            className="modal"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/tasks/" + editing.id, "POST", {
                  status: f.get("status"),
                  detail: f.get("detail"),
                  assigned_to: f.get("assigned_to"),
                  due_at: new Date(String(f.get("due_at"))).toISOString(),
                });
                setEditing(null);
                await refresh();
              });
            }}
          >
            <h2>Update {editing.kind.replaceAll("_", " ")}</h2>
            <label>
              Status
              <select name="status" defaultValue={editing.status}>
                {["pending", "confirmed", "completed", "problem"].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            <label>
              Evidence / issue / next action
              <textarea
                name="detail"
                defaultValue={editing.detail}
                required
                minLength={5}
              />
            </label>
            {editing.kind === "working_check" && (
              <p className="hint">
                Record picture, sound, devices and satisfaction to confirm the
                working check.
              </p>
            )}
            <label>
              Owner
              <input
                name="assigned_to"
                defaultValue={editing.assigned_to}
                required
              />
            </label>
            <label>
              Confirmed or next update time
              <input
                name="due_at"
                type="datetime-local"
                defaultValue={new Date(
                  new Date(editing.due_at).getTime() -
                    new Date().getTimezoneOffset() * 60000,
                )
                  .toISOString()
                  .slice(0, 16)}
                required
              />
            </label>
            <div className="form-actions">
              <Button secondary onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button type="submit">Save update</Button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

export function Requests({ data, active, run, refresh, open }: any) {
  const [question, setQuestion] = useState(""),
    [blocking, setBlocking] = useState(false),
    [customerId, setCustomerId] = useState(active?.id || ""),
    [selected, setSelected] = useState(active?.active_request_id || "");
  const request = data.requests.find((r: any) => r.id === selected);
  return (
    <>
      <Heading
        eyebrow="CONFIDENCE COMES FROM FACTS"
        title="Ask an expert"
        subtitle="Check approved knowledge in chat, then bring an admin into any unanswered question."
      />
      <div className="requests-layout">
        <section className="panel">
          <h3>A question worth confirming.</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                const r = await api("/requests", "POST", {
                  customer_id: customerId,
                  question,
                  blocking,
                });
                setSelected(r.id);
                setQuestion("");
                await refresh();
              });
            }}
          >
            <label>
              Customer
              <select
                required
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
              >
                <option value="">Choose a customer</option>
                {data.customers.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.serial}. {c.name} ·{" "}
                    {data.associates.find((u: any) => u.id === c.owner)?.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              What couldn’t you confirm?
              <textarea
                required
                minLength={3}
                maxLength={4000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Include the model and the missing fact…"
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={blocking}
                onChange={(e) => setBlocking(e.target.checked)}
              />
              Affects compatibility, charges or finance — hold finalisation
            </label>
            <Button type="submit">
              Ask admin <ArrowUpRight size={15} />
            </Button>
          </form>
          <p className="hint">
            Reminder after 2 minutes, escalation after 5. These are demo
            timings, not promised reply times.
          </p>
          <hr />
          {data.requests.map((r: any) => (
            <button
              key={r.id}
              className={`request-list-item ${r.id === selected ? "active" : ""}`}
              onClick={() => setSelected(r.id)}
            >
              <div>
                <b>
                  #{r.number} · {r.customer_name}
                </b>
                <Badge tone={r.status === "resolved" ? "green" : "neutral"}>
                  {r.status}
                </Badge>
              </div>
              <p>{r.question}</p>
              <small>
                {date(r.created_at)} ·{" "}
                {r.assigned_to || "Waiting for assignment"}
                {r.escalated ? " · Escalated" : ""}
              </small>
            </button>
          ))}
        </section>
        <section className="panel request-thread">
          {request ? (
            <>
              <div className="section-header">
                <div>
                  <div className="eyebrow">REQUEST #{request.number}</div>
                  <h2>{request.customer_name}</h2>
                </div>
                <Badge>{request.status}</Badge>
              </div>
              <p>{request.question}</p>
              <Sources sources={request.sources} />
              <div className="request-answer">
                <small>INITIAL KNOWLEDGE ANSWER</small>
                <p>{request.answer || "Not enough facts present."}</p>
              </div>
              {request.thread.map((t: any, i: number) => (
                <div key={i} className="thread-message">
                  <b>
                    {t.role === "admin" ? "Answered by " : ""}
                    {t.by}
                  </b>
                  <small>{date(t.at)}</small>
                  <p>{t.text}</p>
                </div>
              ))}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const text = String(f.get("text"));
                  run(async () => {
                    if (data.user.role === "admin")
                      await api(`/requests/${request.id}/reply`, "POST", {
                        text,
                      });
                    else
                      await api(`/requests/${request.id}/action`, "POST", {
                        action: "followup",
                        version: 1,
                        data: { text },
                      });
                    await refresh();
                  });
                  e.currentTarget.reset();
                }}
              >
                <label>
                  {data.user.role === "admin"
                    ? "Reply as " + data.user.name
                    : "Ask a follow-up"}
                  <textarea
                    name="text"
                    required
                    maxLength={4000}
                    placeholder="Identify anything that remains unconfirmed."
                  />
                </label>
                <Button type="submit">
                  {data.user.role === "admin" ? "Send reply" : "Send follow-up"}
                  <Send size={15} />
                </Button>
              </form>
              <div className="form-actions">
                {data.user.role === "admin" && (
                  <Button
                    secondary
                    onClick={() =>
                      run(async () => {
                        await api(`/requests/${request.id}/action`, "POST", {
                          action: "assign",
                          version: 1,
                          data: { owner: data.user.name },
                        });
                        await refresh();
                      })
                    }
                  >
                    Assign to me
                  </Button>
                )}
                <Button
                  secondary
                  onClick={() =>
                    run(async () => {
                      await api(`/requests/${request.id}/action`, "POST", {
                        action:
                          request.status === "resolved" ? "reopen" : "resolve",
                        version: 1,
                        data: request.blocking && request.status !== "resolved" ? { evidence: prompt("Verified answer or alternative and source (leave blank to resolve the thread while retaining the finalisation hold)") || "" } : {},
                      });
                      await refresh();
                    })
                  }
                >
                  {request.status === "resolved"
                    ? "Reopen request"
                    : "Resolved"}
                </Button>
                <button
                  className="text-button"
                  onClick={() =>
                    open(
                      data.customers.find(
                        (c: any) => c.id === request.customer_id,
                      ),
                    )
                  }
                >
                  Continue flow <ArrowRight size={15} />
                </button>
              </div>
            </>
          ) : (
            <Empty title="Every question keeps its context">
              Select a request to see sources, ownership and attributed replies.
            </Empty>
          )}
        </section>
      </div>
    </>
  );
}

export function Admin({ data, run, refresh, busy, open }: any) {
  const [tab, setTab] = useState("activity"),
    [editing, setEditing] = useState<any>(null),
    [json, setJson] = useState("");
  const edit = (record: any) => {
    setEditing(record);
    setJson(JSON.stringify(record, null, 2));
  };
  return (
    <>
      <Heading
        eyebrow="KEEP YOUR FLOOR IN SYNC"
        title="Store management"
        subtitle="Track customer interactions, unblock pending actions, and manage store information."
      />
      {tab !== "activity" && <section className="index-banner">
        <div className="square-icon">
          <BookOpen size={23} />
        </div>
        <div>
          <h3>
            {data.index.dirty
              ? "Stable facts are waiting to be indexed."
              : "Your knowledge index is ready."}
          </h3>
          <p>
            Version {data.index.version} ·{" "}
            {data.index.indexed_at
              ? date(data.index.indexed_at)
              : "Not indexed yet"}{" "}
            · BM25 + semantic embeddings + reciprocal rank fusion
          </p>
          <small>
            Prices, inventory, arrivals, offers and finance stay outside the
            index and are supplied live.
          </small>
        </div>
        <Button
          disabled={busy}
          onClick={() =>
            run(async () => {
              await api("/admin/reindex", "POST");
              await refresh();
            }, "Knowledge index rebuilt and published")
          }
        >
          {busy ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <RefreshCw size={17} />
          )}
          Rebuild RAG index
        </Button>
      </section>}
      <div className="brand-tabs task-tabs">
        {["activity", "products", "offers", "commercial", "knowledge"].map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => {
              setTab(t);
              setEditing(null);
            }}
          >
            {t === "activity" ? "Customer activity" : t === "products"
              ? "TVs & inventory"
              : t === "offers"
                ? "Dated offers"
                : t === "commercial"
                  ? "Charges & finance"
                  : "Approved knowledge"}
          </button>
        ))}
      </div>
      {tab === "activity" ? <CustomerActivity data={data} open={open} /> : <div className="admin-layout">
        <section className="panel">
          {(data[tab] || []).map((r: any) => (
            <button key={r.id} className="admin-record" onClick={() => edit(r)}>
              <div>
                <b>
                  {r.title ||
                    (tab === "commercial"
                      ? "Approved charges & finance"
                      : `${r.brand} ${r.model}`)}
                </b>
                <small>
                  {tab === "products"
                    ? `${money(r.price)} · ${r.stock} units · ${r.expected_on ? "arrives " + r.expected_on : "available"}`
                    : tab === "offers"
                      ? `${r.starts_on} — ${r.ends_on} · ${money(r.discount)} off`
                      : tab === "commercial"
                        ? `Installation ${money(r.installation)} · finance fee ${money(r.finance_fee)}`
                        : r.text.slice(0, 100) + "…"}
                </small>
              </div>
              <span>v{r.version}</span>
              <RefreshCw size={15} />
            </button>
          ))}
        </section>
        <section className="panel admin-editor">
          {editing ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                run(async () => {
                  let body;
                  try {
                    body = JSON.parse(json);
                  } catch {
                    throw Error("Invalid JSON. Correct it before saving.");
                  }
                  await api(`/admin/${tab}/${editing.id}`, "PUT", body);
                  setEditing(null);
                  await refresh();
                }, "Changes saved");
              }}
            >
              <h3>
                Edit {editing.title || editing.model || "charges & finance"}
              </h3>
              <p className="hint">
                Validated structured editor. Preserve id and version.
                Specification changes mark the index dirty; stock and price
                edits do not.
              </p>
              <RecordFields json={json} setJson={setJson} />
              <details className="advanced-editor">
                <summary>Advanced structured record</summary>
                <label>
                  Record
                  <textarea
                    className="json-editor"
                    spellCheck={false}
                    value={json}
                    onChange={(e) => setJson(e.target.value)}
                  />
                </label>
              </details>
              <div className="form-actions">
                <Button secondary onClick={() => setEditing(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={busy}>
                  Save changes <Check size={15} />
                </Button>
              </div>
            </form>
          ) : (
            <Empty title="Your store facts, under your control">
              Choose a record to edit. Knowledge rebuilds publish atomically;
              failures retain the previous index.
            </Empty>
          )}
        </section>
      </div>}
    </>
  );
}

export function Training({ data, run, refresh, newCustomer, onNavigate }: any) {
  const [feedback, setFeedback] = useState<any>(data.practice?.feedback || null),
    [repeat, setRepeat] = useState(false),
    [round, setRound] = useState<string[]>([]),
    [finished, setFinished] = useState(data.practice?.finished || false),
    [owner, setOwner] = useState(""),
    [since, setSince] = useState(""),
    [until, setUntil] = useState("");
  useEffect(() => { setFeedback(data.practice?.feedback || null); setFinished(data.practice?.finished || false); }, [data.practice?.feedback?.id, data.practice?.finished]);
  const mine = data.attempts.filter((a: any) => a.owner === data.user.id),
    seen = new Set(data.practice?.answered || []);
  const q = data.questions.find((q: any) => !seen.has(q.id));
  const attempts = data.attempts.filter(
    (a: any) =>
      (!owner || a.owner === owner) &&
      (!since ||
        new Date(a.created_at).toLocaleDateString("en-CA", {
          timeZone: "Asia/Kolkata",
        }) >= since) &&
      (!until ||
        new Date(a.created_at).toLocaleDateString("en-CA", {
          timeZone: "Asia/Kolkata",
        }) <= until),
  );
  return (
    <>
      <Heading
        eyebrow="A FEW MINUTES. A BETTER CONVERSATION."
        title="Learning studio"
        subtitle="One question at a time. Build the habits customers remember."
        action={
          <div className="chat-title-actions">
            <Button secondary onClick={() => onNavigate("chat")}>
              Back to chat
            </Button>
            <Button secondary onClick={newCustomer}>
              Start customer <ArrowRight size={15} />
            </Button>
          </div>
        }
      />
      <div className="training-layout">
        <section className="practice-card panel">
          <Badge>TV SPECIALIST PRACTICE</Badge>
          <p className="hint">
            No approved video is available. Practise with verified text
            guidance.
          </p>
          {feedback ? (
            <>
              <span
                className={`answer-icon ${feedback.correct ? "correct" : "incorrect"}`}
              >
                <CheckCircle2 size={30} />
              </span>
              <h2>
                {feedback.correct
                  ? "That’s the right instinct."
                  : "A useful moment to learn."}
              </h2>
              <p>{feedback.explanation}</p>
              <Button
                onClick={() => run(async () => {
                  await api("/training/session", "POST", {action: "next", version: 1});
                  setFeedback(null); await refresh();
                })}
              >
                Next question <ArrowRight size={16} />
              </Button>
            </>
          ) : q && !finished ? (
            <>
              <div className="eyebrow">{q.topic}</div>
              <h2>{q.question}</h2>
              <div className="answer-options">
                {q.options.map((o: string, i: number) => (
                  <button
                    key={o}
                    onClick={() =>
                      run(async () => {
                        const r = await api("/training", "POST", {
                          question_id: q.id,
                          choice: i,
                        });
                        setFeedback(r);
                        await refresh();
                      })
                    }
                  >
                    <span>{String.fromCharCode(65 + i)}</span>
                    {o}
                    <ArrowRight size={17} />
                  </button>
                ))}
              </div>
              <button className="text-button" onClick={() => run(async () => { await api("/training/session", "POST", {action: "finish", version: 1}); setFinished(true); await refresh(); })}>
                Finish practice & save progress
              </button>
            </>
          ) : (
            <>
              <CheckCircle2 size={40} />
              <h2>
                {finished
                  ? "A little sharper for the floor."
                  : "You’ve explored every topic."}
              </h2>
              <p>
                {mine.length} answers saved. Revisit a topic, or start your next
                customer.
              </p>
              <Button
                onClick={() => run(async () => {
                  await api("/training/session", "POST", {action: "repeat", version: 1});
                  setRepeat(true);
                  setRound([]);
                  setFinished(false);
                  setFeedback(null);
                  await refresh();
                })}
              >
                Repeat practice
              </Button>
              <Button secondary onClick={() => onNavigate("home")}>
                Return to shift
              </Button>
            </>
          )}
        </section>
        <aside className="panel training-stats">
          <h3>Your progress, saved.</h3>
          <div className="big-metric">
            {mine.length
              ? Math.round(
                  (mine.filter((a: any) => a.correct).length / mine.length) *
                    100,
                )
              : 0}
            <span>%</span>
          </div>
          <p>Accuracy across {mine.length} attempts</p>
          <h4>Topics to revisit</h4>
          {[
            ...new Set(
              mine.filter((a: any) => !a.correct).map((a: any) => a.topic),
            ),
          ].map((t: any) => (
            <Badge tone="orange" key={t}>
              {t}
            </Badge>
          ))}
          {!mine.some((a: any) => !a.correct) && (
            <p className="hint">No revisit topics yet. Keep going.</p>
          )}
          <hr />
          <p className="hint">
            Leaving saves answered questions. Unanswered questions never count
            as wrong.
          </p>
          <Button
            secondary
            onClick={() =>
              run(async () => {
                await api("/shift", "POST", { text: "skip_practice" });
                await refresh();
                onNavigate("home");
              })
            }
          >
            Finish & return to shift
          </Button>
        </aside>
      </div>
      <section className="panel training-history">
        <div className="section-header">
          <h2>Practice history</h2>
          {data.user.role === "admin" && (
            <select
              aria-label="Training associate"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
            >
              <option value="">All associates</option>
              {data.associates.map((u: any) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          )}
          <label className="inline-field">
            Since
            <input
              aria-label="Training start date"
              type="date"
              value={since}
              onChange={(e) => setSince(e.target.value)}
            />
          </label>
          <label className="inline-field">
            Until
            <input
              aria-label="Training end date"
              type="date"
              value={until}
              min={since || undefined}
              onChange={(e) => setUntil(e.target.value)}
            />
          </label>
        </div>
        {attempts
          .slice()
          .reverse()
          .slice(0, 30)
          .map((a: any) => (
            <div className="history-attempt" key={a.id}>
              <span>{a.topic}</span>
              <span>
                {data.associates.find((u: any) => u.id === a.owner)?.name}
              </span>
              <Badge tone={a.correct ? "green" : "orange"}>
                {a.correct ? "Correct" : "Revisit"}
              </Badge>
              <small>{date(a.created_at)}</small>
            </div>
          ))}
        {!attempts.length && (
          <p className="hint">
            Your first answer starts your learning history.
          </p>
        )}
      </section>
    </>
  );
}

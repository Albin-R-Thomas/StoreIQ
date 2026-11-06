import { useState } from "react";
import { date } from "./api";
import { Badge, Button, Empty, HOME, LABELS } from "./ui";

export function CustomerActivity({ data, open }: any) {
  const [query, setQuery] = useState("");
  const [owner, setOwner] = useState("");
  const [filter, setFilter] = useState("all");
  const rows = data.customers.map((c: any) => {
    const associate = data.associates.find((a: any) => a.id === c.owner)?.name || "Unassigned associate";
    const requests = data.requests.filter((r: any) => r.customer_id === c.id);
    const pending = requests.filter((r: any) => r.status !== "resolved");
    const holds = requests.filter((r: any) => r.blocking && !r.decision_evidence);
    const tasks = data.tasks.filter((t: any) => t.customer_id === c.id && t.status !== "completed")
      .sort((a: any, b: any) => Date.parse(a.due_at) - Date.parse(b.due_at));
    const overdue = tasks.some((t: any) => Date.parse(t.due_at) < Date.now());
    const problem = tasks.some((t: any) => t.status === "problem");
    const waiting = pending.filter((r: any) => ["waiting", "assigned"].includes(r.status));
    const attention = overdue || problem || holds.length > 0 || waiting.length > 0;
    return { c, associate, requests, pending, holds, tasks, overdue, problem, waiting, attention };
  });
  const visible = rows.filter((r: any) => (!owner || r.c.owner === owner)
    && `${r.c.name} ${r.c.serial} ${r.associate}`.toLowerCase().includes(query.toLowerCase())
    && (filter === "all" || (filter === "attention" && r.attention) || (filter === "waiting" && r.waiting.length) || (filter === "overdue" && r.overdue)))
    .sort((a: any, b: any) => Number(b.overdue) - Number(a.overdue) || Number(b.attention) - Number(a.attention));
  return <section className="customer-activity">
    <div className="section-header"><div><h2>Customer & associate activity</h2><p>Recorded waits, accountable next steps, and the conversation behind each visit.</p></div></div>
    <div className="activity-counts">
      {[["Customers", rows.length], ["Need attention", rows.filter((r: any) => r.attention).length], ["Waiting for expert", rows.filter((r: any) => r.waiting.length).length], ["Overdue follow-through", rows.filter((r: any) => r.overdue).length]].map(([label, value]) => <div className="panel" key={label}><strong>{value}</strong><span>{label}</span></div>)}
    </div>
    <div className="filter-bar">
      <input aria-label="Search customer or associate" placeholder="Search customer, serial or associate" value={query} onChange={e => setQuery(e.target.value)} />
      <select aria-label="Activity associate" value={owner} onChange={e => setOwner(e.target.value)}><option value="">All associates</option>{data.associates.map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
      <select aria-label="Customer activity status" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All visits</option><option value="attention">Needs attention</option><option value="waiting">Waiting for expert</option><option value="overdue">Overdue tasks</option></select>
    </div>
    <p className="hint">Counts cover the currently loaded visits. A next-step suggestion does not confirm that a customer is waiting. Messages are associate entries and Store IQ guidance.</p>
    {visible.map(({ c, associate, requests, pending, holds, tasks, overdue, problem, waiting }: any) => <section className="panel activity-card" key={c.id}>
      <div className="section-header"><div><h3>#{c.serial} · {c.name}</h3><p>Associate: <b>{associate}</b> · {LABELS[c.stage] || c.stage}</p></div><Badge tone={overdue || problem || holds.length ? "orange" : "neutral"}>{overdue ? "Overdue action" : problem ? "Task issue" : holds.length ? "Finalisation on hold" : waiting.length ? "Waiting for expert" : c.stage === "closed" ? "Completed" : "Visit in progress"}</Badge></div>
      <div className="activity-context"><div><small>NEXT ACTION / OWNER</small><p>{waiting.length ? `Expert response needed · ${waiting[0].assigned_to || "Admin assignment needed"}` : tasks.length ? `${tasks[0].kind.replaceAll("_", " ")} · ${tasks[0].assigned_to || "Owner needed"}` : c.stage === "closed" ? "No further action recorded" : `${c.flow?.buttons?.[0]?.label || LABELS[c.stage] || "Review visit"} · ${associate} (suggested)`}</p></div><div><small>LAST RECORDED ACTIVITY · IST</small><p>{date(c.updated_at)}</p>{tasks.length > 0 && <p>Next task due: {date(tasks[0].due_at)} IST</p>}</div></div>
      {holds.length > 0 && <p className="overdue">{holds.length} blocking question(s) still need verified decision evidence.</p>}
      <details><summary>View customer context, interactions & pending actions</summary>
        <div className="activity-detail">
          <h4>Customer context</h4><dl className="activity-home">{Object.entries(HOME).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{c.home?.[key] || "Not recorded"}</dd></div>)}</dl>
          <p>Selected TVs: {c.selected?.map((id: string) => { const p = data.products.find((p: any) => p.id === id); return p ? `${p.brand} ${p.model}` : id; }).join(", ") || "None recorded"}</p>
          <h4>Expert requests ({pending.length} unresolved)</h4>
          {requests.map((r: any) => <div className="activity-event" key={r.id}><b>#{r.number} · {r.status} · {r.assigned_to || "Unassigned"}</b><p>{r.question}</p><small>Raised {date(r.created_at)} IST{r.escalated ? " · Escalated" : ""}</small>{r.thread?.map((t: any, i: number) => <p key={i}>{t.by} · {date(t.at)}: {t.text}</p>)}</div>)}
          {!requests.length && <p className="hint">No expert requests recorded.</p>}
          <h4>Pending tasks</h4>{tasks.map((t: any) => <div className="activity-event" key={t.id}><b>{t.kind.replaceAll("_", " ")} · {t.status}</b><p>{t.detail}</p><small>Owner: {t.assigned_to || "Unassigned"} · Due {date(t.due_at)} IST</small></div>)}{!tasks.length && <p className="hint">No pending tasks recorded.</p>}
          <h4>Recorded interactions</h4><div className="activity-transcript">{(c.messages || []).map((m: any) => <div className="activity-event" key={m.id}><b>{m.role === "assistant" ? "Store IQ guidance" : m.role === "event" ? "Visit update" : m.role === "admin" ? `Admin · ${m.actor || "Admin"}` : `Associate entry · ${m.actor || associate}`}</b><small>{date(m.created_at)} IST</small><p>{m.text}</p></div>)}</div>{!c.messages?.length && <p className="hint">No interactions recorded.</p>}
          {c.notes?.map((n: any, i: number) => <div className="activity-event" key={i}><b>Visit note · {n.by}</b><small>{date(n.at)} IST</small><p>{n.text}</p></div>)}
          <div className="form-actions"><Button secondary onClick={() => open(c, "history")}>Open visit history</Button><Button secondary onClick={() => open(c, "requests")}>Manage expert requests</Button><Button onClick={() => open(c)}>Continue conversation</Button></div>
        </div>
      </details>
    </section>)}
    {!visible.length && <Empty title="No matching customer visits">Try another customer, associate or status.</Empty>}
  </section>;
}

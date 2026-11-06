import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  FileText,
  Heart,
  LoaderCircle,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api, money } from "./api";
import { VoiceNote } from "./voice-note";
import { ActionForm, MessageList } from "./chat";
import { Badge, Button, HOME, LABELS, STAGES, ReplyButtons } from "./ui";

const TITLES: Record<string, string> = {
  home: "Edit the home card",
  demo: "Which TV did the customer prefer?",
  demo_unavailable: "Why is the demo unavailable?",
  site: "Check the installation site",
  extras: "Choose optional extras",
  followup: "Agree the next step",
  note: "Add a visit note",
  select: "Choose the TVs to show",
  sale: "Review and confirm the test sale",
  expert: "Ask the store admin",
  task: "Update the handover task",
  score: "Review the recorded evidence",
};

export function Chat({
  customer: c,
  data,
  busy,
  run,
  setCustomer,
  refresh,
  act,
  onNavigate,
  onNewCustomer,
  onOpenCustomer,
}: any) {
  const [text, setText] = useState(""),
    [voiceBusy, setVoiceBusy] = useState(false),
    [voiceStatus, setVoiceStatus] = useState({ text: "", error: false }),
    [retry, setRetry] = useState<any>(null),
    [panel, setPanel] = useState<any>(null),
    [resume, setResume] = useState(
      c.messages.some((m: any) => m.role === "user" || m.role === "event"),
    );
  const bottom = useRef<HTMLDivElement>(null),
    composer = useRef<HTMLTextAreaElement>(null);
  const flow = c.flow;
  const lastBot = [...c.messages]
    .reverse()
    .find((m: any) => ["assistant", "admin"].includes(m.role));
  const flowInMessage =
    lastBot &&
    (lastBot.text === (flow?.lines || []).join("\n") ||
      ["expert", "validate", "translate"].includes(flow?.mode));
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [c.messages.length, busy, panel?.name]);
  const setCurrent = (updated: any) =>
    setCustomer((previous: any) =>
      previous?.id === c.id ? updated : previous,
    );
  const reload = async () => {
    const updated = await api("/customers/" + c.id);
    setCurrent(updated);
    await refresh();
    return updated;
  };
  const choose = async (b: any) => {
    setResume(false);
    if (b.kind === "navigate") {
      if (b.name === "new_customer") onNewCustomer();
      else if (b.name === "customers" && b.data?.start) onNavigate("customers", b.data);
      else if (b.name === "customers") onNavigate("customers");
      else if (b.name === "shift") onOpenCustomer("department");
      else onNavigate(b.name);
      return;
    }
    if (b.kind === "input") {
      setPanel(b);
      return;
    }
    const updated = await act(b.name, b.data || {});
    if (updated) {
      setPanel(null);
      if (
        b.name === "ask_home" ||
        b.name === "ask_expert" ||
        b.name === "explain_another"
      )
        composer.current?.focus();
    }
  };
  const send = async (message: string, id = crypto.randomUUID()) => {
    if (!message.trim() || busy || voiceBusy) return;
    setVoiceStatus({ text: "", error: false });
    setText("");
    setResume(false);
    setPanel(null);
    setRetry({ message, id });
    const result = await run(async () => {
      const updated = await api(`/customers/${c.id}/messages`, "POST", {
        text: message,
        request_id: id,
      });
      setCurrent(updated);
      await refresh();
      return updated;
    });
    if (result) setRetry(null);
    else {
      const saved = await api("/customers/" + c.id).catch(() => null);
      if (saved) setCurrent(saved);
    }
  };
  return (
    <>
      <div className="chat-heading">
        <button className="text-button" onClick={() => onNavigate("customers")}>
          <ArrowLeft size={15} />
          Customers
        </button>
        <div className="chat-title">
          <span className="customer-avatar">{c.name[0]}</span>
          <div>
            <h1>
              {c.serial}. {c.name}
            </h1>
            <p>{LABELS[c.stage]} · Saved conversation</p>
          </div>
        </div>
        <div className="chat-title-actions">
          <select
            aria-label="Coaching language"
            value={c.language}
            onChange={(e) => act("language", { language: e.target.value })}
          >
            {["English", "Hindi", "Marathi"].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
          <Button secondary onClick={() => onNavigate("summary")}>
            <FileText size={15} />
            Open summary
          </Button>
        </div>
      </div>
      <div className="journey-strip">
        {STAGES.slice(0, 7).map((s, i) => (
          <div
            key={s}
            className={
              s === c.stage
                ? "current"
                : STAGES.indexOf(c.stage) > i
                  ? "done"
                  : ""
            }
          >
            <span>
              {STAGES.indexOf(c.stage) > i ? <Check size={11} /> : i + 1}
            </span>
            {
              [
                "Home",
                "Options",
                "Demo",
                "Full cost",
                "Payment",
                "Handover",
                "Review",
              ][i]
            }
          </div>
        ))}
      </div>
      <div className="chat-layout guided-layout">
        <section className="chat-panel guided-panel">
          <div className="chat-panel-top">
            <span>
              <span className="status-dot" />
              Store IQ · Your floor partner
            </span>
            <span>
              <ShieldCheck size={13} />
              Facts checked. You choose.
            </span>
          </div>
          <div
            className="chat-scroll"
            role="log"
            aria-label="Customer conversation"
            aria-live="polite"
          >
            <MessageList
              messages={c.messages}
              activeMessageId={!resume && flowInMessage ? lastBot?.id : null}
              buttons={flow?.buttons}
              onChoose={choose}
              busy={busy}
            />
            {resume && (
              <div className="message assistant guided-next">
                <span className="message-avatar">
                  <Sparkles size={15} />
                </span>
                <div className="message-content">
                  <div className="message-meta">STORE IQ · WELCOME BACK</div>
                  <div className="message-bubble">{`Resuming ${c.serial}. ${c.name}. Your previous messages and decisions are saved.\nNext pending step: ${LABELS[c.stage]}.\nContinue the flow, read the history, or open the summary.`}</div>
                  <ReplyButtons
                    buttons={[
                      {
                        label: "Continue flow",
                        kind: "action",
                        name: "continue_flow",
                      },
                      {
                        label: "View history",
                        kind: "navigate",
                        name: "history",
                      },
                      {
                        label: "Open summary",
                        kind: "navigate",
                        name: "summary",
                      },
                    ]}
                    onChoose={choose}
                    disabled={busy}
                  />
                </div>
              </div>
            )}
            {!resume && !flowInMessage && flow && (
              <div className="message assistant guided-next">
                <span className="message-avatar">
                  <Sparkles size={15} />
                </span>
                <div className="message-content">
                  <div className="message-meta">STORE IQ · NEXT STEP</div>
                  <div className="message-bubble">{flow.lines.join("\n")}</div>
                  <ReplyButtons
                    buttons={flow.buttons}
                    onChoose={choose}
                    disabled={busy}
                  />
                </div>
              </div>
            )}
            {["complete", "close"].includes(c.stage) &&
              flow?.quote?.product && (
                <details className="chat-cost-details">
                  <summary>
                    <FileText size={14} />
                    See itemised cost <ChevronDown size={13} />
                  </summary>
                  {flow.quote.lines.map((line: any, i: number) => (
                    <div key={i}>
                      <span>{line.label}</span>
                      <b>{money(line.amount)}</b>
                    </div>
                  ))}
                  <div className="cost-total">
                    <span>
                      {flow.quote.total === null
                        ? "Known subtotal"
                        : "Confirmed total"}
                    </span>
                    <b>{money(flow.quote.total ?? flow.quote.subtotal)}</b>
                  </div>
                  {flow.quote.missing.map((m: string) => (
                    <p key={m}>Not confirmed: {m}</p>
                  ))}
                </details>
              )}
            {panel && (
              <section
                className="inline-chat-form"
                key={`${c.id}-${panel.name}`}
              >
                <div className="inline-form-header">
                  <span>
                    <MessageSquare size={15} />
                    {TITLES[panel.name] || "Continue the conversation"}
                  </span>
                  <button
                    aria-label="Cancel action"
                    className="icon-button"
                    onClick={() => setPanel(null)}
                  >
                    <X size={16} />
                  </button>
                </div>
                <InlineAction
                  panel={panel}
                  c={c}
                  data={data}
                  act={act}
                  run={run}
                  busy={busy}
                  reload={reload}
                  onClose={() => setPanel(null)}
                  onNavigate={onNavigate}
                />
              </section>
            )}
            {busy && (
              <div className="thinking" role="status">
                <LoaderCircle size={15} className="spin" />
                Checking the latest details…
              </div>
            )}
            <div ref={bottom} />
          </div>
          <div className="chat-controls">
            <div className="chat-utilities">
              <button disabled={busy} onClick={onNewCustomer}>
                <Plus size={13} />
                New customer
              </button>
              <button disabled={busy} onClick={() => onOpenCustomer()}>
                <MessageSquare size={13} />
                Customer list
              </button>
              <select
                aria-label="Useful actions"
                value=""
                onChange={(e) => {
                  const name = e.target.value;
                  if (
                    name === "summary" ||
                    name === "history" ||
                    name === "stock"
                  )
                    onNavigate(name);
                  else if (["followup", "note", "score"].includes(name))
                    setPanel({ kind: "input", name });
                  else if (name) choose({ kind: "action", name });
                }}
              >
                <option value="">Useful actions…</option>
                <option value="continue_flow">Continue flow</option>
                <option value="ask_expert">Ask an expert</option>
                <option value="followup">Save follow-up</option>
                <option value="note">Visit note</option>
                <option value="summary">Open summary / share</option>
                <option value="history">View history</option>
                <option value="stock">View stock</option>
                <option value="end_visit">End visit</option>
              </select>
            </div>
            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault();
                send(text);
              }}
            >
              <textarea
                ref={composer}
                rows={1}
                aria-label="Message Store IQ"
                placeholder={
                  flow?.placeholder || "Tell me what the customer says…"
                }
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(text);
                  }
                }}
              />
              <VoiceNote key={c.id} customerId={c.id} version={c.version} disabled={busy}
                onBusy={setVoiceBusy}
                onStatus={(text, error = false) => setVoiceStatus({ text, error })}
                onReady={(translated) => {
                  setText(previous => previous.trim() ? `${previous}\n${translated}` : translated);
                  composer.current?.focus();
                }} />
              <button aria-label="Send message" disabled={busy || voiceBusy || !text.trim()}>
                <Send size={18} />
              </button>
            </form>
            <div className="composer-note">
              <span role={voiceStatus.error ? "alert" : "status"} className={voiceStatus.error ? "error" : ""}>
                {voiceStatus.text || "Type or record a voice note · Shift + Enter for a new line"}
              </span>
              {retry && !busy && (
                <button
                  className="text-button"
                  onClick={() => send(retry.message, retry.id)}
                >
                  Retry saved message
                </button>
              )}
            </div>
          </div>
        </section>
        <aside className="context-panel compact-context">
          <section className="panel home-card">
            <div className="section-header">
              <h3>
                <Heart size={15} />
                This customer’s home
              </h3>
              <Badge tone={c.confirmed ? "green" : "neutral"}>
                {c.confirmed ? "Confirmed" : "In progress"}
              </Badge>
            </div>
            {Object.entries(HOME).map(([k, label]) => (
              <div
                className={`home-field ${flow?.question === k ? "current-home-question" : ""}`}
                key={k}
              >
                <small>{label}</small>
                <span className={c.home[k] ? "" : "muted"}>
                  {c.home[k] || "Not asked yet"}
                </span>
              </div>
            ))}
            <p className="hint">
              The next question appears in chat. Unknown is a valid answer; do
              not guess.
            </p>
          </section>
          <section className="panel conversation-context">
            <div className="eyebrow">KEEP THE CONVERSATION HUMAN</div>
            <p>
              Ask one question. Listen to the answer. Use the next reply button
              when you’re ready.
            </p>
            <p className="hint">
              Reading a page never records a demo, sale or completed
              installation.
            </p>
          </section>
        </aside>
      </div>
    </>
  );
}

function InlineAction({
  panel,
  c,
  data,
  act,
  run,
  busy,
  reload,
  onClose,
  onNavigate,
}: any) {
  const [selected, setSelected] = useState<string[]>(c.selected || []);
  if (
    [
      "home",
      "demo",
      "demo_unavailable",
      "start_demo",
      "site",
      "extras",
      "followup",
      "note",
    ].includes(panel.name)
  )
    return (
      <ActionForm
        modal={{ action: panel.name, title: TITLES[panel.name] }}
        act={act}
        busy={busy}
        onClose={onClose}
        customer={c}
        data={data}
      />
    );
  if (panel.name === "score")
    return (
      <>
        <p className="hint">
          Recorded evidence. Pending steps are not a final score.
        </p>
        {(c.score || []).map((s: any) => (
          <div key={s.step} className="score-row">
            <span>{s.step}</span>
            <Badge tone={s.points ? "green" : "neutral"}>
              {s.applicable ? `${s.points}/2` : s.status}
            </Badge>
          </div>
        ))}
        <Button secondary onClick={onClose}>
          Continue conversation
        </Button>
      </>
    );
  if (panel.name === "select")
    return (
      <>
        <p className="hint">
          Choose up to three TVs. Changing the shortlist clears the previous
          demo evidence.
        </p>
        <div className="inline-product-list">
          {data.products.map((p: any) => (
            <label key={p.id}>
              <input
                type="checkbox"
                checked={selected.includes(p.id)}
                disabled={!selected.includes(p.id) && selected.length >= 3}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, p.id]
                      : selected.filter((id) => id !== p.id),
                  )
                }
              />
              <span>
                <b>
                  {p.brand} {p.model}
                </b>
                <small>
                  {p.size}″ {p.panel} · {money(p.price)} ·{" "}
                  {p.stock ? `${p.stock} in stock` : "Out of stock"}
                </small>
              </span>
            </label>
          ))}
        </div>
        <div className="form-actions">
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || !selected.length}
            onClick={async () => {
              if (await act("select", { products: selected })) onClose();
            }}
          >
            Save options
          </Button>
        </div>
      </>
    );
  if (panel.name === "sale") {
    const q = c.flow.quote;
    const amount = q.finance?.total ?? q.total;
    return (
      <>
        <p>
          Confirm{" "}
          <b>
            {q.product?.brand} {q.product?.model}
          </b>{" "}
          at <b>{money(amount)}</b>.
        </p>
        <p className="hint">
          This explicit confirmation records one synthetic sale and creates
          delivery, installation and working-check tasks. No real payment is
          collected.
        </p>
        <div className="form-actions">
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={busy || amount === null}
            onClick={async () => {
              if (await act("sale", { confirmed_total: amount })) onClose();
            }}
          >
            Confirm test sale
          </Button>
        </div>
      </>
    );
  }
  if (panel.name === "expert") {
    const last = [...c.messages]
      .reverse()
      .find(
        (m: any) =>
          m.role === "user" &&
          !["ask admin", "ask an expert", "ask follow-up", "resolved"].includes(
            m.text.toLowerCase(),
          ),
      );
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          run(async () => {
            const r = await api("/requests", "POST", {
              customer_id: c.id,
              question: f.get("question"),
              blocking: f.get("blocking") === "on",
            });
            await reload();
            onClose();
            return r;
          });
        }}
      >
        <p className="hint">
          The request includes this customer, selected models and the last
          knowledge answer. Repeated open questions are deduplicated.
        </p>
        <label>
          What should the admin check?
          <textarea
            name="question"
            defaultValue={last?.text || ""}
            minLength={3}
            maxLength={4000}
            required
          />
        </label>
        <label className="checkbox-label">
          <input name="blocking" type="checkbox" />
          This affects compatibility, a charge or finance; hold finalisation
        </label>
        <div className="form-actions">
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Ask admin
          </Button>
        </div>
      </form>
    );
  }
  if (panel.name === "task") {
    const t = data.tasks.find((t: any) => t.id === panel.data.task_id);
    if (!t)
      return (
        <p className="hint">The task changed. Refresh this conversation.</p>
      );
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          run(async () => {
            await api("/tasks/" + t.id, "POST", {
              status: panel.data.status,
              detail: f.get("detail"),
              assigned_to: f.get("owner"),
              due_at: new Date(String(f.get("due_at"))).toISOString(),
            });
            await reload();
            onClose();
          });
        }}
      >
        <p>
          <b>{t.kind.replaceAll("_", " ")}</b> ·{" "}
          {panel.data.status === "completed"
            ? "Confirm what was completed."
            : "Record the issue and next update."}
        </p>
        {t.kind === "working_check" && (
          <p className="hint">
            Confirm picture, sound, devices and satisfaction; installation alone
            does not close the visit.
          </p>
        )}
        <label>
          Evidence / issue / next action
          <textarea name="detail" minLength={5} required />
        </label>
        <label>
          Owner
          <input name="owner" defaultValue={t.assigned_to} required />
        </label>
        <label>
          Agreed next update or confirmed time
          <input
            name="due_at"
            type="datetime-local"
            defaultValue={new Date(
              new Date(t.due_at).getTime() -
                new Date().getTimezoneOffset() * 60000,
            )
              .toISOString()
              .slice(0, 16)}
            required
          />
        </label>
        <div className="form-actions">
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Save task update
          </Button>
        </div>
      </form>
    );
  }
  return (
    <Button secondary onClick={onClose}>
      Back to conversation
    </Button>
  );
}

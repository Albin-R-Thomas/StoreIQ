import { useState, useEffect } from "react";
import { ArrowRight, Send, Sparkles } from "lucide-react";
import { api, date } from "./api";
import { Button, Heading, ReplyButtons } from "./ui";

export function ChatLobby({
  data,
  run,
  refresh,
  onNewCustomer,
  onOpen,
  onNavigate,
  initialMode,
}: any) {
  const [mode, setMode] = useState(
      initialMode || (data.shift ? "brief" : "welcome"),
    ),
    [roster, setRoster] = useState<any[]>(data.customers),
    [text, setText] = useState(""),
    [offset, setOffset] = useState(0),
    [range, setRange] = useState({ start: "", end: "" }),
    [filter, setFilter] = useState("all"),
    [notice, setNotice] = useState("");
  useEffect(() => {
    api("/bootstrap")
      .then((b) => setRoster(b.customers))
      .catch(() => {});
  }, []);
  const day = (offset: number) =>
    new Date(Date.now() + offset * 86400000).toLocaleDateString("en-CA", {
      timeZone: "Asia/Kolkata",
    });
  const dates =
    filter === "today"
      ? { start: day(0), end: day(0) }
      : filter === "yesterday"
        ? { start: day(-1), end: day(-1) }
        : filter === "range"
          ? range
          : null;
  const customers = roster.filter(
    (c: any) =>
      !dates ||
      c.activities.some((t: string) => {
        const d = new Date(t).toLocaleDateString("en-CA", {
          timeZone: "Asia/Kolkata",
        });
        return d >= dates.start && d <= dates.end;
      }),
  );
  const showList = (f: string) => {
    setFilter(f);
    setOffset(0);
    setNotice("");
    setMode("customers");
  };
  const choose = async (b: any) => {
    setNotice("");
    switch (b.name) {
      case "start":
        setMode("department");
        break;
      case "tv": {
        const r = await run(async () => {
          await api("/shift", "POST", { text: "start" });
          await refresh();
          return true;
        });
        if (r) setMode("brief");
        break;
      }
      case "skip": {
        const r = await run(async () => {
          await api("/shift", "POST", { text: "skip_practice" });
          await refresh();
          return true;
        });
        if (r) setMode("ready");
        break;
      }
      case "new":
        onNewCustomer();
        break;
      case "list":
        setMode("filters");
        break;
      case "stock":
        onNavigate("stock");
        break;
      case "training":
        onNavigate("training");
        break;
      case "today":
        showList("today");
        break;
      case "yesterday":
        showList("yesterday");
        break;
      case "range":
        setMode("range");
        break;
      case "prev":
        setOffset(Math.max(0, offset - 3));
        break;
      case "next":
        setOffset(offset + 3);
        break;
    }
  };
  const b = (label: string, name: string) => ({ label, name, kind: "local" });
  const buttons =
    mode === "welcome"
      ? [
          b("Start shift", "start"),
          b("New customer", "new"),
          b("Customer list", "list"),
        ]
      : mode === "department"
        ? [b("TV", "tv")]
        : mode === "brief"
          ? [
              b("View stock", "stock"),
              b("Start practice", "training"),
              b("Skip practice today", "skip"),
            ]
          : mode === "ready"
            ? [
                b("New customer", "new"),
                b("Customer list", "list"),
                b("View stock", "stock"),
              ]
            : mode === "filters"
              ? [
                  b("Today", "today"),
                  b("Yesterday", "yesterday"),
                  b("Date range", "range"),
                ]
              : mode === "customers"
                ? [
                    ...(offset > 0 ? [b("Previous", "prev")] : []),
                    ...(offset + 3 < customers.length
                      ? [b("Next", "next")]
                      : []),
                    b("New customer", "new"),
                  ]
                : [];
  const prompt =
    mode === "welcome"
      ? "Welcome to Store IQ. Let’s get ready for your next customer.\nStart your shift or resume a saved conversation."
      : mode === "department"
        ? "Which department are you working in today?\nTV is available for now."
        : mode === "brief"
          ? `TV today: ${data.products.filter((p: any) => p.stock > 0).length} models available; ${data.products.reduce((n: number, p: any) => n + p.stock, 0)} units in stock.\n${data.offers.filter((o: any) => o.starts_on <= day(0) && o.ends_on >= day(0)).length} current store offers; eligibility is checked after assessment and demo.\nWant a quick practice before serving customers?`
          : mode === "ready"
            ? "Your TV shift is ready. Practice is saved separately.\nStart a new customer, resume a visit, or browse the stock."
            : mode === "filters"
              ? "Which customers would you like to see?\nDates use store time (IST) and include both start and end dates."
              : mode === "range"
                ? "Choose the start and end dates.\nI’ll find customers with conversation or visit activity in that period."
                : `${dates ? `${dates.start} to ${dates.end} · IST` : "All permitted customers"}\n${customers.length ? "Choose a customer below or type their serial number to continue." : "No customers match these dates. Change dates to try again."}`;
  const submit = async () => {
    const q = text.trim();
    setText("");
    if (!q) return;
    const key = q.toLowerCase();
    if (mode === "customers" && /^\d+$/.test(q)) {
      const matches = customers.filter((c: any) => c.serial === Number(q));
      if (matches.length === 1) onOpen(matches[0]);
      else
        setNotice(
          matches.length
            ? "Several associates have that serial. Choose the customer row with its owner."
            : "No matching customer serial in this list.",
        );
      return;
    }
    if (key === "start shift") choose({ name: "start" });
    else if (key === "tv") choose({ name: "tv" });
    else if (["my customers", "customer list", "customers"].includes(key))
      setMode("filters");
    else if (key === "customers yesterday") showList("yesterday");
    else if (key === "customers today") showList("today");
    else if (key === "all customers") showList("all");
    else if (key === "change dates") setMode("filters");
    else if (key === "new customer") onNewCustomer();
    else if (key === "practice") onNavigate("training");
    else if (key === "view stock") onNavigate("stock");
    else
      setNotice(
        "Choose Start shift, New customer or Customer list to begin. Customer details are saved in their own conversation.",
      );
  };
  return (
    <>
      <Heading
        eyebrow="ONE CONVERSATION, EVERY STEP"
        title="Your associate chat"
        subtitle="The same guided journey as the documented messaging flow, here in your workspace."
      />
      <div className="lobby-shell">
        <section className="chat-panel guided-panel lobby-panel">
          <div className="chat-panel-top">
            <span>
              <span className="status-dot" />
              Store IQ · TV department
            </span>
            <span>Text and reply buttons</span>
          </div>
          <div className="chat-scroll">
            <div className="conversation-date">YOUR SHIFT · {day(0)}</div>
            <div className="message assistant">
              <span className="message-avatar">
                <Sparkles size={16} />
              </span>
              <div className="message-content">
                <div className="message-meta">STORE IQ</div>
                <div className="message-bubble">{prompt}</div>
                <ReplyButtons buttons={buttons} onChoose={choose} />
              </div>
            </div>
            {mode === "range" && (
              <form
                className="inline-chat-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (range.end < range.start) {
                    setNotice("End date must be on or after start date.");
                    return;
                  }
                  showList("range");
                }}
              >
                <label>
                  Start date
                  <input
                    aria-label="Start date"
                    type="date"
                    required
                    value={range.start}
                    onChange={(e) =>
                      setRange({ ...range, start: e.target.value })
                    }
                  />
                </label>
                <label>
                  End date
                  <input
                    aria-label="End date"
                    type="date"
                    required
                    min={range.start}
                    value={range.end}
                    onChange={(e) =>
                      setRange({ ...range, end: e.target.value })
                    }
                  />
                </label>
                <Button type="submit">Show customers</Button>
              </form>
            )}
            {mode === "customers" && (
              <>
                <div className="chat-customer-list">
                  {customers.slice(offset, offset + 3).map((c: any) => (
                    <button key={c.id} onClick={() => onOpen(c)}>
                      <span className="customer-avatar">{c.serial}</span>
                      <span>
                        <b>
                          {c.serial}. {c.name}
                        </b>
                        <small>
                          {c.stage} · {date(c.updated_at)} ·{" "}
                          {
                            data.associates.find((a: any) => a.id === c.owner)
                              ?.name
                          }
                        </small>
                      </span>
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
                <div className="lobby-filter-actions">
                  <button onClick={() => setMode("filters")}>
                    Change dates
                  </button>
                  <button onClick={() => showList("all")}>All customers</button>
                </div>
              </>
            )}
            {notice && (
              <p className="lobby-notice" role="status">
                {notice}
              </p>
            )}
          </div>
          <div className="chat-controls">
            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault();
                submit();
              }}
            >
              <textarea
                rows={1}
                aria-label="Message Store IQ"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={
                  mode === "customers"
                    ? "Type the customer serial number…"
                    : "Try “Start shift”, “Customer list” or “Practice”…"
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
              />
              <button aria-label="Send message" disabled={!text.trim()}>
                <Send size={18} />
              </button>
            </form>
          </div>
        </section>
        <aside className="panel lobby-guide">
          <Sparkles size={27} />
          <h2>
            Ask. Listen.
            <br />
            Find the right fit.
          </h2>
          <p>
            The chat gives you one useful question and the next action, right
            when you need it.
          </p>
          <ol>
            <li>Start with the home</li>
            <li>Show a real difference</li>
            <li>Explain the complete cost</li>
            <li>Follow through until it works</li>
          </ol>
          <p className="hint">
            Practice is separate. Customers keep their own history, permanent
            serial and next pending step.
          </p>
        </aside>
      </div>
    </>
  );
}

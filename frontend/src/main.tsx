import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  ArrowUpRight,
  ChevronRight,
  ChevronDown,
  Plus,
  Sparkles,
  LayoutDashboard,
  MessageSquare,
  Monitor,
  Users,
  GraduationCap,
  GitCompareArrows,
  ClipboardList,
  Bell,
  Settings,
  LogOut,
  Clock,
  ShieldCheck,
  Package,
  CheckCircle2,
  X,
  LoaderCircle,
  RefreshCw,
  AlertCircle,
  Lightbulb,
  CalendarDays,
  Menu,
  FileText,
} from "lucide-react";
import { api, date, money } from "./api";
import { Button, Badge, Empty, Heading, LABELS } from "./ui";
import { Catalogue, ProductDetails, Comparison } from "./catalogue";
import { ActionForm, MessageList } from "./chat";
import { Chat } from "./guided-chat";
import { ChatLobby } from "./chat-lobby";
import { Summary, Shared } from "./summary";
import { Tasks, Training, Requests, Admin } from "./operations";
import { OfferSchedule } from "./schedule";
import { CustomerActivity } from "./customer-activity";
import { BrandMark } from "./brand-mark";
import "./styles.css";
import "./guided-chat.css";

const NAV = [
  ["home", "Overview", LayoutDashboard],
  ["chat", "Associate chat", MessageSquare],
  ["stock", "TV catalogue", Monitor],
  ["customers", "Customers", Users],
  ["compare", "Compare TVs", GitCompareArrows],
  ["tasks", "Follow-through", ClipboardList],
  ["training", "Learning studio", GraduationCap],
  ["requests", "Ask an expert", Lightbulb],
  ["history", "Visit history", Clock],
] as const;

function Login({ onLogin }: any) {
  const [phone, setPhone] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="login">
      <div className="login-story">
        <div className="brand">
          <span className="brand-icon">
            <BrandMark />
          </span>
          store<span>iq</span>
          <Badge tone="light">ASSOCIATE</Badge>
        </div>
        <div className="login-copy">
          <div className="eyebrow">BETTER QUESTIONS. BETTER EXPERIENCES.</div>
          <h1>
            A little intelligence.
            <br />A lot more human.
          </h1>
          <p>
            Your partner on the shop floor. Understand the home, find the right
            screen, and stay with the customer until it works.
          </p>
          <div className="login-art">
            <div className="orb" />
            <div className="art-card">
              <Monitor />
              <span>
                Thoughtful recommendations.
                <br />
                <b>Made for this home.</b>
              </span>
              <Sparkles />
            </div>
          </div>
        </div>
        <small>
          Store IQ · Synthetic contest workspace · Text conversations
        </small>
      </div>
      <form
        className="login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            onLogin(await api("/auth/login", "POST", { phone, password }));
          } catch (e: any) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Badge>YOUR FLOOR. YOUR WORKSPACE.</Badge>
        <h2>Welcome to your shift.</h2>
        <p>Sign in to pick up where your customers left off.</p>
        <label>
          Registered mobile number
          <input
            autoComplete="username"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        <Button type="submit" disabled={busy}>
          {busy ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <>
              Open workspace <ArrowRight size={17} />
            </>
          )}
        </Button>
      </form>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<any>(null),
    [loading, setLoading] = useState(true),
    [data, setData] = useState<any>(null),
    [page, setPage] = useState("home"),
    [chatEntry, setChatEntry] = useState<string | null>(null),
    [active, setActive] = useState<any>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [modal, setModal] = useState<any>(null),
    [shortlist, setShortlist] = useState<string[]>([]),
    [mobile, setMobile] = useState(false),
    [filters, setFilters] = useState({ start: "", end: "", associate: "" });
  const shareToken = location.pathname.startsWith("/share/")
    ? location.pathname.split("/")[2]
    : null;
  useEffect(() => { setError(""); setModal(null); }, [page, active?.id]);
  const currentContext = useRef("");
  currentContext.current = `${page}:${active?.id || ""}`;
  const refresh = async (f = filters) => {
    const q = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
    const b = await api("/bootstrap?" + q);
    setData(b);
    setActive((current: any) => {
      if (!current) return current;
      const updated = b.customers.find((c: any) => c.id === current.id);
      if (!updated) return current;
      return updated.version !== current.version
        ? updated
        : { ...current, flow: updated.flow };
    });
    return b;
  };
  const run = async (fn: () => Promise<any>, success = "") => {
    const context = currentContext.current;
    setBusy(true);
    setError("");
    try {
      const r = await fn();
      if (success) setNotice(success);
      return r;
    } catch (e: any) {
      if (currentContext.current === context) setError(e.message);
      if (e.status === 401) {
        setUser(null);
        setData(null);
        setActive(null);
      }
      return null;
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (shareToken) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!user) return;
    refresh().catch((e) => setError(e.message));
    const timer = setInterval(() => refresh().catch(() => {}), 30000);
    return () => clearInterval(timer);
  }, [user, filters.start, filters.end, filters.associate]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(timer);
  }, [notice]);
  const open = async (c: any, target = "chat") => {
    if (!c) return;
    await run(async () => {
      const full = await api("/customers/" + c.id);
      setActive(full);
      setShortlist(full.selected);
      setPage(target);
      setMobile(false);
    });
  };
  const act = async (action: string, values: any = {}) => {
    if (!active) return;
    return run(async () => {
      try {
        await api(`/customers/${active.id}/actions`, "POST", {
          action,
          version: active.version,
          data: values,
        });
      } catch (e: any) {
        if (e.status === 409) {
          const current = await api("/customers/" + active.id);
          setActive((previous: any) =>
            previous?.id === active.id ? current : previous,
          );
        }
        throw e;
      }
      const c = await api("/customers/" + active.id);
      setActive((previous: any) => (previous?.id === active.id ? c : previous));
      if (action === "select" || action === "confirm_home")
        setShortlist(c.selected);
      await refresh();
      return c;
    });
  };
  const nav = (p: string, dates?: {start: string; end: string}) => {
    if (dates?.start) setFilters(f => ({...f, ...dates}));
    setPage(p);
    setMobile(false);
  };
  const newCustomer = () => setModal({ type: "new" });
  if (shareToken) return <Shared token={shareToken} />;
  if (loading)
    return (
      <div className="loading">
        <Sparkles className="pulse" />
        Opening Store IQ…
      </div>
    );
  if (!user) return <Login onLogin={setUser} />;
  if (!data)
    return (
      <div className="loading">
        {error || "Preparing your workspace…"}
        {error && <Button onClick={() => run(() => refresh())}>Retry</Button>}
      </div>
    );
  const unresolved = data.requests.filter(
    (r: any) => !["resolved", "answered"].includes(r.status),
  );
  const overdue = data.tasks.filter(
    (t: any) => t.status !== "completed" && new Date(t.due_at) < new Date(),
  );
  const unread = data.notifications.filter((n: any) => !n.read).length;
  return (
    <div className="app">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-icon">
            <BrandMark />
          </span>
          store<span>iq</span>
          <span className="brand-dot" />
        </div>
        <div className="store-switch">
          <div className="store-symbol">
            <Monitor size={18} />
          </div>
          <div>
            <b>Andheri Experience</b>
            <small>Mumbai · TV department</small>
          </div>
          <ChevronDown size={15} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {NAV.map(([id, label, Icon]) => (
            <button
              key={id}
              className={page === id ? "active" : ""}
              onClick={() => nav(id)}
            >
              <Icon size={18} />
              {label}
              {id === "requests" && unresolved.length > 0 && (
                <span className="nav-count">{unresolved.length}</span>
              )}
            </button>
          ))}
          {user.role === "admin" && (
            <button
              onClick={() => nav("admin")}
              className={page === "admin" ? "active" : ""}
            >
              <Settings size={18} />
              Store management
            </button>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="knowledge-status">
            <span className={`status-dot ${data.index.dirty ? "amber" : ""}`} />
            <div>
              <b>
                {data.index.dirty
                  ? "Knowledge update pending"
                  : "Knowledge is up to date"}
              </b>
              <small>
                {data.index.dirty
                  ? "Live data is always current"
                  : `Index v${data.index.version} · approved facts`}
              </small>
            </div>
          </div>
          <div className="profile">
            <span className="avatar">
              {user.name
                .split(" ")
                .map((n: string) => n[0])
                .join("")}
            </span>
            <div>
              <b>{user.name}</b>
              <small>
                {user.role === "admin"
                  ? "Store administrator"
                  : "TV specialist"}
              </small>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={() =>
                run(async () => {
                  await api("/auth/logout", "POST");
                  setUser(null);
                  setData(null);
                  setActive(null);
                })
              }
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-only"
              aria-label="Open menu"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            Workspace <ChevronRight size={13} />
            <b>
              {NAV.find((n) => n[0] === page)?.[1] ||
                (page === "summary"
                  ? "Customer summary"
                  : page === "notifications"
                    ? "Notifications"
                    : "Store management")}
            </b>
          </div>
          <div className="top-actions">
            <span className="test-label">
              {data.demo ? "DEMO WORKSPACE" : "STORE WORKSPACE"}
            </span>
            <span className="today">
              <CalendarDays size={15} />
              {new Date().toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                timeZone: "Asia/Kolkata",
              })}
            </span>
            <button
              className="notification-button"
              aria-label={`${unread} unread notifications`}
              onClick={() => nav("notifications")}
            >
              <Bell size={19} />
              {unread > 0 && <span>{unread}</span>}
            </button>
            <span className="avatar small">{user.name[0]}</span>
          </div>
        </header>
        <main key={page} className="main animate-in">
          {error && (
            <div className="error global-error" role="alert">
              <AlertCircle size={17} />
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <CheckCircle2 size={17} />
              {notice}
            </div>
          )}
          {page === "home" && (
            <>
              <Heading
                eyebrow="YOUR EVERYDAY EDGE"
                title={
                  <>
                    Good {new Date().getHours() < 12 ? "morning" : "afternoon"},{" "}
                    {user.name.split(" ")[0]}{" "}
                    <span className="sun-icon">✳</span>
                  </>
                }
                subtitle="Great conversations start with a little clarity. Here’s your floor today."
                action={
                  <Button onClick={newCustomer}>
                    <Plus size={17} />
                    New customer
                  </Button>
                }
              />
              {user.role === "admin" && <CustomerActivity data={data} open={open} />}
              <div className="overview-grid">
                <section className="shift-card">
                  <div className="shift-intro">
                    <Badge tone="light">
                      <span className="status-dot" /> YOUR SHIFT BRIEF
                    </Badge>
                    <span className="shift-date">
                      TV DEPARTMENT <Monitor size={17} />
                    </span>
                  </div>
                  <h2>
                    A better fit.
                    <br />A better experience.
                  </h2>
                  <p>
                    {data.products.filter((p: any) => p.stock > 0).length} TVs
                    ready to recommend.{" "}
                    {
                      data.offers.filter(
                        (o: any) =>
                          o.starts_on <=
                            new Date().toISOString().slice(0, 10) &&
                          o.ends_on >= new Date().toISOString().slice(0, 10),
                      ).length
                    }{" "}
                    store promotions running.
                    <br />
                    Start with the home. Let the right screen follow.
                  </p>
                  <div className="shift-buttons">
                    <Button
                      onClick={() =>
                        run(async () => {
                          await api("/shift", "POST", { text: "start" });
                          await refresh();
                          nav("stock");
                        })
                      }
                    >
                      {data.shift ? "Browse today’s stock" : "Start TV shift"}
                      <ArrowUpRight size={16} />
                    </Button>
                    <button
                      className="text-button"
                      onClick={() => nav("training")}
                    >
                      Quick practice <ArrowRight size={16} />
                    </button>
                  </div>
                  <div className="hero-orbit orbit-one" />
                  <div className="hero-orbit orbit-two" />
                  <div className="hero-screen">
                    <div className="hero-landscape" />
                    <span>made for their world.</span>
                  </div>
                </section>
                <section className="focus-card">
                  <div className="card-title">
                    <span className="square-icon">
                      <Lightbulb size={18} />
                    </span>
                    <span>Today’s focus</span>
                    <Badge tone="neutral">COACHING</Badge>
                  </div>
                  <h3>
                    Ask about the home.
                    <br />
                    Before the screen.
                  </h3>
                  <p>“Does sunlight fall on your TV during the day?”</p>
                  <div className="focus-reason">
                    <Sparkles size={16} />
                    <span>
                      A simple question that helps you explain brightness and
                      reflections with purpose.
                    </span>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => nav("training")}
                  >
                    Build your skills <ArrowUpRight size={16} />
                  </button>
                </section>
              </div>
              <div className="stats-grid">
                {[
                  [
                    Users,
                    "Active conversations",
                    data.customers.filter((c: any) => c.stage !== "closed")
                      .length,
                    "Every customer, one saved journey",
                    "violet",
                  ],
                  [
                    Package,
                    "TVs available",
                    data.products.reduce((n: number, p: any) => n + p.stock, 0),
                    `${data.products.length} models across 4 brands`,
                    "green",
                  ],
                  [
                    Clock,
                    "Follow-ups to make",
                    data.tasks.filter((t: any) => t.status !== "completed")
                      .length,
                    `${overdue.length} need your attention`,
                    "orange",
                  ],
                  [
                    GraduationCap,
                    "Practice accuracy",
                    data.attempts.length
                      ? Math.round(
                          (data.attempts.filter((a: any) => a.correct).length /
                            data.attempts.length) *
                            100,
                        ) + "%"
                      : "—",
                    `${data.attempts.length} questions attempted`,
                    "blue",
                  ],
                ].map(([Icon, title, value, sub, tone]: any) => (
                  <section key={title} className="stat-card">
                    <div>
                      <span className={`stat-icon ${tone}`}>
                        <Icon size={19} />
                      </span>
                      <ArrowUpRight size={15} />
                    </div>
                    <span>{title}</span>
                    <strong>{value}</strong>
                    <small>{sub}</small>
                  </section>
                ))}
              </div>
              <div className="lower-grid">
                <section className="panel">
                  <div className="section-header">
                    <div>
                      <h2>Pick up the conversation</h2>
                      <p>A familiar face. The next right step.</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => nav("customers")}
                    >
                      All customers <ArrowRight size={15} />
                    </button>
                  </div>
                  {data.customers.slice(0, 3).map((c: any, i: number) => (
                    <button
                      key={c.id}
                      className="customer-row"
                      onClick={() => open(c)}
                    >
                      <span className={`customer-avatar color-${i % 3}`}>
                        {c.name[0]}
                      </span>
                      <div>
                        <b>
                          {c.serial}. {c.name}
                        </b>
                        <span>{c.home.use || "Let’s understand the home"}</span>
                      </div>
                      <Badge tone={c.confirmed ? "green" : "neutral"}>
                        {LABELS[c.stage]}
                      </Badge>
                      <ArrowUpRight size={17} />
                    </button>
                  ))}
                  {!data.customers.length && (
                    <Empty title="Your next conversation starts here">
                      Add a customer to begin.
                    </Empty>
                  )}
                </section>
                <section className="panel next-card">
                  <div className="section-header">
                    <h2>A little learning goes a long way.</h2>
                    <span className="stat-icon violet">
                      <GraduationCap size={21} />
                    </span>
                  </div>
                  <p>
                    A few minutes. A sharper conversation.
                    <br />
                    Practise home questions, demos and follow-through.
                  </p>
                  <div className="learning-progress">
                    <span>
                      {
                        new Set(data.attempts.map((a: any) => a.question_id))
                          .size
                      }{" "}
                      of {data.questions.length} topics explored
                    </span>
                    <div className="progress-track">
                      <div
                        style={{
                          width: `${(new Set(data.attempts.map((a: any) => a.question_id)).size / data.questions.length) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                  <Button secondary onClick={() => nav("training")}>
                    Enter learning studio <ArrowRight size={16} />
                  </Button>
                </section>
              </div>
              <OfferSchedule offers={data.offers} />
              <div className="bottom-note">
                <ShieldCheck size={14} /> Grounded in approved facts. Guided by
                you. <span>STORE IQ · YOUR PARTNER ON THE FLOOR</span>
              </div>
            </>
          )}
          {page === "stock" && (
            <Catalogue
              data={data}
              selected={shortlist}
              setSelected={setShortlist}
              active={active}
              onCompare={() => nav("compare")}
              onBack={() => nav("chat")}
              onDetails={(p: any) => setModal({ type: "product", product: p })}
              onSelect={async () => {
                const c = await act("select", { products: shortlist });
                if (c) nav("chat");
              }}
            />
          )}
          {page === "customers" && (
            <>
              <Heading
                eyebrow="EVERY VISIT MATTERS"
                title="Your customers"
                subtitle="The same customer, the whole conversation. Pick up where you left off."
                action={
                  <Button onClick={newCustomer}>
                    <Plus size={16} />
                    New customer
                  </Button>
                }
              />
              <DateFilters
                filters={filters}
                setFilters={setFilters}
                data={data}
                onApply={(f: any) => run(() => refresh(f))}
              />
              <section className="panel">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>CUSTOMER</th>
                        <th>HOME & INTEREST</th>
                        <th>ASSOCIATE</th>
                        <th>NEXT STEP</th>
                        <th>LAST ACTIVITY · IST</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {data.customers.map((c: any) => (
                        <tr
                          key={c.id}
                          onClick={() => open(c)}
                          tabIndex={0}
                          onKeyDown={(e) => e.key === "Enter" && open(c)}
                        >
                          <td>
                            <b>
                              {c.serial}. {c.name}
                            </b>
                          </td>
                          <td>{c.home.use || "Not recorded"}</td>
                          <td>
                            {
                              data.associates.find((u: any) => u.id === c.owner)
                                ?.name
                            }
                          </td>
                          <td>
                            <Badge tone="neutral">{LABELS[c.stage]}</Badge>
                          </td>
                          <td>{date(c.updated_at)}</td>
                          <td>
                            <ArrowUpRight size={16} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!data.customers.length && (
                  <Empty title="No customers in this period">
                    Try another date range or clear the filters.
                  </Empty>
                )}
              </section>
            </>
          )}
          {page === "chat" &&
            (active ? (
              <Chat
                key={active.id}
                customer={active}
                data={data}
                busy={busy}
                run={run}
                setCustomer={setActive}
                refresh={refresh}
                act={act}
                onNavigate={nav}
                onModal={setModal}
                onNewCustomer={newCustomer}
                onOpenCustomer={(entry = "filters") => {
                  setChatEntry(entry);
                  setActive(null);
                }}
              />
            ) : (
              <ChatLobby
                initialMode={chatEntry}
                data={data}
                run={run}
                refresh={refresh}
                onOpen={open}
                onNewCustomer={newCustomer}
                onNavigate={nav}
              />
            ))}
          {page === "compare" && (
            <Comparison
              data={data}
              active={active}
              selected={shortlist}
              run={run}
              busy={busy}
              act={act}
              onNavigate={nav}
            />
          )}
          {page === "summary" &&
            (active ? (
              <Summary
                customer={active}
                run={run}
                act={act}
                setNotice={setNotice}
                onNavigate={nav}
              />
            ) : (
              <Empty title="Choose a customer first">
                Open a conversation to prepare a summary.
              </Empty>
            ))}
          {page === "tasks" && (
            <Tasks data={data} run={run} refresh={refresh} open={open} />
          )}
          {page === "training" && (
            <Training
              data={data}
              run={run}
              refresh={refresh}
              newCustomer={newCustomer}
              onNavigate={nav}
            />
          )}
          {page === "requests" && (
            <Requests
              data={data}
              active={active}
              run={run}
              refresh={refresh}
              open={open}
            />
          )}
          {page === "history" && (
            <>
              <Heading
                eyebrow="THE WHOLE STORY"
                title="Visit history"
                subtitle="Conversations, decisions and evidence, all in one place."
              />
              <DateFilters
                filters={filters}
                setFilters={setFilters}
                data={data}
                onApply={(f: any) => run(() => refresh(f))}
              />
              {active && (
                <section className="panel history-panel">
                  <div className="section-header">
                    <h2>
                      {active.serial}. {active.name}
                    </h2>
                    <Button secondary onClick={() => open(active)}>
                      Back to chat <ArrowRight size={15} />
                    </Button>
                  </div>
                  <MessageList messages={active.messages} />
                  {active.notes.map((n: any, i: number) => (
                    <div className="visit-note" key={i}>
                      <b>
                        Visit note · {n.by} · {date(n.at)}
                      </b>
                      <p>{n.text}</p>
                    </div>
                  ))}
                </section>
              )}
              <CustomerPicker
                data={data}
                open={(c: any) => open(c, "history")}
                newCustomer={newCustomer}
              />
            </>
          )}
          {page === "admin" && user.role === "admin" && (
            <Admin data={data} run={run} refresh={refresh} busy={busy} open={open} />
          )}
          {page === "notifications" && (
            <>
              <Heading
                eyebrow="STAY IN THE LOOP"
                title="Notifications"
                subtitle="Expert replies and requests stay attached to the right customer."
              />
              <section className="panel">
                {data.notifications.map((n: any) => (
                  <button
                    className="notification-row"
                    key={n.id}
                    onClick={() =>
                      run(async () => {
                        await api(`/notifications/${n.id}/read`, "POST");
                        await refresh();
                        const c = data.customers.find(
                          (c: any) => c.id === n.customer_id,
                        );
                        if (c)
                          await open(c, n.request_id ? "requests" : "chat");
                      })
                    }
                  >
                    <span className={`status-dot ${n.read ? "muted" : ""}`} />
                    <div>
                      <b>{n.title}</b>
                      <p>{date(n.created_at)}</p>
                    </div>
                    <ArrowUpRight size={17} />
                  </button>
                ))}
                {!data.notifications.length && (
                  <Empty title="You’re all caught up">
                    Notifications will appear here.
                  </Empty>
                )}
              </section>
            </>
          )}
        </main>
        <footer className="workspace-footer">
          <span>
            <span className="status-dot" /> Saved customer journeys
          </span>
          <span>
            Made for thoughtful retail. <b>storeiq</b>
          </span>
        </footer>
      </div>
      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <section
            role="dialog"
            aria-modal="true"
            className="modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-modal icon-button"
              aria-label="Close dialog"
              onClick={() => setModal(null)}
            >
              <X size={21} />
            </button>
            {modal.type === "new" && (
              <>
                <Badge>START WITH THE CUSTOMER</Badge>
                <h2>A new conversation.</h2>
                <p>
                  Give this visit a name. We’ll keep their home, preferences and
                  next steps together.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    run(async () => {
                      const c = await api("/customers", "POST", {
                        name: f.get("name"),
                      });
                      setModal(null);
                      await refresh();
                      await open(c);
                    });
                  }}
                >
                  <label>
                    Customer name <span className="muted">(optional)</span>
                    <input
                      name="name"
                      placeholder="e.g. Rahul"
                      maxLength={100}
                      autoFocus
                    />
                  </label>
                  <p className="hint">
                    Test customers only. Duplicate names get a permanent,
                    separate serial number.
                  </p>
                  <Button type="submit" disabled={busy}>
                    Start conversation <ArrowRight size={16} />
                  </Button>
                </form>
              </>
            )}
            {modal.type === "product" && (
              <ProductDetails product={modal.product} />
            )}{" "}
            {modal.type === "form" && (
              <ActionForm
                modal={modal}
                act={act}
                busy={busy}
                onClose={() => setModal(null)}
                customer={active}
                data={data}
              />
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function CustomerPicker({ data, open, newCustomer }: any) {
  return (
    <div className="customer-picker">
      {data.customers.map((c: any) => (
        <button
          key={c.id}
          className="panel picker-card"
          onClick={() => open(c)}
        >
          <span className="customer-avatar">{c.name[0]}</span>
          <h3>
            {c.serial}. {c.name}
          </h3>
          <p>{c.home.use || "Home questions pending"}</p>
          <Badge tone="neutral">{LABELS[c.stage]}</Badge>
          <ArrowUpRight size={17} />
        </button>
      ))}
      <button className="panel picker-card new-picker" onClick={newCustomer}>
        <Plus size={26} />
        <h3>New customer</h3>
        <p>A fresh home. A new possibility.</p>
      </button>
    </div>
  );
}
function DateFilters({ filters, setFilters, data, onApply }: any) {
  const day = (offset: number) =>
    new Date(Date.now() + offset * 86400000).toLocaleDateString("en-CA", {
      timeZone: "Asia/Kolkata",
    });
  return (
    <div className="filter-bar">
      <CalendarDays size={17} />
      {[
        ["Today", 0],
        ["Yesterday", -1],
      ].map(([title, offset]) => (
        <button
          key={title}
          className="filter-chip"
          onClick={() => {
            const f = {
              ...filters,
              start: day(Number(offset)),
              end: day(Number(offset)),
            };
            setFilters(f);
            onApply(f);
          }}
        >
          {title}
        </button>
      ))}
      <label className="inline-field">
        From
        <input
          aria-label="From date"
          type="date"
          value={filters.start}
          onChange={(e) => setFilters({ ...filters, start: e.target.value })}
        />
      </label>
      <label className="inline-field">
        To
        <input
          aria-label="To date"
          type="date"
          value={filters.end}
          onChange={(e) => setFilters({ ...filters, end: e.target.value })}
        />
      </label>
      {data.user.role === "admin" && (
        <select
          aria-label="Associate filter"
          value={filters.associate}
          onChange={(e) =>
            setFilters({ ...filters, associate: e.target.value })
          }
        >
          <option value="">All associates</option>
          {data.associates.map((u: any) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      )}
      <Button secondary onClick={() => onApply(filters)}>
        Apply
      </Button>
      <button
        className="text-button"
        onClick={() => {
          const f = { start: "", end: "", associate: "" };
          setFilters(f);
          onApply(f);
        }}
      >
        Clear
      </button>
      <small>Activity dates · IST</small>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

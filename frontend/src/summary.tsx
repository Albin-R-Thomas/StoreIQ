import { useEffect, useState } from "react";
import {
  Sparkles,
  ShieldCheck,
  Download,
  Link,
  ExternalLink,
} from "lucide-react";
import { api, date, money } from "./api";
import { Badge, Button, Empty, Heading, HOME, TV } from "./ui";

export function QuoteView({ quote: q }: any) {
  return (
    <div className="quote-sheet">
      <div className="quote-header">
        <div className="brand">
          <Sparkles size={22} />
          store<span>iq</span>
        </div>
        <Badge tone="neutral">{q.kind}</Badge>
      </div>
      <div className="quote-intro">
        <div className="eyebrow">A SCREEN FOR YOUR WORLD</div>
        <h1>{q.customer.name}’s TV summary</h1>
        <p>
          Prepared by {q.associate} · {date(q.generated_at)} IST · Version{" "}
          {q.version}
        </p>
      </div>
      {q.outdated && (
        <div className="warning">
          A newer visit version is available. Ask your associate for an updated
          summary before deciding.
        </div>
      )}
      <div className="summary-home">
        <div><small>Customer serial</small><b>{q.customer.serial}</b></div>
        <div><small>Contact owner</small><b>{q.contact_owner || q.associate}</b></div>
        {Object.entries(q.home).map(([k, v]) => (
          <div key={k}>
            <small>{HOME[k] || k}</small>
            <b>{String(v)}</b>
          </div>
        ))}
      </div>
      {q.site && <div className="summary-home">{Object.entries(q.site).filter(([k]) => k !== "confirmed").map(([k, v]) => <div key={k}><small>{k.replaceAll("_", " ")}</small><b>{String(v)}</b></div>)}</div>}
      {q.product && (
        <div className="summary-product">
          <TV product={q.product} />
          <div>
            <small>
              {q.product.brand} · {q.product.size}″ {q.product.panel}
            </small>
            <h2>{q.product.model}</h2>
            <p>
              {q.product.refresh_rate} Hz · {q.product.os}
            </p>
            {q.demo && <p>Customer’s preference: {q.demo.reason}</p>}
          </div>
        </div>
      )}
      {q.compared?.length > 0 && (
        <p className="hint">
          Compared:{" "}
          {q.compared
            .map(
              (p: any) => `${p.brand} ${p.model} (${p.size} inch ${p.panel})`,
            )
            .join(" · ")}
        </p>
      )}
      <h3>Your solution, item by item.</h3>
      {q.lines.map((l: any, i: number) => (
        <div className="quote-line" key={i}>
          <span>{l.label}</span>
          {l.description && <small>{l.description}</small>}
          <b>{money(l.amount)}</b>
        </div>
      ))}
      <div className="quote-total">
        <span>{q.total === null ? "Known subtotal" : "Payable total"}</span>
        <strong>{money(q.total ?? q.subtotal)}</strong>
      </div>
      <p className="hint">Required items: {money(q.required_total ?? q.subtotal)} · Optional items: {money(q.optional_total ?? 0)}</p>
      {q.missing.length > 0 && (
        <div className="warning">
          <b>Final total pending</b>
          {q.missing.map((s: string) => (
            <p key={s}>{s}</p>
          ))}
        </div>
      )}
      {q.offer && (
        <div className="summary-offer">
          <b>{q.offer.title}</b>
          <p>{q.offer.conditions}</p>
          <small>
            Valid {q.offer.starts_on} – {q.offer.ends_on}. Synthetic terms.
          </small>
        </div>
      )}
      {q.finance && (
        <div className="summary-offer">
          <b>Full finance cost</b>
          <p>
            Upfront {money(q.finance.upfront)} + {q.finance.months} EMIs of{" "}
            {money(q.finance.emi)} + fees {money(q.finance.fees)} ={" "}
            {money(q.finance.total)}. APR {q.finance.apr}%. {q.finance.status}.
          </p>
        </div>
      )}
      {q.tasks?.length > 0 && (
        <>
          <h3>We stay with you until it works.</h3>
          {q.tasks.map((t: any, i: number) => (
            <div className="quote-line" key={i}>
              <span>
                {t.kind.replaceAll("_", " ")} · {t.assigned_to}
              </span>
              <Badge tone={t.status === "completed" ? "green" : "neutral"}>
                {t.status} · {date(t.due_at)}
              </Badge>
            </div>
          ))}
        </>
      )}
      <div className="summary-footer">
        <ShieldCheck size={16} />
        <p>
          Synthetic contest summary. No payment collected. Requested
          installation slots need confirmation.{" "}
          {q.kind.startsWith("Quote")
            ? "This quote is not a confirmed purchase."
            : ""}
        </p>
      </div>
    </div>
  );
}

export function Summary({ customer: c, run, act, setNotice, onNavigate }: any) {
  const [quote, setQuote] = useState<any>(null),
    [link, setLink] = useState(""),
    [preview, setPreview] = useState<any>(null),
    [recipient, setRecipient] = useState("");
  useEffect(() => {
    setPreview(null); setLink(""); setQuote(null);
    api(`/customers/${c.id}/summary`)
      .then(setQuote)
      .catch(() => {});
  }, [c.id, c.version]);
  if (!quote) return <div className="loading">Preparing summary…</div>;
  return (
    <>
      <Heading
        eyebrow="EVERY DETAIL. CLEARLY SHARED."
        title="The complete picture."
        subtitle="Review the quote and consent before creating a customer-safe link."
        action={
          <Button
            secondary
            onClick={() =>
              window.open(
                `/api/customers/${c.id}/summary.pdf`,
                "_blank",
                "noopener",
              )
            }
          >
            <Download size={16} />
            Generate & download PDF
          </Button>
        }
      />
      <div className="summary-layout">
        <QuoteView quote={quote} />
        <aside className="summary-actions panel">
          <h3>One clear next step.</h3>
          <p>
            Promotions{" "}
            {c.confirmed && c.demo
              ? "unlocked after assessment and demo."
              : "locked until assessment and physical demo are complete."}
          </p>
          {!c.sale && (
            <>
              <Button secondary onClick={() => onNavigate("chat")}>
                Complete site check in chat
              </Button>
              <Button
                secondary
                onClick={() => act("payment", { method: "full" })}
              >
                Pay in full preference
              </Button>
              <Button
                secondary
                onClick={() => act("payment", { method: "finance" })}
              >
                Finance preference
              </Button>
              {c.payment && (
                <Button
                  onClick={() => {
                    if (
                      confirm(
                        "Confirm this synthetic sale at " +
                          money(quote.finance?.total ?? quote.total) +
                          "? No real payment is taken.",
                      )
                    )
                      act("sale", {
                        confirmed_total: quote.finance?.total ?? quote.total,
                      });
                  }}
                >
                  Confirm test sale
                </Button>
              )}
            </>
          )}
          <hr />
          {c.sale && <Button secondary onClick={() => { const reason = prompt("Describe the purchase correction for the store manager (at least 10 characters). Confirmed amounts remain frozen pending review."); if (reason) act("correction", {reason}); }}>Request purchase correction</Button>}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={c.consent}
              onChange={(e) => act("consent", { given: e.target.checked })}
            />
            Customer consented to share summary and updates
          </label>
          <label>Test recipient<input value={recipient} onChange={e => { setRecipient(e.target.value); setPreview(null); }} placeholder="Test recipient name or address" /></label>
          <Button
            secondary
            disabled={!c.consent || recipient.trim().length < 3}
            onClick={() => run(async () => {
              const p = await api(`/customers/${c.id}/share-preview`, "POST", {action: "preview", version: c.version, data: {recipient}});
              setPreview(p);
            })}
          >
            <Link size={16} />
            Preview share
          </Button>
          {preview && (
            <div className="share-preview">
              <p>Simulated test share to: {preview.recipient}. PDF version {preview.version} generated. Review the summary shown alongside before confirming.</p>
              <b>Share {c.name}’s summary</b>
              <p>
                Version {c.version}. Includes home needs, chosen TV, charges and
                handover status. Link expires in 7 days. Anyone with it can
                view.
              </p>
              <Button
                onClick={() =>
                  run(async () => {
                    const r = await api(`/customers/${c.id}/share`, "POST", {
                      action: "share",
                      version: c.version,
                      data: { confirmed: true, preview_id: preview.id },
                    });
                    setLink(location.origin + r.path);
                    setPreview(null);
                  })
                }
              >
                Confirm & create link
              </Button>
              <button className="text-button" onClick={() => setPreview(null)}>
                Cancel
              </button>
            </div>
          )}
          {link && (
            <div className="share-result">
              <label>
                Shareable link
                <input readOnly value={link} />
              </label>
              <Button
                secondary
                onClick={() =>
                  run(async () => {
                    await navigator.clipboard.writeText(link);
                    setNotice("Link copied");
                  })
                }
              >
                Copy link
              </Button>
              <a href={link} target="_blank" rel="noreferrer">
                Preview customer view <ExternalLink size={13} />
              </a>
            </div>
          )}
          <button
            className="text-button danger"
            onClick={() =>
              run(async () => {
                await api(`/customers/${c.id}/share`, "DELETE");
                setLink("");
              }, "All summary links revoked")
            }
          >
            Revoke existing links
          </button>
          <p className="hint">
            Sharing creates a snapshot. Later changes are labelled outdated;
            generate a fresh link after review.
          </p>
          <Button secondary onClick={() => onNavigate("chat")}>
            Back to chat
          </Button>
        </aside>
      </div>
    </>
  );
}

export function Shared({ token }: any) {
  const [q, setQ] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/shared/" + token)
      .then(setQ)
      .catch((e) => setError(e.message));
  }, [token]);
  return (
    <div className="public-summary">
      {error ? (
        <Empty title="Summary unavailable">{error}</Empty>
      ) : q ? (
        <>
          <div className="public-toolbar">
            <span>YOUR STORE IQ SUMMARY</span>
            <Button secondary onClick={() => window.print()}>
              <Download size={15} />
              Save as PDF
            </Button>
          </div>
          <QuoteView quote={q} />
        </>
      ) : (
        <div className="loading">Opening your summary…</div>
      )}
    </div>
  );
}

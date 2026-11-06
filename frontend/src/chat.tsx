import { UserRound, Sparkles, Check, LoaderCircle } from "lucide-react";
import { date, money } from "./api";
import { Badge, Button, Sources, HOME, ReplyButtons } from "./ui";
import { local } from "./locale";
import { MessageText } from "./message-text";

export function MessageList({
  messages,
  activeMessageId,
  buttons,
  onChoose,
  busy = false,
}: any) {
  return (
    <div className="messages">
      {messages.map((m: any) => (
        <div className={`message ${m.role}`} key={m.id}>
          {m.role !== "user" && m.role !== "event" && (
            <span className="message-avatar">
              {m.role === "admin" ? (
                <UserRound size={15} />
              ) : (
                <Sparkles size={15} />
              )}
            </span>
          )}
          <div className="message-content">
            <div className="message-meta">
              {m.role === "assistant"
                ? "STORE IQ"
                : m.role === "admin"
                  ? `Answered by ${m.actor}`
                  : m.role === "event"
                    ? "VISIT UPDATE"
                    : m.actor || "YOU"}{" "}
              <span>{date(m.created_at)}</span>
            </div>
            <div className="message-bubble"><MessageText text={m.text} /></div>
            {m.share?.path && <div className="message-share"><MessageText text={m.share.path} /></div>}
            <Sources sources={m.sources} trace={m.trace} />
            {(m.id === activeMessageId || m.buttons?.length > 0) && (
              <ReplyButtons
                buttons={m.id === activeMessageId ? buttons : m.buttons}
                onChoose={onChoose}
                disabled={busy || m.id !== activeMessageId}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ActionForm({
  modal,
  act,
  busy,
  onClose,
  customer: c,
  data,
}: any) {
  const t = (value: string) => local(c.language, value);
  return (
    <>
      <Badge>RECORD THE REAL ACTION</Badge>
      <h2>{modal.title}</h2>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          let values: any = Object.fromEntries(f);
          if (modal.action === "home") values = { home: values };
          if (modal.action === "followup")
            values = {
              ...values,
              consent: f.get("consent") === "on",
              due_at: new Date(String(f.get("due_at"))).toISOString(),
            };
          if (modal.action === "extras")
            values = { extras: f.getAll("extras") };
          const result = await act(modal.action, values);
          if (result) onClose();
        }}
      >
        {modal.action === "home" &&
          Object.entries(HOME).map(([k, label]) => (
            <label key={k}>
              {t(label)}
              <input
                name={k}
                defaultValue={c.home[k] || ""}
                required
                maxLength={500}
                placeholder={
                  k === "budget"
                    ? "e.g. 50000–70000"
                    : t("Their answer, or Unknown")
                }
              />
            </label>
          ))}
        {modal.action === "demo" && (
          <>
            <p>
              Confirm only after showing the actual TVs at matched settings.
            </p>
            <label>
              Customer’s preferred TV
              <select name="preferred" required>
                {c.selected.map((id: string) => {
                  const p = data.products.find((p: any) => p.id === id);
                  return (
                    <option key={id} value={id}>
                      {p?.brand} {p?.model}
                    </option>
                  );
                })}
              </select>
            </label>
            <label>
              {t("What difference did the customer prefer?")}
              <textarea
                name="reason"
                minLength={5}
                required
                placeholder="e.g. Sharper cricket motion from the side seat"
              />
            </label>
          </>
        )}
        {modal.action === "start_demo" && <label>{t("What difference still needs checking?")}<input name="focus" required maxLength={500} placeholder="Dialogue, gaming, motion, reflections or side seats" /></label>}
        {modal.action === "demo_unavailable" && (
          <label>
            {t("Why could the physical demo not be completed?")}
            <textarea
              name="reason"
              minLength={3}
              maxLength={1000}
              required
              placeholder="e.g. This display model is unavailable"
            />
          </label>
        )}
        {modal.action === "site" && (
          <>
            <label>
              {t("Placement")}
              <select
                name="placement"
                defaultValue={c.site.placement || ""}
                required
              >
                <option value="">{t("Choose")}</option>
                <option>Wall</option>
                <option>Table</option>
              </select>
            </label>
            <label>
              {t("Specialist drilling or structural work needed?")}
              <select
                name="specialist"
                defaultValue={c.site.specialist || ""}
                required
              >
                <option value="">{t("Choose")}</option>
                <option value="no">{t("No — standard installation confirmed")}</option>
                <option value="yes">{t("Yes — charge needs confirmation")}</option>
                <option value="unknown">{t("Unknown — finalisation pending")}</option>
              </select>
            </label>
            {[["power", "Power socket"], ["cable_route", "Cable route"], ["access", "Wall and access"], ["devices", "Connected devices"]].map(([key, label]) => (
              <label key={key}>{t(label)}<input name={key} required defaultValue={c.site[key] || ""} placeholder={t("Record the check, or Unknown")} /></label>
            ))}
            <label>
              {t("Power, cable route, wall/access & devices")}
              <textarea
                name="notes"
                defaultValue={c.site.notes || ""}
                required
                minLength={5}
              />
            </label>
          </>
        )}
        {modal.action === "extras" && (
          <>
            <p>Offer optional extras only when they help this customer.</p>
            {[
              ["soundbar", "2.1 soundbar", money(data.commercial[0].soundbar)],
              [
                "protection",
                "2-year protection plan",
                money(data.commercial[0].protection),
              ],
            ].map(([id, label, price]) => (
              <label key={id} className="extra-option">
                <input
                  type="checkbox"
                  name="extras"
                  value={id}
                  defaultChecked={c.extras.includes(id)}
                />
                <span>
                  <b>{label}</b>
                  <small>{price} · Optional. {data.commercial[0][id + "_description"] || (id === "protection" ? "Coverage, exclusions, provider and claims procedure not confirmed; ask admin before recommending." : "Check dialogue needs and device compatibility before adding.")}</small>
                </span>
              </label>
            ))}
          </>
        )}
        {modal.action === "followup" && (
          <>
            <label>
              {t("What is pending?")}
              <textarea name="reason" required minLength={3} />
            </label>
            <label>
              {t("Agreed date & time (local timezone)")}
              <input type="datetime-local" name="due_at" required />
            </label>
            <label>
              {t("Owner")}
              <input name="owner" defaultValue={data.user.name} required />
            </label>
            <label className="checkbox-label">
              <input type="checkbox" name="consent" />
              {t("Customer agreed to follow-up contact")}
            </label>
            <p className="hint">
              Without consent this stays internal. A due time is not a promise
              of an expert answer.
            </p>
          </>
        )}
        {modal.action === "note" && (
          <label>
            {t("Visit note")}
            <textarea name="text" required maxLength={3000} />
          </label>
        )}
        <div className="form-actions">
          <Button secondary onClick={onClose}>
            {t("Cancel")}
          </Button>
          <Button type="submit" disabled={busy}>
            {t("Save")}{" "}
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Check size={16} />
            )}
          </Button>
        </div>
      </form>
    </>
  );
}

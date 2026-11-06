import { Check, Sparkles, ShieldCheck } from "lucide-react";
export const HOME: Record<string, string> = {
  distance: "Viewing distance",
  light: "Room light",
  use: "Main use",
  seating: "Seating",
  problem: "Current frustration",
  placement: "Placement & space",
  budget: "Comfortable budget",
};
export const STAGES = [
  "assess",
  "recommend",
  "demo",
  "complete",
  "close",
  "handover",
  "review",
  "closed",
];
export const LABELS: Record<string, string> = {
  assess: "Understand the home",
  recommend: "Find the right fit",
  demo: "Show the difference",
  complete: "Complete solution",
  close: "Offer & payment",
  handover: "Delivery & installation",
  review: "Visit review",
  closed: "Working check complete",
};
export function Button({
  children,
  onClick,
  secondary = false,
  disabled = false,
  className = "",
  type = "button",
}: any) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${secondary ? "button secondary" : "button"} ${className}`}
    >
      {children}
    </button>
  );
}
export function Badge({ children, tone = "green" }: any) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Empty({ title, children }: any) {
  return (
    <div className="empty">
      <Sparkles size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Heading({ eyebrow, title, subtitle, action }: any) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
export function TV({ product: p, large = false }: any) {
  return (
    <div className={`tv-stage ${p.scene} ${large ? "large" : ""}`}>
      <div className="tv-body">
        <div className="tv-screen">
          <div className="scene-light" />
          <div className="scene-ridge ridge-back" />
          <div className="scene-ridge ridge-front" />
          <span className="scene-caption">
            {p.panel === "OLED"
              ? "EVERY SHADE. EVERY DETAIL."
              : "CLOSER TO EXTRAORDINARY."}
          </span>
        </div>
        <div className="tv-brand">{p.brand}</div>
      </div>
      <div className="tv-foot" />
      <span className="tv-size">{p.size}″</span>
    </div>
  );
}
export function Sources({ sources, trace }: any) {
  if (!sources?.length && !trace) return null;
  return (
    <details className="sources">
      <summary>
        <ShieldCheck size={13} /> {sources?.length || 0} supporting sources{" "}
        {trace && <span>· {trace.mode?.replaceAll("_", " ")}</span>}
      </summary>
      {trace?.query && <p>Query: {trace.query}</p>}
      {sources?.map((s: any) => (
        <div key={s.id}>
          <strong>{s.title}</strong>
          <p>{s.text}</p>
          <small>
            Reference: {s.id} · relevance {s.score}
          </small>
        </div>
      ))}
    </details>
  );
}

export function ReplyButtons({ buttons, onChoose, disabled = false }: any) {
  return (
    <div className="reply-buttons">
      {(buttons || []).slice(0, 3).map((b: any) => (
        <button
          key={`${b.kind}-${b.name}-${b.label}`}
          disabled={disabled}
          onClick={() => onChoose?.(b)}
        >
          <span>{b.label}</span>
          <Check size={12} />
        </button>
      ))}
    </div>
  );
}

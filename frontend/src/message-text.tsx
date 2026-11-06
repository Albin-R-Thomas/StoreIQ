const LINK_CANDIDATE = /(https?:\/\/[^\s<>"']+|\/api\/customers\/[A-Za-z0-9_-]+\/summary\.pdf(?:\?[^\s<>"']*)?|\/share\/[A-Za-z0-9_-]+)/g;

export function summaryLink(value: string, origin: string) {
  try {
    const url = new URL(value, origin);
    if (url.origin !== origin || !["http:", "https:"].includes(url.protocol)) return null;
    const pdf = /^\/api\/customers\/[A-Za-z0-9_-]+\/summary\.pdf$/.test(url.pathname);
    const share = /^\/share\/[A-Za-z0-9_-]+$/.test(url.pathname);
    if (!pdf && !share) return null;
    return { href: url.pathname + url.search + url.hash, pdf };
  } catch {
    return null;
  }
}

export function MessageText({ text, origin = window.location.origin }: { text: string; origin?: string }) {
  return <>{text.split(LINK_CANDIDATE).map((part, index) => {
    if (index % 2 === 0) return part;
    const candidate = part.replace(/[),.;!]+$/, "");
    const link = summaryLink(candidate, origin);
    if (!link) return part;
    return <span key={index}><a className="message-summary-link" href={link.href} target="_blank" rel="noopener noreferrer" download={link.pdf || undefined}>{link.pdf ? "Download summary PDF" : "Open shared summary"}</a>{part.slice(candidate.length)}</span>;
  })}</>;
}

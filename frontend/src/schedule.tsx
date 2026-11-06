import { CalendarDays, ArrowUpRight } from "lucide-react";
import { Badge } from "./ui";
export function OfferSchedule({ offers }: any) {
  const today = new Date().toLocaleDateString("en-CA", {
    timeZone: "Asia/Kolkata",
  });
  return (
    <section className="panel offer-schedule">
      <div>
        <CalendarDays size={18} />
        <h3>On the store calendar</h3>
        <span>Offer details unlock after assessment and demo.</span>
      </div>
      {offers.map((o: any) => {
        const days = Math.ceil(
          (Date.parse(o.starts_on) - Date.parse(today)) / 86400000,
        );
        return (
          <div className="schedule-row" key={o.id}>
            <b>{o.title}</b>
            <small>
              {o.starts_on} — {o.ends_on}
            </small>
            <Badge tone={days > 0 ? "orange" : "green"}>
              {days > 0
                ? `In ${days} days`
                : o.ends_on < today
                  ? "Ended"
                  : "Running now"}
            </Badge>
          </div>
        );
      })}
    </section>
  );
}

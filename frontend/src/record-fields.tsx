export function RecordFields({ json, setJson }: any) {
  let draft: any;
  try {
    draft = JSON.parse(json);
  } catch {
    return (
      <p className="hint">Correct the advanced record JSON to use the form.</p>
    );
  }
  const names: Record<string, string> = {
    price: "Price (INR)",
    stock: "Available units",
    expected_on: "Expected arrival date",
    refresh_rate: "Native refresh (Hz)",
    brightness: "Brightness (nits)",
    sound: "Sound output (W)",
    specialist_work: "Specialist charge (INR, blank = unconfirmed)",
    finance_months: "EMI count",
    finance_fee: "Finance fee (INR)",
    min_size: "Minimum size (inches)",
    starts_on: "Offer starts",
    ends_on: "Offer ends",
    wall_mount: "Wall mount (INR)",
  };
  const change = (key: string, value: any) =>
    setJson(JSON.stringify({ ...draft, [key]: value }, null, 2));
  const options: Record<string, string[]> = {
    panel: ["LED", "QLED", "OLED", "Mini LED"],
    viewing_angle: ["wide", "standard"],
  };
  return (
    <div className="record-fields">
      {Object.entries(draft)
        .filter(
          ([k]) =>
            !["id", "version", "mock", "scene", "finance_apr"].includes(k),
        )
        .map(([key, value]) => (
          <label
            key={key}
            className={
              [
                "text",
                "description",
                "conditions",
                "features",
                "warranty",
              ].includes(key)
                ? "wide-field"
                : ""
            }
          >
            {names[key] || key.replaceAll("_", " ")}
            {options[key] ? (
              <select
                value={String(value)}
                onChange={(e) => change(key, e.target.value)}
              >
                {options[key].map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            ) : ["text", "description", "conditions", "warranty"].includes(
                key,
              ) ? (
              <textarea
                value={String(value)}
                onChange={(e) => change(key, e.target.value)}
              />
            ) : Array.isArray(value) ? (
              <input
                key={`${draft.id}-${key}`}
                defaultValue={value.join(", ")}
                onBlur={(e) =>
                  change(
                    key,
                    e.target.value
                      .split(",")
                      .map((v) => v.trim())
                      .filter(Boolean),
                  )
                }
              />
            ) : (
              <input
                type={
                  typeof value === "number" || key === "specialist_work"
                    ? "number"
                    : key.endsWith("_on")
                      ? "date"
                      : "text"
                }
                min={typeof value === "number" ? 0 : undefined}
                value={
                  Array.isArray(value)
                    ? value.join(", ")
                    : value === null
                      ? ""
                      : String(value)
                }
                onChange={(e) =>
                  change(
                    key,
                    Array.isArray(value)
                      ? e.target.value
                          .split(",")
                          .map((v) => v.trim())
                          .filter(Boolean)
                      : typeof value === "number"
                        ? Number(e.target.value)
                        : key === "specialist_work"
                          ? e.target.value
                            ? Number(e.target.value)
                            : null
                          : key === "expected_on"
                            ? e.target.value || null
                            : e.target.value,
                  )
                }
              />
            )}
          </label>
        ))}
    </div>
  );
}

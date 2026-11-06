import { useEffect, useState } from "react";
import {
  Search,
  SlidersHorizontal,
  Check,
  ArrowRight,
  ArrowUpRight,
  GitCompareArrows,
  Sparkles,
  LoaderCircle,
  Heart,
  Monitor,
} from "lucide-react";
import { api, money } from "./api";
import { Badge, Button, Empty, Heading, TV, Sources } from "./ui";

export function Catalogue({
  data,
  selected,
  setSelected,
  active,
  onCompare,
  onDetails,
  onSelect,
  onBack,
}: any) {
  const [search, setSearch] = useState(""),
    [brand, setBrand] = useState("All brands"),
    [size, setSize] = useState(""),
    [stock, setStock] = useState(false),
    [price, setPrice] = useState(""),
    [feature, setFeature] = useState("");
  const products = data.products.filter(
    (p: any) =>
      (brand === "All brands" || p.brand === brand) &&
      (!size || p.size === Number(size)) &&
      (!stock || p.stock > 0) &&
      (!price || p.price <= Number(price)) &&
      (!feature || p.features.some((f: string) => f.includes(feature))) &&
      `${p.brand} ${p.model} ${p.panel}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <Heading
        eyebrow="FIND THEIR NEXT SCREEN"
        title="A screen for every home."
        subtitle="Explore the details. Know what’s available. Recommend with a reason."
        action={
          <div className="chat-title-actions">
            {onBack && (
              <Button secondary onClick={onBack}>
                Back to chat
              </Button>
            )}
            <Badge tone="neutral">
              {data.products.length} MODELS · DEMO CATALOGUE
            </Badge>
          </div>
        }
      />
      <div className="catalogue-toolbar">
        <div className="search-field">
          <Search size={18} />
          <input
            aria-label="Search TVs"
            placeholder="Search a brand, model or display…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="brand-tabs">
          {["All brands", "Samsung", "LG", "Sony", "TCL"].map((b) => (
            <button
              onClick={() => setBrand(b)}
              className={brand === b ? "active" : ""}
              key={b}
            >
              {b}
            </button>
          ))}
        </div>
      </div>
      <div className="filter-bar">
        <SlidersHorizontal size={16} />
        <select
          aria-label="Screen size"
          value={size}
          onChange={(e) => setSize(e.target.value)}
        >
          <option value="">Screen size</option>
          {[43, 55, 65].map((s) => (
            <option key={s} value={s}>
              {s} inch
            </option>
          ))}
        </select>
        <select
          aria-label="Maximum price"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        >
          <option value="">Any price</option>
          {[40000, 70000, 100000, 150000].map((p) => (
            <option key={p} value={p}>
              Under {money(p)}
            </option>
          ))}
        </select>
        <select
          aria-label="Feature"
          value={feature}
          onChange={(e) => setFeature(e.target.value)}
        >
          <option value="">All features</option>
          {["VRR", "HDMI 2.1", "Dolby Vision", "ALLM"].map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={stock}
            onChange={(e) => setStock(e.target.checked)}
          />
          In stock only
        </label>
        <span className="toolbar-count">{products.length} matching TVs</span>
      </div>
      <div className="product-grid">
        {products.map((p: any) => (
          <article
            key={p.id}
            className={`product-card ${selected.includes(p.id) ? "selected" : ""}`}
          >
            <button
              className="product-image"
              onClick={() => onDetails(p)}
              aria-label={"View " + p.model}
            >
              <TV product={p} />
              <Badge tone={p.stock ? "light" : "orange"}>
                {p.stock ? "Available in store" : "Arriving " + p.expected_on}
              </Badge>
            </button>
            <div className="product-info">
              <div className="product-brand">
                {p.brand.toUpperCase()}
                <span>{p.size}″ · 4K UHD</span>
              </div>
              <h3>{p.model}</h3>
              <p>
                {p.panel} · {p.refresh_rate} Hz · {p.os}
              </p>
              <div className="feature-tags">
                {p.features.slice(0, 3).map((f: string) => (
                  <span key={f}>{f}</span>
                ))}
              </div>
              <div className="product-price">
                <strong>{money(p.price)}</strong>
                <span>
                  <span className={`status-dot ${!p.stock ? "amber" : ""}`} />
                  {p.stock ? `${p.stock} in stock` : "Out of stock"}
                </span>
              </div>
              <div className="product-actions">
                <button
                  className={`compare-toggle ${selected.includes(p.id) ? "checked" : ""}`}
                  disabled={!selected.includes(p.id) && selected.length >= 3}
                  onClick={() =>
                    setSelected(
                      selected.includes(p.id)
                        ? selected.filter((s: string) => s !== p.id)
                        : [...selected, p.id],
                    )
                  }
                >
                  <span>{selected.includes(p.id) && <Check size={12} />}</span>
                  Compare
                </button>
                <button className="text-button" onClick={() => onDetails(p)}>
                  Full specs <ArrowUpRight size={15} />
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
      {!products.length && (
        <Empty title="No matching screens">
          Adjust the filters to explore more options.
        </Empty>
      )}
      {selected.length > 0 && (
        <div className="compare-dock">
          <GitCompareArrows size={20} />
          <div>
            <b>
              {selected.length} TV{selected.length > 1 ? "s" : ""} selected
            </b>
            <small>
              {selected
                .map(
                  (id: string) =>
                    data.products.find((p: any) => p.id === id)?.model,
                )
                .join(" · ")}
            </small>
          </div>
          <button className="text-button" onClick={() => setSelected([])}>
            Clear
          </button>
          {active && (
            <Button secondary onClick={onSelect}>
              Save to {active.name}
            </Button>
          )}
          <Button disabled={selected.length < 2} onClick={onCompare}>
            Compare screens <ArrowRight size={16} />
          </Button>
        </div>
      )}
    </>
  );
}

export function ProductDetails({ product: p }: any) {
  return (
    <>
      <TV product={p} large />
      <div className="eyebrow">{p.brand} · SYNTHETIC SPECIFICATIONS</div>
      <h2>
        {p.model} <span className="muted">{p.size}″</span>
      </h2>
      <p>{p.description}</p>
      <div className="detail-price">
        {money(p.price)} <Badge>{p.stock} available</Badge>
      </div>
      <div className="spec-grid">
        {[
          ["Display", p.panel],
          ["Resolution", p.resolution],
          ["Native refresh", p.refresh_rate + " Hz"],
          ["Brightness", p.brightness + " nits"],
          ["Sound", p.sound + " W"],
          ["Platform", p.os],
          ["HDMI ports", p.hdmi_ports],
          ["Side seating", p.viewing_angle],
          ["Features", p.features.join(", ")],
          ["Warranty", p.warranty],
        ].map(([k, v]) => (
          <div key={k}>
            <small>{k}</small>
            <b>{v}</b>
          </div>
        ))}
      </div>
      <p className="hint">
        Demonstration data; these are not official manufacturer specifications.
        Offers unlock only after assessment and a physical demo.
      </p>
    </>
  );
}

export function Comparison({
  data,
  active,
  selected,
  run,
  busy,
  act,
  onNavigate,
}: any) {
  const [result, setResult] = useState<any>(null);
  useEffect(() => {
    setResult(null);
  }, [selected.join(","), active?.id]);
  const products = selected
    .map((id: string) => data.products.find((p: any) => p.id === id))
    .filter(Boolean);
  return (
    <>
      <Heading
        eyebrow="MAKE THE DIFFERENCE VISIBLE"
        title="Side by side. Home in mind."
        subtitle={
          active
            ? `Comparing for ${active.name} · ${active.home.use || "Needs to discuss"}`
            : "Choose two or three TVs. Add a customer for a verdict tailored to their home."
        }
        action={
          <Button secondary onClick={() => onNavigate("stock")}>
            Change TVs <Monitor size={16} />
          </Button>
        }
      />
      {products.length < 2 ? (
        <Empty title="Choose at least two screens">
          Select TVs in the catalogue to see the differences that matter.
        </Empty>
      ) : (
        <>
          <div className="comparison-table panel">
            <div
              className="compare-products"
              style={{
                gridTemplateColumns: `180px repeat(${products.length},1fr)`,
              }}
            >
              <div className="compare-label">
                <Sparkles size={26} />
                <h3>
                  The details.
                  <br />
                  The difference.
                </h3>
                <p>All specifications are synthetic contest data.</p>
              </div>
              {products.map((p: any) => (
                <div key={p.id}>
                  <TV product={p} />
                  <small>{p.brand}</small>
                  <h3>{p.model}</h3>
                  <strong>{money(p.price)}</strong>
                  <Badge tone={p.stock ? "green" : "orange"}>
                    {p.stock ? `${p.stock} in store` : "Stock pending"}
                  </Badge>
                  {active && (
                    <button
                      className="text-button"
                      disabled={!active.selected.includes(p.id)}
                      onClick={() => act("preferred", { product: p.id })}
                    >
                      Prefer this TV <Heart size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            {[
              ["Screen size", "size", " inch"],
              ["Display", "panel", ""],
              ["Native refresh", "refresh_rate", " Hz"],
              ["Peak brightness", "brightness", " nits"],
              ["Sound output", "sound", " W"],
              ["Smart platform", "os", ""],
              ["Viewing angle", "viewing_angle", ""],
              ["HDMI ports", "hdmi_ports", ""],
              ["Features", "features", ""],
            ].map(([label, k, suffix]) => (
              <div
                className="compare-row"
                key={k}
                style={{
                  gridTemplateColumns: `180px repeat(${products.length},1fr)`,
                }}
              >
                <b>{label}</b>
                {products.map((p: any) => (
                  <span
                    key={p.id}
                    className={
                      new Set(products.map((x: any) => String(x[k]))).size > 1
                        ? "difference"
                        : ""
                    }
                  >
                    {Array.isArray(p[k]) ? p[k].join(" · ") : p[k]}
                    {suffix}
                  </span>
                ))}
              </div>
            ))}
          </div>
          <section className="verdict-card">
            <div>
              <span className="square-icon">
                <Sparkles size={21} />
              </span>
              <div>
                <div className="eyebrow">AI VERDICT</div>
                <h2>The best fit starts with their home.</h2>
              </div>
              <Button
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    setResult(
                      await api("/comparison", "POST", {
                        customer_id: active?.id || null,
                        products: selected,
                      }),
                    );
                  })
                }
              >
                {busy ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Sparkles size={17} />
                )}
                Generate verdict
              </Button>
            </div>
            {result ? (
              <>
                <p className="verdict-text">{result.verdict.text}</p>
                <Sources
                  sources={result.verdict.sources}
                  trace={result.verdict.trace}
                />
              </>
            ) : (
              <p>
                Get a grounded recommendation, the tradeoff to explain, and the
                difference to demonstrate. You own the final choice.
              </p>
            )}
            <p className="hint">
              A comparison does not complete a physical demo. Save the shortlist
              to the customer before recording a demo.
            </p>
            {active && (
              <Button
                secondary
                onClick={async () => {
                  const c = await act("select", { products: selected });
                  if (c) onNavigate("chat");
                }}
              >
                Save shortlist & return to demo <ArrowRight size={16} />
              </Button>
            )}
          </section>
        </>
      )}
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import api from "./api";
import en from "./i18n/en.json";
import sw from "./i18n/sw.json";

const SW_TEXT = {
  "Data Analyst": "Mchambuzi wa Data",
  "Junior Data Analyst": "Mchambuzi wa Data wa ngazi ya mwanzo",
  Spreadsheets: "Majedwali",
  "Data Visualisation": "Uwasilishaji wa Data kwa Michoro",
  Statistics: "Takwimu",
  "Content Strategy": "Mkakati wa Maudhui",
  "Social Media": "Mitandao ya Kijamii",
  "Marketing Analytics": "Uchambuzi wa Masoko",
};
function localText(t, value) {
  return t === sw ? SW_TEXT[value] || value : value;
}
function checkpointTitle(t, value) {
  return t === sw
    ? `${localText(t, value.replace(" checkpoint", ""))} · hatua`
    : value;
}

let pathwayRequestInFlight = null;
let pathwayResponseCache = null;
function getPathways() {
  if (pathwayResponseCache) return Promise.resolve(pathwayResponseCache);
  if (!pathwayRequestInFlight) {
    const request = api.get("/pathways/").then((response) => {
      pathwayResponseCache = response;
      return response;
    });
    pathwayRequestInFlight = request;
    request.then(
      () => {
        if (pathwayRequestInFlight === request) pathwayRequestInFlight = null;
      },
      () => {
        if (pathwayRequestInFlight === request) pathwayRequestInFlight = null;
      },
    );
  }
  return pathwayRequestInFlight;
}

function App() {
  const loadLearner = useLocation().pathname !== "/catalogue";
  const [language, setLanguage] = useState(
    localStorage.getItem("somai-language") || "en",
  );
  const [learner, setLearner] = useState(null);
  const [pathways, setPathways] = useState([]);
  const [error, setError] = useState("");
  const t = language === "sw" ? sw : en;
  const refresh = useCallback(async () => {
    let pathwayRequest;
    try {
      const meRequest = api.get("/me/");
      pathwayRequest = getPathways();
      const [me, pathwayResponse] = await Promise.all([
        meRequest,
        pathwayRequest,
      ]);
      setLearner(me.data);
      setPathways(pathwayResponse.data);
      setError("");
    } catch {
      setLearner(null);
      try {
        const pathwayResponse = await pathwayRequest;
        setPathways(pathwayResponse.data);
      } catch {
        try {
          setPathways((await getPathways()).data);
        } catch {
          setPathways([]);
        }
      }
    }
  }, []);
  useEffect(() => {
    if (loadLearner) refresh();
  }, [refresh, loadLearner]);
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);
  const setLang = (value) => {
    localStorage.setItem("somai-language", value);
    setLanguage(value);
  };
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        lang={language === "sw" ? "en" : undefined}
      >
        {en.skipToContent}
      </a>
      <header className="site-header">
        <Link to="/" className="brand" aria-label="SOMA.i home">
          {t.brand}
        </Link>
        <span>{t.tagline}</span>
        <nav aria-label="Main navigation">
          <NavLink
            to="/catalogue"
            end
            lang={language === "sw" ? "en" : undefined}
          >
            {en.catalogue}
          </NavLink>
          <NavLink to="/pathway" end>
            {t.dashboard}
          </NavLink>
          <NavLink to="/items" end>
            {t.items}
          </NavLink>
          <NavLink to="/settings" end>
            {t.settings}
          </NavLink>
        </nav>
      </header>
      {error && (
        <p role="alert" className="notice">
          {t.error}
        </p>
      )}
      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route
            path="/"
            element={
              <Onboarding
                pathways={pathways}
                t={t}
                language={language}
                setLang={setLang}
                refresh={refresh}
              />
            }
          />
          <Route
            path="/pathway"
            element={
              <Dashboard
                learner={learner}
                pathways={pathways}
                refresh={refresh}
                t={t}
              />
            }
          />
          <Route path="/catalogue" element={<Catalogue t={t} />} />
          <Route path="/items" element={<ItemList t={t} />} />
          <Route path="/checkpoint/:id" element={<CheckpointPage t={t} />} />
          <Route path="/next" element={<NextPage t={t} />} />
          <Route
            path="/settings"
            element={
              <Settings
                learner={learner}
                t={t}
                language={language}
                setLang={setLang}
                refresh={refresh}
              />
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer>SOMA.i · {t.tagline}</footer>
    </div>
  );
}

function Catalogue({ t }) {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") || "";
  const rawPage = params.get("page") || "1";
  const page =
    /^[1-9]\d{0,5}$/.test(rawPage) || rawPage === "1000000"
      ? Number(rawPage)
      : 1;
  const [search, setSearch] = useState(query);
  const [state, setState] = useState({ loading: true });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setSearch(query);
  }, [query]);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setState({ loading: true });
    api
      .get("/pathways/", {
        params: { page, q: query },
        signal: controller.signal,
      })
      .then(({ data }) => {
        if (active) setState({ data });
      })
      .catch(() => {
        if (active) setState({ error: true });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [query, page, retry]);
  function navigatePage(next) {
    setParams({ ...(query ? { q: query } : {}), page: String(next) });
  }
  const data = state.data;
  return (
    <section className="stack" lang={t === sw ? "en" : undefined}>
      <div className="panel stack">
        <h1>{en.catalogue}</h1>
        <p>{en.catalogueIntro}</p>
        <form
          className="toolbar"
          onSubmit={(event) => {
            event.preventDefault();
            setParams({
              ...(search.trim() ? { q: search.trim() } : {}),
              page: "1",
            });
          }}
        >
          <label>
            {en.searchTopics}
            <input
              type="search"
              maxLength={120}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <button>{en.search}</button>
          <button
            type="button"
            className="quiet"
            onClick={() => {
              setSearch("");
              setParams({ page: "1" });
            }}
          >
            {en.clearSearch}
          </button>
        </form>
      </div>
      <div aria-live="polite" aria-atomic="true">
        {state.loading && <p role="status">{en.loading}</p>}
        {state.error && (
          <div className="panel">
            <p role="alert">{en.catalogueError}</p>
            <button onClick={() => setRetry((value) => value + 1)}>
              {en.retry}
            </button>
          </div>
        )}
        {data && (
          <p role="status">
            {data.count} {en.topicsFound} | {en.page} {data.page}
          </p>
        )}
      </div>
      {data && (
        <>
          {data.results.length === 0 && <p className="panel">{en.noTopics}</p>}
          <div className="cards catalogue-cards">
            {data.results.map((topic) => (
              <article className="panel stack" key={topic.id}>
                <h2>{topic.title}</h2>
                {topic.is_demo && <p className="eyebrow">{en.demoTopic}</p>}
                <p>{topic.description}</p>
                <p>{topic.target_outcome}</p>
                <Link
                  className="button"
                  to={`/?pathway=${topic.id}`}
                  aria-label={`${en.choosePathway}: ${topic.title}`}
                >
                  {en.choosePathway}
                </Link>
              </article>
            ))}
          </div>
          <nav className="toolbar" aria-label={en.cataloguePages}>
            <button
              className="quiet"
              disabled={page <= 1}
              onClick={() => navigatePage(page - 1)}
            >
              {en.previousPage}
            </button>
            <button
              className="quiet"
              disabled={!data.has_next}
              onClick={() => navigatePage(page + 1)}
            >
              {en.nextPage}
            </button>
          </nav>
        </>
      )}
    </section>
  );
}

function Onboarding({ pathways, t, language, setLang, refresh }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requested = params.get("pathway");
  const [selected, setSelected] = useState("");
  useEffect(() => {
    if (
      requested &&
      pathways.some((pathway) => String(pathway.id) === requested)
    ) {
      setSelected(requested);
    }
  }, [requested, pathways]);
  const [name, setName] = useState("");
  async function start(event) {
    event.preventDefault();
    try {
      await api.post("/me/", {
        display_name: name || "Learner",
        preferred_language: language,
        pathway_id: selected,
      });
      await refresh();
      navigate("/pathway");
    } catch {}
  }
  async function demo() {
    try {
      await api.post("/demo/");
      await refresh();
      navigate("/pathway");
    } catch {}
  }
  return (
    <section className="panel hero">
      <p className="eyebrow">SOMA.i</p>
      <h1>{t.onboarding}</h1>
      <p>
        {t.tagline}. {t.intro}
      </p>
      <form onSubmit={start} className="stack">
        <label>
          {t.language}
          <select value={language} onChange={(e) => setLang(e.target.value)}>
            <option value="en">English</option>
            <option value="sw">Kiswahili</option>
          </select>
        </label>
        <label>
          {t.pathway}
          <select
            required
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">—</option>
            {pathways.map((p) => (
              <option key={p.id} value={p.id}>
                {localText(t, p.title)} · {localText(t, p.target_outcome)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t.nameOptional}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength="80"
          />
        </label>
        <button disabled={!selected}>{t.start}</button>
      </form>
      <button className="quiet" onClick={demo}>
        {t.demo}
      </button>
    </section>
  );
}

function Dashboard({ learner, pathways = [], refresh, t }) {
  const [data, setData] = useState(null);
  const navigate = useNavigate();
  useEffect(() => {
    api
      .get("/dashboard/")
      .then((r) => setData(r.data))
      .catch(() => setData(null));
  }, [learner]);
  async function action(name) {
    try {
      await api.post(`/pathway/${name}/`);
      await refresh();
      setData((await api.get("/dashboard/")).data);
    } catch {}
  }
  if (!data)
    return (
      <section className="panel">
        <h1>{t.dashboard}</h1>
        <p>Choose a pathway to get started.</p>
        <Link className="button" to="/">
          {t.onboarding}
        </Link>
      </section>
    );
  return (
    <section className="stack">
      <div className="panel">
        <p className="eyebrow">{localText(t, data.pathway?.target_outcome)}</p>
        <h1>{localText(t, data.pathway?.title)}</h1>
        <label htmlFor="progress">
          {t.progress}: {data.progress_percent}%
        </label>
        <progress id="progress" max="100" value={data.progress_percent}>
          {data.progress_percent}%
        </progress>
        <p>
          {t.done}:{" "}
          {data.done.map((value) => localText(t, value)).join(", ") || "—"}
        </p>
        <p>
          {t.remaining}:{" "}
          {data.remaining.map((value) => localText(t, value)).join(", ") || "—"}
        </p>
        {data.next_checkpoint && (
          <div className="callout">
            <h2>
              {t.checkpoint}: {checkpointTitle(t, data.next_checkpoint.title)}
            </h2>
            <p>
              {t === sw
                ? "Kamilisha zoezi fupi ukitumia ujuzi huu na utafakari kuhusu ulichojifunza."
                : data.next_checkpoint.criteria}
            </p>
            <button
              onClick={() => navigate(`/checkpoint/${data.next_checkpoint.id}`)}
            >
              {t.openCheckpoint}
            </button>
          </div>
        )}
        <div className="toolbar">
          <label>
            {t.switch}
            <select
              value={data.pathway?.id || ""}
              onChange={async (e) => {
                await api.post("/pathway/switch/", {
                  pathway_id: e.target.value,
                });
                await refresh();
                setData((await api.get("/dashboard/")).data);
              }}
            >
              {pathways.map((p) => (
                <option key={p.id} value={p.id}>
                  {localText(t, p.title)}
                </option>
              ))}
            </select>
          </label>
          <button className="quiet" onClick={() => action("skip")}>
            {t.skip}
          </button>
          <button className="quiet" onClick={() => action("restart")}>
            {t.restart}
          </button>
        </div>
      </div>
      <h2>{t.lessons}</h2>
      <Cards items={data.items} t={t} />
    </section>
  );
}

function ItemProvenance({ item, t }) {
  const text = (key) => t[key] || en[key];
  const dateOnly = (value) => {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? null
      : date.toISOString().slice(0, 10);
  };
  const contentDate =
    item.date_source === "published" || item.date_source === "updated"
      ? dateOnly(item.content_date)
      : null;
  const retrievedDate = dateOnly(item.fetched_at);
  return (
    <details className="item-provenance" lang={t === sw ? "en" : undefined}>
      <summary>{text("sourceDetails")}</summary>
      <dl>
        <dt>{text("attribution")}</dt>
        <dd>{item.source_attribution || text("attributionUnavailable")}</dd>
        <dt>
          {item.date_source === "updated" ? text("updated") : text("published")}
        </dt>
        <dd>
          {contentDate ? (
            <time dateTime={contentDate}>{contentDate}</time>
          ) : (
            text("publicationDateUnavailable")
          )}
        </dd>
        {retrievedDate && (
          <>
            <dt>{text("retrieved")}</dt>
            <dd>
              <time dateTime={retrievedDate}>{retrievedDate}</time>
            </dd>
          </>
        )}
        <dt>{text("reportedRights")}</dt>
        <dd>{item.source_rights || text("rightsUnavailable")}</dd>
      </dl>
      <p>{text("reuseUnverified")}</p>
      {item.source_url && (
        <a href={item.source_url} target="_blank" rel="noreferrer">
          {text("sourceFeed")}
        </a>
      )}
    </details>
  );
}

function Cards({ items = [], t, doneCallback }) {
  return (
    <div className="cards">
      {items.map((item) => (
        <article className="panel item-card" key={item.id}>
          <h3>
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.title}
              </a>
            ) : (
              item.title
            )}
          </h3>
          <p className="item-summary">{item.summary}</p>
          <p className="meta">
            {[item.source, item.is_low_data && t.lowData]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <ItemProvenance item={item} t={t} />
          <p>{item.skills.join(" · ")}</p>
          {!item.done && (
            <button onClick={() => doneCallback?.(item.id)}>
              {t.markDone}
            </button>
          )}
          {item.done && <span>✓ {t.done}</span>}
        </article>
      ))}
    </div>
  );
}

function ItemList({ t }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api
      .get("/items/")
      .then((r) => setItems(r.data))
      .catch(() => {});
  }, []);
  async function done(id) {
    await api.post(`/items/${id}/done/`);
    setItems((all) => all.map((i) => (i.id === id ? { ...i, done: true } : i)));
  }
  return (
    <section>
      <h1>{t.items}</h1>
      <Cards items={items} t={t} doneCallback={done} />
    </section>
  );
}

function CheckpointPage({ t }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [checkpoint, setCheckpoint] = useState(null);
  const [attested, setAttested] = useState(false);
  const [answers, setAnswers] = useState([null, null, null]);
  useEffect(() => {
    api
      .get("/dashboard/")
      .then((r) => {
        const match = r.data.next_checkpoint;
        if (match && String(match.id) === id) setCheckpoint(match);
      })
      .catch(() => {});
  }, [id]);
  async function complete() {
    try {
      await api.post(`/checkpoints/${id}/complete/`, {
        self_attested: attested,
        quiz_answers: answers,
      });
      navigate("/next");
    } catch {}
  }
  if (!checkpoint)
    return (
      <section className="panel">
        <h1>{t.checkpoint}</h1>
        <p>This checkpoint is not available on the current pathway.</p>
        <Link to="/pathway">{t.back}</Link>
      </section>
    );
  return (
    <section className="panel stack">
      <p className="eyebrow">{localText(t, checkpoint.skill)}</p>
      <h1>{checkpointTitle(t, checkpoint.title)}</h1>
      <p>
        {t === sw
          ? "Kamilisha zoezi fupi ukitumia ujuzi huu na utafakari kuhusu ulichojifunza."
          : checkpoint.criteria}
      </p>
      <h2>{t.quiz}</h2>
      {checkpoint.quiz.map((q, index) => (
        <fieldset key={index}>
          <legend>
            {t === sw
              ? [
                  "Ni hatua ipi inaonyesha ujuzi huu vizuri?",
                  "Ufanye nini matokeo yakionekana si sahihi?",
                  "Unawezaje kuendelea kuboresha ujuzi wako?",
                ][index]
              : q.question}
          </legend>
          {q.options.map((option, i) => (
            <label className="radio" key={option}>
              <input
                type="radio"
                name={`q${index}`}
                checked={answers[index] === i}
                onChange={() =>
                  setAnswers((old) =>
                    old.map((answer, n) => (n === index ? i : answer)),
                  )
                }
              />
              {t === sw
                ? i === 0
                  ? [
                      "Tumia kwenye zoezi dogo",
                      "Kagua hatua ulizofuata",
                      "Fanya mazoezi na tafakari",
                    ][index]
                  : [
                      "Ruka mazoezi yote",
                      "Puuza matokeo",
                      "Acha baada ya jaribio moja",
                    ][index]
                : option}
            </label>
          ))}
        </fieldset>
      ))}
      <label className="radio">
        <input
          type="checkbox"
          checked={attested}
          onChange={(e) => setAttested(e.target.checked)}
        />
        {t.selfAttest}
      </label>
      <button
        disabled={!attested || answers.some((answer) => answer === null)}
        onClick={complete}
      >
        {t.complete}
      </button>
      <button
        className="quiet"
        onClick={async () => {
          await api.post(`/checkpoints/${id}/skip/`);
          navigate("/pathway");
        }}
      >
        {t.skip}
      </button>
      <Link to="/pathway">{t.back}</Link>
    </section>
  );
}

function NextPage({ t }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    api
      .get("/next/")
      .then((response) => setData(response.data))
      .catch(() => setData({ available: false, reason: "no_learner" }));
  }, []);
  if (data === null)
    return (
      <section className="panel">
        <h1>{t.whatsNext}</h1>
        <p>{t.loading}</p>
      </section>
    );
  if (!data.unlocked_skill)
    return (
      <section className="panel stack">
        <h1>{t.whatsNext}</h1>
        <p>
          {data.reason === "no_checkpoint" ? t.nextNoCheckpoint : t.nextEmpty}
        </p>
        <Link
          className="button"
          to={data.reason === "no_checkpoint" ? "/pathway" : "/"}
        >
          {data.reason === "no_checkpoint" ? t.back : t.choosePathway}
        </Link>
      </section>
    );
  return (
    <section className="stack">
      <div className="panel">
        <h1>{t.whatsNext}</h1>
        <h2>
          {t.unlocked}: {localText(t, data?.unlocked_skill)}
        </h2>
        <p>
          {t === sw
            ? `Sasa unaweza kutumia ${localText(t, data?.unlocked_skill)} kama sehemu ya safari yako ya kazi.`
            : data?.unlocks_text}
        </p>
        {data?.next_checkpoint && (
          <p>
            {t.nextCheckpoint}: {checkpointTitle(t, data.next_checkpoint.title)}
          </p>
        )}
        <Link className="button" to="/pathway">
          {t.back}
        </Link>
      </div>
      <h2>{t.lessons}</h2>
      <Cards items={data?.items || []} t={t} />
      <h2>{t.opportunities}</h2>
      <div className="cards">
        {(data?.opportunities || []).map((op) => (
          <OpportunityCard key={op.id} op={op} t={t} />
        ))}
      </div>
    </section>
  );
}

function OpportunityCard({ op, t }) {
  return (
    <article className="panel">
      <h3>
        <a href={op.url} target="_blank" rel="noreferrer">
          {op.title}
        </a>
      </h3>
      <p>
        {op.provider} · {op.location}
      </p>
      <p>
        {op.match_percent}% {t.match} · {t.sampleListing}
      </p>
    </article>
  );
}

function Settings({ learner, t, language, setLang, refresh }) {
  const [message, setMessage] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [phone, setPhone] = useState("");
  useEffect(() => {
    setOptIn(Boolean(learner?.reminder_opt_in));
    setPhone(learner?.phone || "");
  }, [learner]);
  async function save() {
    try {
      await api.patch("/me/", {
        preferred_language: language,
        reminder_opt_in: optIn,
        phone,
      });
      await refresh();
      setMessage(t.saved);
    } catch {
      setMessage(t.error);
    }
  }
  async function remove() {
    if (!window.confirm(t.delete + "?")) return;
    await api.delete("/me/");
    await refresh();
  }
  return (
    <section className="panel stack">
      <h1>{t.settings}</h1>
      <label>
        {t.language}
        <select value={language} onChange={(e) => setLang(e.target.value)}>
          <option value="en">English</option>
          <option value="sw">Kiswahili</option>
        </select>
      </label>
      <label>
        {t.phoneOptional}
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          maxLength="30"
        />
      </label>
      <label className="radio">
        <input
          type="checkbox"
          checked={optIn}
          onChange={(e) => setOptIn(e.target.checked)}
        />
        {t.reminders}
      </label>
      <button onClick={save}>{t.save}</button>
      {message && <p role="status">{message}</p>}
      <button className="danger" onClick={remove}>
        {t.delete}
      </button>
    </section>
  );
}

export default App;

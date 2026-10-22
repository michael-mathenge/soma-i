import { useCallback, useEffect, useRef, useState } from "react";
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
  const [pathwayStatus, setPathwayStatus] = useState("loading");
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
      setPathwayStatus("ready");
      setError("");
    } catch {
      setLearner(null);
      try {
        const pathwayResponse = await pathwayRequest;
        setPathways(pathwayResponse.data);
        setPathwayStatus("ready");
      } catch {
        try {
          setPathways((await getPathways()).data);
          setPathwayStatus("ready");
        } catch {
          setPathways([]);
          setPathwayStatus("error");
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
          <NavLink
            to="/account"
            end
            lang={language === "sw" ? "en" : undefined}
          >
            {en.account}
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
                pathwayStatus={pathwayStatus}
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
          <Route
            path="/account/verify"
            element={<RecoveryConfirm purpose="verify" t={t} />}
          />
          <Route
            path="/account/reset"
            element={<RecoveryConfirm purpose="reset" t={t} />}
          />
          <Route
            path="/account"
            element={<AccountPage refresh={refresh} t={t} />}
          />
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
  // Adopt a query that arrived from the URL, but never clobber a value the
  // learner is still typing; the form owns the input until it is submitted.
  const lastQuery = useRef(query);
  useEffect(() => {
    if (query !== lastQuery.current) {
      lastQuery.current = query;
      setSearch(query);
    }
  }, [query]);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setState({ loading: true });
    api
      .get("/roadmaps/", {
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
            // The submitted term is read from the form itself rather than
            // from the component state, so a term that was typed and
            // submitted in quick succession is never dropped.
            const term = (
              event.currentTarget.elements.namedItem("q")?.value ?? ""
            ).trim();
            setParams({
              ...(term ? { q: term } : {}),
              page: "1",
            });
          }}
        >
          <label>
            {en.searchTopics}
            <input
              type="search"
              name="q"
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
              <RoadmapCard topic={topic} key={topic.slug || topic.id} />
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

function RoadmapCard({ topic }) {
  const availableId = topic.available_pathway_id || topic.id;
  const canStart = Boolean(topic.available || topic.is_demo);
  const steps = topic.steps || [];
  return (
    <article className="panel stack roadmap-card">
      {topic.image?.url && (
        <figure className="roadmap-image">
          <img
            src={topic.image.url}
            alt={topic.image.alt || ""}
            loading="lazy"
          />
          {topic.image.credit && <figcaption>{topic.image.credit}</figcaption>}
        </figure>
      )}
      <div className="roadmap-card__body">
        <p className="eyebrow">
          {canStart ? en.availableNow : en.previewRoadmap}
          {topic.version ? ` · v${topic.version}` : ""}
        </p>
        {topic.is_demo && <p className="eyebrow">{en.demoTopic}</p>}
        <h2>{topic.title}</h2>
        <p>{topic.description}</p>
        <p className="roadmap-outcome">{topic.target_outcome}</p>
        {steps.length > 0 && (
          <ol className="roadmap-steps" aria-label={en.roadmapSteps}>
            {steps.map((step, index) => (
              <li key={`${index}-${step.skill}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{step.skill}</strong>
              </li>
            ))}
          </ol>
        )}
        {canStart ? (
          <Link
            className="button"
            to={`/?pathway=${availableId}`}
            aria-label={`${en.choosePathway}: ${topic.title}`}
          >
            {en.choosePathway}
          </Link>
        ) : (
          <p className="source-gate">{en.sourceGate}</p>
        )}
      </div>
    </article>
  );
}

// Reads may be retried explicitly. Writes are never replayed automatically.
function useJourneyData(endpoint, identity = null) {
  const [state, setState] = useState({ loading: true, data: null });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setState({ loading: true, data: null });
    api
      .get(endpoint, { signal: controller.signal })
      .then(({ data }) => {
        if (active) setState({ data });
      })
      .catch((error) => {
        if (active)
          setState({
            unauthenticated: error.response?.status === 401,
            error: error.response?.status !== 401,
            data: null,
          });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [endpoint, identity, attempt]);
  return {
    ...state,
    retry: () => setAttempt((value) => value + 1),
    update: (transform) =>
      setState((old) =>
        old.data == null ? old : { ...old, data: transform(old.data) },
      ),
  };
}
function useJourneyAction() {
  const locked = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  async function run(work) {
    if (locked.current) return;
    locked.current = true;
    setPending(true);
    setError(false);
    try {
      await work();
    } catch {
      setError(true);
    } finally {
      locked.current = false;
      setPending(false);
    }
  }
  return { pending, error, run };
}
function ActionFeedback({ action, t }) {
  if (!action.pending && !action.error) return null;
  return (
    <div lang={t === sw ? "en" : undefined}>
      {action.pending && <p role="status">{en.savingProgress}</p>}
      {action.error && (
        <p role="alert" className="notice">
          {en.actionUnconfirmed}
        </p>
      )}
    </div>
  );
}
function JourneyState({ state, title, t }) {
  return (
    <section className="panel stack">
      <h1>{title}</h1>
      {state.loading ? (
        <p role="status">{t.loading}</p>
      ) : state.error ? (
        <div lang={t === sw ? "en" : undefined}>
          <p role="alert">{en.journeyLoadError}</p>
          <button onClick={state.retry}>{en.retry}</button>
        </div>
      ) : (
        <>
          <p lang={t === sw ? "en" : undefined}>{en.chooseToBegin}</p>
          <Link className="button" to="/">
            {t.choosePathway}
          </Link>
        </>
      )}
    </section>
  );
}
function completedLesson(items, id) {
  return items.map((item) => (item.id === id ? { ...item, done: true } : item));
}

function Onboarding({
  pathways,
  pathwayStatus,
  t,
  language,
  setLang,
  refresh,
}) {
  const navigate = useNavigate();
  const action = useJourneyAction();
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
    action.run(async () => {
      await api.post("/me/", {
        display_name: name || "Learner",
        preferred_language: language,
        pathway_id: selected,
      });
      await refresh();
      navigate("/pathway");
    });
  }
  async function demo() {
    action.run(async () => {
      await api.post("/demo/");
      await refresh();
      navigate("/pathway");
    });
  }
  return (
    <section className="panel hero">
      <p className="eyebrow">SOMA.i</p>
      <h1>{t.onboarding}</h1>
      <p>
        {t.tagline}. {t.intro}
      </p>
      <p lang={t === sw ? "en" : undefined}>{en.guestJourney}</p>
      {pathwayStatus === "loading" && <p role="status">{t.loading}</p>}
      {pathwayStatus === "error" && (
        <div lang={t === sw ? "en" : undefined}>
          <p role="alert">{en.catalogueError}</p>
          <button onClick={refresh}>{en.retry}</button>
        </div>
      )}
      {pathwayStatus === "ready" && !pathways.length && (
        <p lang={t === sw ? "en" : undefined}>{en.noEnrollableTopics}</p>
      )}
      <ActionFeedback action={action} t={t} />
      <form onSubmit={start} className="stack" aria-busy={action.pending}>
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
        <button disabled={!selected || action.pending}>{t.start}</button>
      </form>
      <button className="quiet" disabled={action.pending} onClick={demo}>
        {t.demo}
      </button>
    </section>
  );
}

function Dashboard({ learner, pathways = [], refresh, t }) {
  const state = useJourneyData("/dashboard/", learner);
  const actionState = useJourneyAction();
  const data = state.data;
  const navigate = useNavigate();
  function action(name, payload) {
    if (name === "restart" && !window.confirm(en.restartConfirm)) return;
    actionState.run(async () => {
      await api.post(`/pathway/${name}/`, payload);
      await refresh();
    });
  }
  if (!data?.pathway)
    return <JourneyState state={state} title={t.dashboard} t={t} />;
  return (
    <section className="stack">
      <ActionFeedback action={actionState} t={t} />
      <div className="panel" aria-busy={actionState.pending}>
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
        <section className="journey-outline" lang={t === sw ? "en" : undefined}>
          <h2>{en.yourLearningSteps}</h2>
          <ol className="journey-steps">
            {(data.steps || []).map((step, index) => (
              <li
                key={`${index}-${step.skill}`}
                aria-current={
                  step.skill === data.next_checkpoint?.skill
                    ? "step"
                    : undefined
                }
              >
                <strong>{localText(t, step.skill)}</strong>
                <span>
                  {step.status === "done"
                    ? en.stepDone
                    : step.status === "skipped"
                      ? en.stepSkipped
                      : step.skill === data.next_checkpoint?.skill
                        ? en.stepCurrent
                        : en.stepRemaining}
                </span>
              </li>
            ))}
          </ol>
        </section>
        {!data.next_checkpoint && (
          <p role="status" lang={t === sw ? "en" : undefined}>
            {en.pathwayFinished}
          </p>
        )}
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
              disabled={actionState.pending}
              onChange={(e) => action("switch", { pathway_id: e.target.value })}
            >
              {!pathways.some((p) => p.id === data.pathway.id) && (
                <option value={data.pathway.id}>
                  {localText(t, data.pathway.title)}
                </option>
              )}
              {pathways.map((p) => (
                <option key={p.id} value={p.id}>
                  {localText(t, p.title)}
                </option>
              ))}
            </select>
          </label>
          <button
            className="quiet"
            disabled={actionState.pending || !data.next_checkpoint}
            onClick={() => action("skip")}
          >
            {t.skip}
          </button>
          <button
            className="quiet"
            disabled={actionState.pending}
            onClick={() => action("restart")}
          >
            {t.restart}
          </button>
        </div>
      </div>
      <h2>{t.lessons}</h2>
      {!data.items.length && (
        <p className="panel" lang={t === sw ? "en" : undefined}>
          {en.noLessons}
        </p>
      )}
      <Cards
        items={data.items}
        t={t}
        disabled={actionState.pending}
        doneCallback={(id) =>
          state.update((old) => ({
            ...old,
            items: completedLesson(old.items, id),
          }))
        }
      />
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

function Cards({ items = [], t, doneCallback, disabled = false }) {
  const action = useJourneyAction();
  return (
    <>
      <ActionFeedback action={action} t={t} />
      <div className="cards" aria-busy={action.pending}>
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
            {item.excerpt && <p className="item-summary">{item.excerpt}</p>}
            <p className="meta">
              {[item.source, item.is_low_data && t.lowData]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {item.url && (
              <p className="item-read">
                <a href={item.url} target="_blank" rel="noreferrer">
                  {t.readAtPublisher}
                </a>
              </p>
            )}
            <ItemProvenance item={item} t={t} />
            <p>{item.skills.join(" · ")}</p>
            {!item.done && doneCallback && (
              <button
                disabled={disabled || action.pending}
                onClick={() =>
                  action.run(async () => {
                    await api.post(`/items/${item.id}/done/`);
                    doneCallback(item.id);
                  })
                }
              >
                {t.markDone}
              </button>
            )}
            {item.done && <span>✓ {t.done}</span>}
          </article>
        ))}
      </div>
    </>
  );
}

function ItemList({ t }) {
  const state = useJourneyData("/items/");
  if (!state.data) return <JourneyState state={state} title={t.items} t={t} />;
  return (
    <section className="stack">
      <h1>{t.items}</h1>
      {!state.data.length && (
        <p className="panel" lang={t === sw ? "en" : undefined}>
          {en.noLessons}
        </p>
      )}
      <Cards
        items={state.data}
        t={t}
        doneCallback={(id) =>
          state.update((items) => completedLesson(items, id))
        }
      />
    </section>
  );
}

function CheckpointPage({ t }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const state = useJourneyData("/dashboard/", id);
  const action = useJourneyAction();
  const match = state.data?.next_checkpoint;
  const checkpoint = match && String(match.id) === id ? match : null;
  const [attested, setAttested] = useState(false);
  const [answers, setAnswers] = useState([null, null, null]);
  useEffect(() => {
    setAttested(false);
    setAnswers([null, null, null]);
  }, [id]);
  function submit(kind) {
    action.run(async () => {
      await api.post(
        `/checkpoints/${id}/${kind}/`,
        kind === "complete"
          ? {
              self_attested: attested,
              quiz_answers: answers,
            }
          : undefined,
      );
      navigate(kind === "complete" ? "/next" : "/pathway");
    });
  }
  if (state.loading || state.error || state.unauthenticated)
    return <JourneyState state={state} title={t.checkpoint} t={t} />;
  if (!checkpoint)
    return (
      <section className="panel">
        <h1>{t.checkpoint}</h1>
        <p lang={t === sw ? "en" : undefined}>{en.checkpointUnavailable}</p>
        <Link to="/pathway">{t.back}</Link>
      </section>
    );
  return (
    <section className="panel stack" aria-busy={action.pending}>
      <ActionFeedback action={action} t={t} />
      <p className="eyebrow">{localText(t, checkpoint.skill)}</p>
      <h1>{checkpointTitle(t, checkpoint.title)}</h1>
      <p>
        {t === sw
          ? "Kamilisha zoezi fupi ukitumia ujuzi huu na utafakari kuhusu ulichojifunza."
          : checkpoint.criteria}
      </p>
      <h2>{t.quiz}</h2>
      {checkpoint.quiz.map((q, index) => (
        <fieldset key={index} disabled={action.pending}>
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
          disabled={action.pending}
          checked={attested}
          onChange={(e) => setAttested(e.target.checked)}
        />
        {t.selfAttest}
      </label>
      <button
        disabled={
          action.pending ||
          !attested ||
          answers.some((answer) => answer === null)
        }
        onClick={() => submit("complete")}
      >
        {t.complete}
      </button>
      <button
        className="quiet"
        disabled={action.pending}
        onClick={() => submit("skip")}
      >
        {t.skip}
      </button>
      <Link to="/pathway">{t.back}</Link>
    </section>
  );
}

function NextPage({ t }) {
  const state = useJourneyData("/next/");
  const data = state.data;
  if (!data) return <JourneyState state={state} title={t.whatsNext} t={t} />;
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
      {!data.items?.length && (
        <p className="panel" lang={t === sw ? "en" : undefined}>
          {en.noLessons}
        </p>
      )}
      <Cards
        items={data?.items || []}
        t={t}
        doneCallback={(id) =>
          state.update((old) => ({
            ...old,
            items: completedLesson(old.items || [], id),
          }))
        }
      />
      <h2>{t.opportunities}</h2>
      {!data.opportunities?.length && (
        <p className="panel" lang={t === sw ? "en" : undefined}>
          {en.noOpportunities}
        </p>
      )}
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
    try {
      await api.delete("/me/");
      await refresh();
    } catch {
      setMessage(t.error);
    }
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
      <Link to="/account" lang={t === sw ? "en" : undefined}>
        {en.account}
      </Link>
    </section>
  );
}

export default App;

function AccountPage({ refresh, t }) {
  const [identity, setIdentity] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [attach, setAttach] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const lock = useRef(false);
  const navigate = useNavigate();
  const load = useCallback(() => {
    setError("");
    return api
      .get("/account/")
      .then(({ data }) => setIdentity(data))
      .catch(() => setError(en.accountLoadError));
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  async function act(action) {
    if (lock.current) return;
    if (action === "delete" && !window.confirm(en.accountDeleteConfirm)) return;
    lock.current = true;
    setPending(true);
    setError("");
    try {
      if (action === "register")
        await api.post("/account/", { email, password, attach_guest: attach });
      if (action === "login")
        await api.post("/account/login/", { email, password });
      if (action === "logout") await api.post("/account/logout/");
      if (action === "delete")
        await api.delete("/account/", { data: { password } });
      setPassword("");
      await load();
      await refresh();
      if (action === "login" || action === "register") navigate("/pathway");
    } catch (failure) {
      setError(
        failure.response?.data?.detail ||
          failure.message ||
          en.accountActionError,
      );
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return (
    <section
      className="panel stack account-form"
      lang={t === sw ? "en" : undefined}
    >
      <h1>{en.account}</h1>
      <p>{en.accountOptional}</p>
      <p>{en.accountRecoveryUnavailable}</p>
      {error && <p role="alert">{error}</p>}
      {!identity ? (
        <button disabled={pending} onClick={load}>
          {en.retry}
        </button>
      ) : identity.authenticated ? (
        <>
          <p>
            {en.accountSignedIn}: {identity.email}
          </p>
          <p>
            {identity.email_verified
              ? en.accountVerified
              : en.accountUnverified}
          </p>
          <button disabled={pending} onClick={() => act("logout")}>
            {en.accountLogout}
          </button>
          <label>
            {en.accountPassword}
            <input
              type="password"
              autoComplete="current-password"
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={pending}
            />
          </label>
          <button
            className="danger"
            disabled={pending || !password}
            onClick={() => act("delete")}
          >
            {en.accountDelete}
          </button>
        </>
      ) : (
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            act("login");
          }}
        >
          <label>
            {en.accountEmail}
            <input
              type="email"
              autoComplete="username"
              required
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={pending}
            />
          </label>
          <label>
            {en.accountPassword}
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={pending}
            />
          </label>
          <p>{en.accountPasswordHelp}</p>
          <label className="radio">
            <input
              type="checkbox"
              checked={attach}
              onChange={(event) => setAttach(event.target.checked)}
              disabled={pending}
            />
            {en.accountAttach}
          </label>
          <p>{en.accountLoginGuest}</p>
          <button disabled={pending} type="submit">
            {en.accountLogin}
          </button>
          <button
            disabled={pending || !email || !password}
            type="button"
            onClick={() => act("register")}
          >
            {en.accountRegister}
          </button>
        </form>
      )}
      {pending && <p role="status">{en.accountPending}</p>}
      {identity && <RecoveryTools identity={identity} />}
      <Link to="/">{en.accountContinueGuest}</Link>
    </section>
  );
}

function useRecoveryOptions() {
  const [state, setState] = useState({ loading: true });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    api
      .get("/account/recovery/options/")
      .then(({ data }) => {
        if (active) setState({ data });
      })
      .catch(() => {
        if (active) setState({ error: true });
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  return {
    ...state,
    retry: () => {
      setState({ loading: true });
      setAttempt((value) => value + 1);
    },
  };
}

function RecoveryTools({ identity }) {
  const options = useRecoveryOptions();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const locked = useRef(false);
  async function request(purpose) {
    if (locked.current) return;
    locked.current = true;
    setPending(true);
    setMessage("");
    setError("");
    try {
      await api.post(
        `/account/${purpose}/request/`,
        purpose === "reset" ? { email } : {},
      );
      setMessage(en.recoveryRequested);
    } catch {
      setError(en.recoveryRequestError);
    } finally {
      locked.current = false;
      setPending(false);
    }
  }
  return (
    <section
      className="stack account-recovery"
      aria-labelledby="recovery-heading"
    >
      <h2 id="recovery-heading">{en.recoveryHeading}</h2>
      {options.loading ? (
        <p role="status">{en.loading}</p>
      ) : options.error ? (
        <>
          <p>{en.recoveryOptionsError}</p>
          <button onClick={options.retry}>{en.retry}</button>
        </>
      ) : !options.data.available ? (
        <p>{en.recoveryDisabled}</p>
      ) : (
        <>
          <p>{en.recoveryPreview}</p>
          {identity.authenticated ? (
            <button
              disabled={pending || identity.email_verified}
              onClick={() => request("verify")}
            >
              {en.recoveryVerifyRequest}
            </button>
          ) : (
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                request("reset");
              }}
            >
              <label>
                {en.recoveryEmail}
                <input
                  type="email"
                  required
                  autoComplete="email"
                  maxLength={254}
                  disabled={pending}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <button disabled={pending} type="submit">
                {en.recoveryResetRequest}
              </button>
            </form>
          )}
        </>
      )}
      {pending && <p role="status">{en.accountPending}</p>}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

function RecoveryConfirm({ purpose, t }) {
  const location = useLocation();
  const [token, setToken] = useState(
    () => new URLSearchParams(location.hash.slice(1)).get("token") || "",
  );
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);
  const locked = useRef(false);
  // Fragments never reach the server; scrub history before the capability GET.
  useEffect(() => {
    setToken(new URLSearchParams(location.hash.slice(1)).get("token") || "");
    setPassword("");
    setError("");
    setDone(false);
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname + window.location.search,
    );
  }, [location.key, location.hash, purpose]);
  const options = useRecoveryOptions();
  async function confirm(event) {
    event.preventDefault();
    if (locked.current) return;
    locked.current = true;
    setPending(true);
    setError("");
    try {
      await api.post(`/account/${purpose}/confirm/`, {
        token,
        ...(purpose === "reset" ? { password } : {}),
      });
      setDone(true);
      setToken("");
      setPassword("");
    } catch (failure) {
      setError(
        failure.response?.status === 400
          ? en.recoveryInvalid
          : en.recoveryConfirmError,
      );
    } finally {
      locked.current = false;
      setPending(false);
    }
  }
  return (
    <section
      className="panel stack account-form"
      lang={t === sw ? "en" : undefined}
    >
      <h1>
        {purpose === "reset"
          ? en.recoveryResetHeading
          : en.recoveryVerifyHeading}
      </h1>
      {done ? (
        <p role="status">
          {purpose === "reset" ? en.recoveryResetDone : en.recoveryVerifyDone}
        </p>
      ) : options.loading ? (
        <p role="status">{en.loading}</p>
      ) : options.error ? (
        <>
          <p role="alert">{en.recoveryOptionsError}</p>
          <button onClick={options.retry}>{en.retry}</button>
        </>
      ) : !options.data.available ? (
        <p>{en.recoveryDisabled}</p>
      ) : !/^[a-f0-9]{64}$/.test(token) ? (
        <p role="alert">{en.recoveryInvalid}</p>
      ) : (
        <form className="stack" onSubmit={confirm}>
          <p>{en.recoveryPreview}</p>
          <p>{en.recoveryExplicit}</p>
          {purpose === "reset" && (
            <label>
              {en.recoveryNewPassword}
              <input
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
                disabled={pending}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
          )}
          <button disabled={pending} type="submit">
            {purpose === "reset"
              ? en.recoveryResetConfirm
              : en.recoveryVerifyConfirm}
          </button>
        </form>
      )}
      {pending && <p role="status">{en.accountPending}</p>}
      {error && <p role="alert">{error}</p>}
      <Link to="/account">{en.account}</Link>
    </section>
  );
}

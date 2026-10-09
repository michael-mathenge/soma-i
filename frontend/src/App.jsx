import { useCallback, useEffect, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
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
    refresh();
  }, [refresh]);
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);
  const setLang = (value) => {
    localStorage.setItem("somai-language", value);
    setLanguage(value);
  };
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link to="/" className="brand" aria-label="SOMA.i home">
          {t.brand}
        </Link>
        <span>{t.tagline}</span>
        <nav aria-label="Main navigation">
          <Link to="/pathway">{t.dashboard}</Link>
          <Link to="/items">{t.items}</Link>
          <Link to="/settings">{t.settings}</Link>
        </nav>
      </header>
      {error && (
        <p role="alert" className="notice">
          {t.error}
        </p>
      )}
      <main>
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

function Onboarding({ pathways, t, language, setLang, refresh }) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState("");
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

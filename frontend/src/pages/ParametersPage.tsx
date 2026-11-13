import { useEffect, useMemo, useState } from "react";
import type { EvalParam } from "../api/client";
import { useEvalSettings } from "../state/EvalSettingsContext";

function ParamList({
  title,
  items,
  draft,
  onToggle,
}: {
  title: string;
  items: EvalParam[];
  draft: Record<string, boolean>;
  onToggle: (key: string) => void;
}) {
  return (
    <section className="panel param-section param-pane">
      <h2>{title}</h2>
      <div className="param-list">
        {items.map((param) => {
          const on = draft[param.key] ?? param.enabled;
          return (
            <div className="param-row" key={param.key}>
              <div>
                <h3>{param.label}</h3>
                <p>{param.description}</p>
                <p className="mono muted" style={{ marginTop: "0.35rem" }}>
                  {param.key}
                </p>
              </div>
              <button
                type="button"
                className={`toggle ${on ? "on" : ""}`}
                aria-pressed={on}
                aria-label={`Toggle ${param.label}`}
                onClick={() => onToggle(param.key)}
              >
                <span />
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function ParametersPage() {
  const { settings, loading, error, save } = useEvalSettings();
  const [draft, setDraft] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setDraft({ ...settings.enabled });
    }
  }, [settings]);

  const dirty = useMemo(() => {
    if (!settings) return false;
    return Object.keys(draft).some((k) => draft[k] !== settings.enabled[k]);
  }, [draft, settings]);

  function toggle(key: string) {
    setSaved(false);
    setDraft((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  async function onSave() {
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      await save(draft);
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !settings) {
    return <p className="muted">Loading parameter settings…</p>;
  }

  if (error && !settings) {
    return <p className="error">{error}</p>;
  }

  if (!settings) return null;

  return (
    <div className="parameters-page">
      <div className="parameters-page-top">
        <header className="page-head detailed-results-head">
          <h1>Parameters</h1>
          <p>
            Turn evaluation metrics on or off. Disabled parameters are omitted from
            new session scorecards after you save.
          </p>
        </header>
        {saveError && <p className="error">{saveError}</p>}
      </div>

      <div className="parameters-page-body">
        <ParamList
          title="Audio parameters"
          items={settings.audio}
          draft={draft}
          onToggle={toggle}
        />
        <ParamList
          title="Knowledge parameters"
          items={settings.knowledge}
          draft={draft}
          onToggle={toggle}
        />
      </div>

      <div className="save-bar parameters-save-bar">
        <div>
          {saved && <span className="toast-ok">Saved.</span>}
          {!saved && dirty && <span className="muted">Unsaved changes</span>}
        </div>
        <button className="btn" type="button" onClick={onSave} disabled={saving || !dirty}>
          {saving ? "Saving…" : "Save settings"}
        </button>
      </div>
    </div>
  );
}

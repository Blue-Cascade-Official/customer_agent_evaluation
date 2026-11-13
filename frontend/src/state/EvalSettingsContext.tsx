import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getEvalSettings,
  updateEvalSettings,
  type EvalSettings,
} from "../api/client";

type EvalSettingsContextValue = {
  settings: EvalSettings | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  save: (enabled: Record<string, boolean>) => Promise<EvalSettings>;
};

const EvalSettingsContext = createContext<EvalSettingsContextValue | null>(null);

// Module-level cache so remounts (tab switches) reuse the last payload
let cachedSettings: EvalSettings | null = null;
let inflight: Promise<EvalSettings> | null = null;

async function loadSettings(force = false): Promise<EvalSettings> {
  if (!force && cachedSettings) return cachedSettings;
  if (!force && inflight) return inflight;
  inflight = getEvalSettings()
    .then((data) => {
      cachedSettings = data;
      return data;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

export function EvalSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<EvalSettings | null>(cachedSettings);
  const [loading, setLoading] = useState(!cachedSettings);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (force = true) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loadSettings(force);
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (cachedSettings) {
        setSettings(cachedSettings);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const data = await loadSettings(false);
        if (!cancelled) setSettings(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load settings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = useCallback(async (enabled: Record<string, boolean>) => {
    const updated = await updateEvalSettings(enabled);
    cachedSettings = updated;
    setSettings(updated);
    return updated;
  }, []);

  const value = useMemo(
    () => ({
      settings,
      loading,
      error,
      refresh: () => refresh(true),
      save,
    }),
    [settings, loading, error, refresh, save],
  );

  return (
    <EvalSettingsContext.Provider value={value}>{children}</EvalSettingsContext.Provider>
  );
}

export function useEvalSettings() {
  const ctx = useContext(EvalSettingsContext);
  if (!ctx) {
    throw new Error("useEvalSettings must be used within EvalSettingsProvider");
  }
  return ctx;
}

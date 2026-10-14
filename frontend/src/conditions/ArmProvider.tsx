import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Affordances } from "./affordances";
import { studyHeaders } from "../features/consent/ConsentGate";

type ConditionContextValue = {
  affordances: Affordances | null;
  askUrl: string;
  error: string;
};

const ConditionContext = createContext<ConditionContextValue | null>(null);

export function ArmProvider({ children }: { children: ReactNode }) {
  const [affordances, setAffordances] = useState<Affordances | null>(null);
  const [error, setError] = useState("");
  const arm = new URLSearchParams(window.location.search).get("arm");
  const suffix = arm ? `?arm=${encodeURIComponent(arm)}` : "";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/conditions/affordances${suffix}`, { signal: controller.signal, headers: studyHeaders() })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Conditions request failed: ${response.status}`);
        const body = await response.json() as { affordances: Affordances };
        setAffordances(body.affordances);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(String(cause));
      });
    return () => controller.abort();
  }, [suffix]);

  const value = useMemo(
    () => ({ affordances, askUrl: `/ask${suffix}`, error }),
    [affordances, suffix, error],
  );
  return <ConditionContext.Provider value={value}>{children}</ConditionContext.Provider>;
}

export function useArmConditions(): ConditionContextValue {
  const value = useContext(ConditionContext);
  if (!value) throw new Error("useArmConditions must be used inside ArmProvider");
  return value;
}

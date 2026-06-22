"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface AppContextValue {
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  datasetIds: string[];
  setDatasetIds: (ids: string[]) => void;
}

const AppContext = createContext<AppContextValue>({
  activeSessionId: null,
  setActiveSessionId: () => {},
  datasetIds: [],
  setDatasetIds: () => {},
});

export function AppProvider({ children }: { children: ReactNode }) {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [datasetIds, setDatasetIds] = useState<string[]>([]);

  return (
    <AppContext.Provider
      value={{ activeSessionId, setActiveSessionId, datasetIds, setDatasetIds }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}

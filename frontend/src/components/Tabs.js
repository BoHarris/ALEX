import { Children, createContext, useContext, useMemo, useState } from "react";

const TabsContext = createContext(null);

export function Tabs({ children, defaultvalue, value, onValueChange }) {
  const [internalActive, setInternalActive] = useState(defaultvalue);
  const active = value ?? internalActive;
  const setActive = onValueChange ?? setInternalActive;
  const ctx = useMemo(() => ({ active, setActive }), [active, setActive]);
  return <TabsContext.Provider value={ctx}>{children}</TabsContext.Provider>;
}

export function TabList({ children }) {
  return <div className="flex border-b border-app">{children}</div>;
}

export function Tab({ value, children }) {
  const { active, setActive } = useContext(TabsContext);
  const isActive = active === value;
  return (
    <button
      onClick={() => setActive(value)}
      className={
        isActive
          ? "px-4 py-2 -mb-px border-b-2 border-cyan-500 text-cyan-400 font-medium"
          : "px-4 py-2 text-app-secondary hover:text-app"
      }
    >
      {children}
    </button>
  );
}

export function TabPanels({ children }) {
  const { active } = useContext(TabsContext);
  const panels = Children.toArray(children);
  return (
    <>
      {panels.map((panel) => (panel.props.value === active ? panel : null))}
    </>
  );
}

export function TabPanel({ value, children }) {
  return <div className="p-4">{children}</div>;
}

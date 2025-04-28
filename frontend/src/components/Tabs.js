import { createContext, useContext, useMemo, useState } from "react";

const TabsContext = createContext(null);

export function Tabs({ children, defaultvalue }) {
  const [active, setActive] = useState(defaultvalue);
  const ctx = useMemo(() => ({ active, setActive }), [active]);
  return <TabsContext.Provider value={ctx}>{children}</TabsContext.Provider>;
}

export function TabList({ children }) {
  return <div className="flex border-b">{children}</div>;
}

export function Tab({ value, children }) {
  const { active, setActive } = useContext(TabsContext);
  const isActive = active === value;
  return (
    <button
      onClick={() => setActive(value)}
      className={
        isActive
          ? "px-4 py-2 -mb-px border-b-2 border-blue-500 text-blue-500 font-medium"
          : "px-4 py-2 text-gray-500 hover:text-gray-700"
      }
    >
      {children}
    </button>
  );
}

export function TabPanels({ children }) {
  const { active } = useContext(TabsContext);
  return (
    <>
      {children.map((panel) => (panel.props.value === active ? panel : null))}
    </>
  );
}

export function TabPanel({ value, children }) {
  return <div className="p-4">{children}</div>;
}

import { NavLink, Outlet } from "react-router-dom";
import {
  Books,
  ChartBar,
  GearSix,
  House,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import { EvalSettingsProvider } from "../state/EvalSettingsContext";

export default function SettingsLayout() {
  return (
    <EvalSettingsProvider>
      <div className="settings-shell">
        <aside className="settings-sidebar">
          <div className="brand-lockup">
            <strong>Call Desk</strong>
            <span>Settings</span>
          </div>
          <nav className="side-nav">
            <NavLink to="/settings/results" end>
              <ChartBar size={18} weight="bold" />
              Results
            </NavLink>
            <NavLink to="/settings/detailed-results">
              <MagnifyingGlass size={18} weight="bold" />
              Detailed results
            </NavLink>
            <NavLink to="/settings/knowledge">
              <Books size={18} weight="bold" />
              Knowledge
            </NavLink>
            <NavLink to="/settings/parameters">
              <GearSix size={18} weight="bold" />
              Parameters
            </NavLink>
          </nav>
          <div style={{ marginTop: "auto" }}>
            <NavLink to="/" className="link-quiet" style={{ color: "var(--sidebar-muted)" }}>
              <House size={16} weight="bold" />
              Back to call desk
            </NavLink>
          </div>
        </aside>
        <div className="settings-content">
          <Outlet />
        </div>
      </div>
    </EvalSettingsProvider>
  );
}

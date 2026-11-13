import { Link } from "react-router-dom";
import { GearSix } from "@phosphor-icons/react";
import CallPanel from "../components/CallPanel";

export default function HomePage() {
  return (
    <div className="user-shell">
      <header className="user-top">
        <div className="brand-lockup">
          <strong>Call Desk</strong>
          <span>Internee practice line</span>
        </div>
        <Link to="/settings" className="link-quiet">
          <GearSix size={16} weight="bold" />
          Settings
        </Link>
      </header>
      <main className="user-main">
        <div className="call-layout">
          <section className="panel call-copy stack">
            <div>
              <h1>Enter your name. Take the call.</h1>
              <p>
                Speak with the company AI agent. When you hang up, we score
                delivery and knowledge against the configured rubrics.
              </p>
            </div>
            <CallPanel />
          </section>
          <section className="panel panel-flush">
            <div className="call-stage" aria-hidden>
              <div className="call-stage-inner">
                <p
                  style={{
                    margin: "0 0 0.4rem",
                    fontFamily: "var(--mono)",
                    fontSize: "0.75rem",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    opacity: 0.75,
                  }}
                >
                  Live practice channel
                </p>
                <p style={{ margin: 0, fontFamily: "var(--display)", fontSize: "1.55rem" }}>
                  Mic on. Stay on script. Answer with company facts.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

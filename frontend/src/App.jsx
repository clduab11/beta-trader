import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";

function Playground() {
  return <div><h2>Playground</h2><p>Intel query interface — coming soon.</p></div>;
}

function ModelRotation() {
  return <div><h2>Model Rotation</h2><p>OpenRouter model rotation testing — coming soon.</p></div>;
}

function Settings() {
  return <div><h2>Settings</h2><p>API key configuration — coming soon.</p></div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <header style={{ padding: "1rem", borderBottom: "1px solid #333" }}>
        <nav style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <strong>Beta-Trader</strong>
          <NavLink to="/playground">Playground</NavLink>
          <NavLink to="/model-rotation">Model Rotation</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </header>
      <main style={{ padding: "1rem" }}>
        <Routes>
          <Route path="/" element={<Playground />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/model-rotation" element={<ModelRotation />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

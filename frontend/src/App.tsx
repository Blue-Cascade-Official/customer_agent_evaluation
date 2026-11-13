import { Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ResultsPage from "./pages/ResultsPage";
import DetailedResultsPage from "./pages/DetailedResultsPage";
import KnowledgePage from "./pages/KnowledgePage";
import ParametersPage from "./pages/ParametersPage";
import SettingsLayout from "./layouts/SettingsLayout";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/settings" element={<SettingsLayout />}>
        <Route index element={<Navigate to="results" replace />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="detailed-results" element={<DetailedResultsPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="parameters" element={<ParametersPage />} />
      </Route>
      <Route path="/results" element={<Navigate to="/settings/results" replace />} />
      <Route path="/knowledge" element={<Navigate to="/settings/knowledge" replace />} />
    </Routes>
  );
}

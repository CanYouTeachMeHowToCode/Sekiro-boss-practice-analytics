import { Route, Routes } from "react-router-dom";
import BossSelectionPage from "./pages/BossSelectionPage";
import BossDashboardPage from "./pages/BossDashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<BossSelectionPage />} />
      <Route path="/bosses/:bossId" element={<BossDashboardPage />} />
    </Routes>
  );
}

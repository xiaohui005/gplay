import { BrowserRouter, Routes, Route } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import DetailPage from './pages/DetailPage'
import TechnicalAnalysisPage from './pages/TechnicalAnalysisPage'
import AnalysisHistoryPage from './pages/AnalysisHistoryPage'
import SettingsPage from './pages/SettingsPage'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/stock/:symbol" element={<DetailPage />} />
        <Route path="/analysis/:symbol" element={<TechnicalAnalysisPage />} />
        <Route path="/analysis/history" element={<AnalysisHistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

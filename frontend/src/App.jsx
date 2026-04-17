import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import ImpactPage from './pages/ImpactPage'
import RisksPage from './pages/RisksPage'
import SimulationPage from './pages/SimulationPage'
import UploadPage from './pages/UploadPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/risks" element={<RisksPage />} />
        <Route path="/impact" element={<ImpactPage />} />
        <Route path="/simulation" element={<SimulationPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App

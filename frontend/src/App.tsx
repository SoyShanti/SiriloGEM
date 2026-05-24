import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import { Layout } from './components/Layout'
import { GeneratePage } from './pages/GeneratePage'
import { DiscoverPage } from './pages/DiscoverPage'
import { PredictPage } from './pages/PredictPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<GeneratePage />} />
            <Route path="/discover" element={<DiscoverPage />} />
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
      </AppProvider>
    </BrowserRouter>
  )
}

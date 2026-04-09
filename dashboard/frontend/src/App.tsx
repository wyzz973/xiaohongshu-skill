import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Monitor from './pages/Monitor'
import Content from './pages/Content'
import Interact from './pages/Interact'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="monitor" element={<Monitor />} />
        <Route path="content" element={<Content />} />
        <Route path="interact" element={<Interact />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

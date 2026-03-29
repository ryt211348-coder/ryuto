import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/dashboard/Dashboard'
import KPIDashboard from './components/kpi/KPIDashboard'
import TaskBoard from './components/tasks/TaskBoard'
import GooglePanel from './components/google/GooglePanel'
import AutomationCenter from './components/automation/AutomationCenter'
import CostManager from './components/cost/CostManager'
import WeeklyReport from './components/report/WeeklyReport'
import Settings from './components/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/kpi" element={<KPIDashboard />} />
        <Route path="/tasks" element={<TaskBoard />} />
        <Route path="/google" element={<GooglePanel />} />
        <Route path="/automation" element={<AutomationCenter />} />
        <Route path="/cost" element={<CostManager />} />
        <Route path="/report" element={<WeeklyReport />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

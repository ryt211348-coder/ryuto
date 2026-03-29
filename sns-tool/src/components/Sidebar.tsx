import { NavLink } from 'react-router-dom'

interface Props {
  isOpen: boolean
  onClose: () => void
}

const NAV_ITEMS = [
  { to: '/', label: 'ダッシュボード', icon: '📊' },
  { to: '/kpi', label: 'KPI管理', icon: '📈' },
  { to: '/tasks', label: 'タスクボード', icon: '✅' },
  { to: '/google', label: 'Google連携', icon: '📁' },
  { to: '/automation', label: 'AI自動化', icon: '🤖' },
  { to: '/cost', label: 'コスト管理', icon: '💰' },
  { to: '/report', label: '週次レポート', icon: '📋' },
  { to: '/settings', label: '設定', icon: '⚙️' },
]

export default function Sidebar({ isOpen, onClose }: Props) {
  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}
      <nav className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <span className="sidebar-logo">🚀</span>
          <span className="sidebar-brand">SNS AI Tool</span>
        </div>
        <ul className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                onClick={onClose}
                end={item.to === '/'}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="sidebar-footer">
          <p>りゅうと専用ツール</p>
          <p className="sidebar-version">v1.0.0 MVP</p>
        </div>
      </nav>
    </>
  )
}

import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import './BottomNav.css'

function BottomNav() {
  const location = useLocation()

  const isActive = (path) => {
    return location.pathname === path
  }

  return (
    <nav className="bottom-nav">
      <Link
        to="/scan"
        className={`nav-item ${isActive('/scan') ? 'active' : ''}`}
      >
        <span className="nav-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <circle cx="12" cy="13" r="4"></circle>
          </svg>
        </span>
        <span className="nav-label">Scan</span>
      </Link>
      <Link
        to="/bill"
        className={`nav-item ${isActive('/bill') ? 'active' : ''}`}
      >
        <span className="nav-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="1" x2="12" y2="23"></line>
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
          </svg>
        </span>
        <span className="nav-label">Bill</span>
      </Link>
      <Link
        to="/history"
        className={`nav-item ${isActive('/history') ? 'active' : ''}`}
      >
        <span className="nav-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </span>
        <span className="nav-label">History</span>
      </Link>
      <Link
        to="/statistics"
        className={`nav-item ${isActive('/statistics') ? 'active' : ''}`}
      >
        <span className="nav-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </span>
        <span className="nav-label">Stats</span>
      </Link>
    </nav>
  )
}

export default BottomNav







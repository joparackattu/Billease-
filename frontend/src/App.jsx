import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import ScanPage from './pages/ScanPage'
import BillPage from './pages/BillPage'
import HistoryPage from './pages/HistoryPage'
import LoginPage from './pages/LoginPage'
import PricePage from './pages/PricePage'
import StatisticsPage from './pages/StatisticsPage'
import BottomNav from './components/BottomNav'
import ProfileDropdown from './components/ProfileDropdown'
import './App.css'

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('authToken')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

// App Layout with Header and Bottom Nav
function AppLayout({ children }) {
  const location = useLocation()
  const [shopkeeper, setShopkeeper] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const isLoginPage = location.pathname === '/login'

  useEffect(() => {
    // Load shopkeeper info from localStorage
    const loadShopkeeper = async () => {
      const token = localStorage.getItem('authToken')
      const shopkeeperData = localStorage.getItem('shopkeeper')
      
      setIsAuthenticated(!!token)
      
      if (shopkeeperData) {
        try {
          const parsed = JSON.parse(shopkeeperData)
          setShopkeeper(parsed)
          
          // If billease_id is missing, try to refresh from server
          if (token && !parsed.billease_id) {
            try {
              const { getProfile } = await import('./api/backend')
              const result = await getProfile()
              if (result && result.shopkeeper && result.shopkeeper.billease_id) {
                localStorage.setItem('shopkeeper', JSON.stringify(result.shopkeeper))
                setShopkeeper(result.shopkeeper)
              }
            } catch (e) {
              console.error('Error refreshing shopkeeper data:', e)
            }
          }
        } catch (e) {
          console.error('Error parsing shopkeeper data:', e)
        }
      } else {
        setShopkeeper(null)
      }
    }
    
    loadShopkeeper()

    // Listen for storage changes (when login happens)
    const handleStorageChange = () => {
      loadShopkeeper()
    }

    // Listen for auth changes (custom event from login)
    const handleAuthChange = () => {
      loadShopkeeper()
    }

    window.addEventListener('storage', handleStorageChange)
    window.addEventListener('auth-change', handleAuthChange)
    
    // Also check on focus (in case login happened in same tab)
    window.addEventListener('focus', handleStorageChange)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('auth-change', handleAuthChange)
      window.removeEventListener('focus', handleStorageChange)
    }
  }, [])

  if (isLoginPage) {
    return <>{children}</>
  }

  // Profile Icon SVG
  const ProfileIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
      <circle cx="12" cy="7" r="4"></circle>
    </svg>
  )

  return (
    <div className="app-layout">
      {/* Header with Profile */}
      {shopkeeper && (
        <header className="app-header">
          <div className="header-content">
            <button 
              className="profile-button"
              onClick={() => setShowProfile(true)}
              title="Profile"
            >
              <ProfileIcon />
            </button>
            <div className="shop-info">
              <h2 className="shop-name">{shopkeeper.shop_name}</h2>
            </div>
            <div className="header-spacer"></div>
          </div>
        </header>
      )}
      
      <main className="app-main">
        {children}
      </main>
      
      {/* Bottom Navigation */}
      {isAuthenticated && <BottomNav />}

      {/* Profile Dropdown */}
      {showProfile && shopkeeper && (
        <ProfileDropdown 
          shopkeeper={shopkeeper} 
          onClose={() => setShowProfile(false)}
        />
      )}
    </div>
  )
}

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/scan" replace />} />
          <Route 
            path="/scan" 
            element={
              <ProtectedRoute>
                <ScanPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/bill" 
            element={
              <ProtectedRoute>
                <BillPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/history" 
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/prices" 
            element={
              <ProtectedRoute>
                <PricePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/statistics" 
            element={
              <ProtectedRoute>
                <StatisticsPage />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </AppLayout>
    </Router>
  )
}

export default App







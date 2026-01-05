import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { updateProfile, getProfile } from '../api/backend'
import './ProfileDropdown.css'

// SVG Icons
const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
)

const SettingsIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M12 1v6m0 6v6m9-9h-6m-6 0H3m15.364 6.364l-4.243-4.243m0-4.242l4.243-4.243M4.636 19.364l4.243-4.243m0-4.242L4.636 6.636"></path>
  </svg>
)

const LogoutIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
    <polyline points="16 17 21 12 16 7"></polyline>
    <line x1="21" y1="12" x2="9" y2="12"></line>
  </svg>
)

const CloseIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
)

const EditIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
  </svg>
)

const SaveIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
    <polyline points="17 21 17 13 7 13 7 21"></polyline>
    <polyline points="7 3 7 8 15 8"></polyline>
  </svg>
)

const XIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
)

const ChartIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
)

const UsersIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
    <circle cx="9" cy="7" r="4"></circle>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
  </svg>
)

function ProfileDropdown({ shopkeeper, onClose }) {
  const navigate = useNavigate()
  const dropdownRef = useRef(null)
  const [currentView, setCurrentView] = useState('menu') // 'menu', 'edit'
  const [loading, setLoading] = useState(false)
  const [localShopkeeper, setLocalShopkeeper] = useState(shopkeeper)
  const [formData, setFormData] = useState({
    shop_name: shopkeeper.shop_name || '',
    email: shopkeeper.email || '',
    phone: shopkeeper.phone || ''
  })
  const [error, setError] = useState('')
  
  // Update local shopkeeper when prop changes
  useEffect(() => {
    setLocalShopkeeper(shopkeeper)
  }, [shopkeeper])

  useEffect(() => {
    // Always refresh shopkeeper data to ensure we have billease_id
    const refreshShopkeeperData = async () => {
      try {
        console.log('Refreshing shopkeeper data to get billease_id...')
        const result = await getProfile()
        console.log('Profile data received:', result)
        if (result && result.shopkeeper) {
          console.log('Billease ID:', result.shopkeeper.billease_id)
          // Update localStorage with fresh data
          localStorage.setItem('shopkeeper', JSON.stringify(result.shopkeeper))
          setLocalShopkeeper(result.shopkeeper)
          window.dispatchEvent(new Event('auth-change'))
        }
      } catch (error) {
        console.error('Error refreshing shopkeeper data:', error)
        // If refresh fails, keep using existing data
      }
    }
    
    // Refresh when component mounts
    refreshShopkeeperData()

    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        onClose()
      }
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
    }, [onClose])

  const handleEdit = () => {
    setCurrentView('edit')
    setError('')
  }

  const handleBackToMenu = () => {
    setCurrentView('menu')
    setFormData({
      shop_name: shopkeeper.shop_name || '',
      email: shopkeeper.email || '',
      phone: shopkeeper.phone || ''
    })
    setError('')
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    setError('')
  }

  const handleSave = async () => {
    if (!formData.shop_name.trim()) {
      setError('Shop name is required')
      return
    }

    try {
      setLoading(true)
      setError('')
      const result = await updateProfile(formData)
      
      // Update localStorage with new shopkeeper data
      localStorage.setItem('shopkeeper', JSON.stringify(result.shopkeeper))
      setLocalShopkeeper(result.shopkeeper)
      window.dispatchEvent(new Event('auth-change'))
      
      setCurrentView('menu')
      alert('Profile updated successfully!')
    } catch (err) {
      console.error('Update profile error:', err)
      setError(err.response?.data?.detail || 'Failed to update profile. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleManagePrices = () => {
    navigate('/prices')
    onClose()
  }

  const handleAccounts = () => {
    // Placeholder - will be designed later
    alert('Accounts page coming soon!')
  }

  const handleAnalytics = () => {
    // Placeholder - will be designed later
    alert('Analytics page coming soon!')
  }

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('shopkeeper')
    window.dispatchEvent(new Event('auth-change'))
    navigate('/login')
  }

  // Get owner name (username or email)
  const ownerName = localShopkeeper.username || localShopkeeper.email || 'Owner'

  return (
    <div className="profile-side-menu-overlay" onClick={onClose}>
      <div className="profile-side-menu" ref={dropdownRef} onClick={(e) => e.stopPropagation()}>
        {/* Header with Shop Name and Owner Name */}
        <div className="profile-side-menu-header">
          <button className="close-button" onClick={onClose}>
            <CloseIcon />
          </button>
          <div className="shop-owner-info">
            <h2 className="shop-name">{localShopkeeper.shop_name}</h2>
            <p className="billease-id">ID: {localShopkeeper.billease_id || 'Loading...'}</p>
            <p className="owner-name">
              <span className="owner-label">Owner:</span> {ownerName}
            </p>
          </div>
        </div>

        {/* Menu Content */}
        <div className="profile-side-menu-content">
          {currentView === 'menu' ? (
            <div className="menu-items">
              <button className="menu-item" onClick={handleEdit}>
                <EditIcon />
                <span>Edit Profile</span>
              </button>
              <button className="menu-item" onClick={handleManagePrices}>
                <SettingsIcon />
                <span>Manage Prices</span>
              </button>
              <button className="menu-item" onClick={handleAccounts}>
                <UsersIcon />
                <span>Accounts</span>
              </button>
              <button className="menu-item" onClick={handleAnalytics}>
                <ChartIcon />
                <span>Analytics</span>
              </button>
              <button className="menu-item menu-item-logout" onClick={handleLogout}>
                <LogoutIcon />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <div className="edit-profile-view">
              <div className="edit-header">
                <button className="back-button" onClick={handleBackToMenu}>
                  ← Back
                </button>
                <h3>Edit Profile</h3>
              </div>
              
              <div className="edit-content">
                {error && <div className="profile-error">{error}</div>}
                
                <div className="profile-info-item">
                  <label>Shop Name *</label>
                  <input
                    type="text"
                    name="shop_name"
                    value={formData.shop_name}
                    onChange={handleChange}
                    className="profile-input"
                    required
                    placeholder="Enter shop name"
                  />
                </div>
                
                <div className="profile-info-item">
                  <label>Username</label>
                  <div className="profile-info-value profile-readonly">@{localShopkeeper.username}</div>
                  <small className="profile-hint">Username cannot be changed</small>
                </div>
                
                <div className="profile-info-item">
                  <label>Email</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="profile-input"
                    placeholder="Enter email (optional)"
                  />
                </div>
                
                <div className="profile-info-item">
                  <label>Phone</label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    className="profile-input"
                    placeholder="Enter phone number (optional)"
                  />
                </div>

                <div className="profile-edit-actions">
                  <button 
                    className="profile-cancel-button" 
                    onClick={handleBackToMenu}
                    disabled={loading}
                  >
                    <XIcon />
                    <span>Cancel</span>
                  </button>
                  <button 
                    className="profile-save-button" 
                    onClick={handleSave}
                    disabled={loading}
                  >
                    <SaveIcon />
                    <span>{loading ? 'Saving...' : 'Save'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProfileDropdown

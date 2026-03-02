import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api/backend'
import { UserIcon, LoaderIcon } from '../components/Icons'
import './LoginPage.css'

// Get API URL for debugging
const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`

function LoginPage() {
  const navigate = useNavigate()
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    shop_name: '',
    email: '',
    phone: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    setError('')
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await login(formData.username, formData.password)
      
      // Validate response structure
      if (!result || !result.token || !result.shopkeeper) {
        setError('Invalid response from server. Please try again.')
        setLoading(false)
        return
      }
      
      localStorage.setItem('authToken', result.token)
      localStorage.setItem('shopkeeper', JSON.stringify(result.shopkeeper))
      window.dispatchEvent(new Event('auth-change'))
      navigate('/scan')
    } catch (err) {
      console.error('Login error details:', err)
      
      // Handle different types of errors
      if (err.code === 'ECONNREFUSED' || err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Cannot connect to server. Please make sure the backend is running.')
      } else if (err.response) {
        // Server responded with error
        const status = err.response.status
        if (status === 401) {
          setError('Invalid username or password. Please try again.')
        } else if (status === 500) {
          setError('Server error. Please try again later.')
        } else {
          setError(err.response?.data?.detail || `Login failed (${status}). Please try again.`)
        }
      } else if (err.request) {
        // Request was made but no response received
        setError('No response from server. Please check your connection and try again.')
      } else {
        // Something else happened
        setError(err.message || 'Login failed. Please check your credentials and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  // Validation functions
  const validateEmail = (email) => {
    if (!email || email.trim() === '') return true // Optional field
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const validatePhone = (phone) => {
    if (!phone || phone.trim() === '') return true // Optional field
    // Remove spaces, dashes, parentheses, and plus signs for validation
    const cleaned = phone.replace(/[\s\-\(\)\+]/g, '')
    // Indian phone: 10 digits, optionally with country code 91
    const phoneRegex = /^(91)?[6-9]\d{9}$/
    return phoneRegex.test(cleaned) && cleaned.length >= 10 && cleaned.length <= 12
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters')
      setLoading(false)
      return
    }

    // Validate email if provided
    if (formData.email && !validateEmail(formData.email)) {
      setError('Please enter a valid email address')
      setLoading(false)
      return
    }

    // Validate phone if provided
    if (formData.phone && !validatePhone(formData.phone)) {
      setError('Please enter a valid phone number (10 digits, Indian format)')
      setLoading(false)
      return
    }

    try {
      await register(formData)
      setIsLogin(true)
      setError('')
      alert('Registration successful! Please login.')
      setFormData({ ...formData, password: '' })
      window.dispatchEvent(new Event('auth-change'))
    } catch (err) {
      console.error('Registration error details:', err)
      
      // Handle different types of errors
      if (err.code === 'ECONNREFUSED' || err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Cannot connect to server. Please make sure the backend is running.')
      } else if (err.response) {
        // Server responded with error
        const status = err.response.status
        if (status === 400 || status === 409) {
          setError(err.response?.data?.detail || 'Registration failed. Username may already exist.')
        } else if (status === 500) {
          setError('Server error. Please try again later.')
        } else {
          setError(err.response?.data?.detail || `Registration failed (${status}). Please try again.`)
        }
      } else if (err.request) {
        // Request was made but no response received
        setError('No response from server. Please check your connection and try again.')
      } else {
        // Something else happened
        setError(err.message || 'Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="logo-icon">
            <UserIcon size={48} />
          </div>
          <h1>BILLESE</h1>
          <p>Smart Billing System</p>
        </div>

        <div className="login-tabs">
          <button
            className={isLogin ? 'active' : ''}
            onClick={() => setIsLogin(true)}
          >
            Login
          </button>
          <button
            className={!isLogin ? 'active' : ''}
            onClick={() => setIsLogin(false)}
          >
            Register
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={isLogin ? handleLogin : handleRegister}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="Enter username"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Enter password"
              minLength={6}
            />
          </div>

          {!isLogin && (
            <>
              <div className="form-group">
                <label>Shop Name</label>
                <input
                  type="text"
                  name="shop_name"
                  value={formData.shop_name}
                  onChange={handleChange}
                  required
                  placeholder="Enter shop name"
                />
              </div>

              <div className="form-group">
                <label>Email (Optional)</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Enter email"
                />
              </div>

              <div className="form-group">
                <label>Phone (Optional)</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="Enter phone number"
                />
              </div>
            </>
          )}

          <button
            type="submit"
            className="submit-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <LoaderIcon size={20} className="spinner" />
                <span>Processing...</span>
              </>
            ) : (
              <span>{isLogin ? 'Login' : 'Register'}</span>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage

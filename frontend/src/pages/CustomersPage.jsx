import React, { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getAllCustomers, createCustomer, deleteCustomer } from '../api/backend'
import { UsersIcon, LoaderIcon, XIcon, PhoneIcon } from '../components/Icons'
import './CustomersPage.css'

function CustomersPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [allCustomers, setAllCustomers] = useState([])
  const [loadingCustomers, setLoadingCustomers] = useState(true)
  const [showAddCustomerForm, setShowAddCustomerForm] = useState(false)
  const [newCustomerName, setNewCustomerName] = useState('')
  const [newCustomerPhone, setNewCustomerPhone] = useState('')
  const [addingCustomer, setAddingCustomer] = useState(false)
  const [deletingCustomerId, setDeletingCustomerId] = useState(null)
  const lastPathRef = useRef(null)
  const touchStartX = useRef(null)
  const touchEndX = useRef(null)

  const loadAllCustomers = async (background = false) => {
    try {
      if (!background) {
        setLoadingCustomers(true)
      }
      const data = await getAllCustomers()
      const customersData = data.customers || []
      setAllCustomers(customersData)
      // Cache the data
      sessionStorage.setItem('allCustomers', JSON.stringify(customersData))
      sessionStorage.setItem('allCustomersTime', Date.now().toString())
    } catch (error) {
      console.error('Error loading all customers:', error)
      console.error('Error response:', error.response?.data)
      if (!background) {
        // Show error message to help debug
        console.error('Full error:', error)
        setAllCustomers([])
        // Don't show alert on initial load to avoid annoying users
        // But log it for debugging
      }
    } finally {
      if (!background) {
        setLoadingCustomers(false)
      }
    }
  }

  useEffect(() => {
    // Load from cache first
    const cachedData = sessionStorage.getItem('allCustomers')
    const cacheTime = sessionStorage.getItem('allCustomersTime')
    const now = Date.now()
    const CACHE_DURATION = 2 * 60 * 1000 // 2 minutes
    
    if (cachedData && cacheTime && (now - parseInt(cacheTime)) < CACHE_DURATION) {
      try {
        setAllCustomers(JSON.parse(cachedData))
        setLoadingCustomers(false)
        // Load fresh data in background
        loadAllCustomers(true)
        return
      } catch (e) {
        console.error('Error parsing cached customers:', e)
      }
    }
    
    // Only load if this is a new navigation to this page
    if (lastPathRef.current !== location.pathname) {
      lastPathRef.current = location.pathname
      loadAllCustomers(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  // Swipe gesture handlers - swipe left to right to go back to accounts
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX
  }

  const handleTouchMove = (e) => {
    touchEndX.current = e.touches[0].clientX
  }

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return
    
    const swipeDistance = touchEndX.current - touchStartX.current
    const minSwipeDistance = 50 // Minimum distance for a swipe
    
    // Swipe from left to right (navigate back to accounts page)
    if (swipeDistance > minSwipeDistance) {
      navigate('/accounts')
    }
    
    // Reset
    touchStartX.current = null
    touchEndX.current = null
  }

  const handleAddCustomer = async (e) => {
    e.preventDefault()
    
    if (!newCustomerName.trim()) {
      alert('Customer name is required')
      return
    }
    
    if (!newCustomerPhone.trim()) {
      alert('Customer phone is required')
      return
    }

    try {
      setAddingCustomer(true)
      await createCustomer(newCustomerName.trim(), newCustomerPhone.trim())
      
      // Clear cache and reload customers list
      sessionStorage.removeItem('allCustomers')
      sessionStorage.removeItem('allCustomersTime')
      await loadAllCustomers(false)
      
      // Clear form
      setNewCustomerName('')
      setNewCustomerPhone('')
      setShowAddCustomerForm(false)
      
      alert('Customer added successfully!')
    } catch (error) {
      console.error('Error adding customer:', error)
      alert(`Failed to add customer: ${error.response?.data?.detail || error.message}`)
    } finally {
      setAddingCustomer(false)
    }
  }

  const handleDeleteCustomer = async (customerId, customerName) => {
    if (!confirm(`Are you sure you want to delete customer "${customerName}"?`)) {
      return
    }

    try {
      setDeletingCustomerId(customerId)
      await deleteCustomer(customerId)
      
      // Clear cache and reload customers list
      sessionStorage.removeItem('allCustomers')
      sessionStorage.removeItem('allCustomersTime')
      await loadAllCustomers(false)
      
      alert('Customer deleted successfully!')
    } catch (error) {
      console.error('Error deleting customer:', error)
      alert(`Failed to delete customer: ${error.response?.data?.detail || error.message}`)
    } finally {
      setDeletingCustomerId(null)
    }
  }

  return (
    <div 
      className="customers-page"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <div className="page-header">
        <UsersIcon size={28} className="page-header-icon" />
        <h1>Customers</h1>
      </div>

      {loadingCustomers ? (
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading customers...</p>
        </div>
      ) : (
        <div className="customers-content">
        <div className="customers-actions">
          <button 
            className="add-customer-button"
            onClick={() => setShowAddCustomerForm(!showAddCustomerForm)}
          >
            + Add Customer
          </button>
        </div>

        {showAddCustomerForm && (
          <form className="add-customer-form" onSubmit={handleAddCustomer}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={newCustomerName}
                onChange={(e) => setNewCustomerName(e.target.value)}
                placeholder="Enter customer name"
                required
              />
            </div>
            <div className="form-group">
              <label>Phone *</label>
              <input
                type="tel"
                value={newCustomerPhone}
                onChange={(e) => setNewCustomerPhone(e.target.value)}
                placeholder="Enter phone number"
                required
              />
            </div>
            <div className="form-actions">
              <button 
                type="button" 
                className="cancel-button"
                onClick={() => {
                  setShowAddCustomerForm(false)
                  setNewCustomerName('')
                  setNewCustomerPhone('')
                }}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="save-button"
                disabled={addingCustomer}
              >
                {addingCustomer ? 'Adding...' : 'Add Customer'}
              </button>
            </div>
          </form>
        )}

        {allCustomers.length === 0 ? (
          <div className="empty-state">
            <UsersIcon size={48} className="empty-icon" />
            <p>No customers found</p>
            <p className="empty-hint">Add your first customer to get started</p>
          </div>
        ) : (
          <div className="all-customers-list">
            {allCustomers.map((customer) => (
              <div key={customer.id} className="customer-item">
                <div className="customer-item-info">
                  <div className="customer-item-name">{customer.name}</div>
                  <div className="customer-item-phone">
                    <PhoneIcon size={14} />
                    <span>{customer.phone}</span>
                  </div>
                </div>
                <button
                  className="delete-customer-button"
                  onClick={() => handleDeleteCustomer(customer.id, customer.name)}
                  disabled={deletingCustomerId === customer.id}
                >
                  {deletingCustomerId === customer.id ? (
                    <LoaderIcon size={16} className="spinner" />
                  ) : (
                    <XIcon size={16} />
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
        </div>
      )}
    </div>
  )
}

export default CustomersPage


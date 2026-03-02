import React, { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getCustomersWithPending, getCustomerUnpaidBills, markBillAsPaid } from '../api/backend'
import { DollarIcon, LoaderIcon, XIcon, PhoneIcon, CheckIcon } from '../components/Icons'
import './AccountsPage.css'

function AccountsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCustomer, setSelectedCustomer] = useState(null)
  const [customerBills, setCustomerBills] = useState([])
  const [loadingBills, setLoadingBills] = useState(false)
  const [markingPaid, setMarkingPaid] = useState(false)
  const lastPathRef = useRef(null)
  const touchStartX = useRef(null)
  const touchEndX = useRef(null)

  useEffect(() => {
    // Load from cache first
    const cachedData = sessionStorage.getItem('accountsCustomers')
    const cacheTime = sessionStorage.getItem('accountsCustomersTime')
    const now = Date.now()
    const CACHE_DURATION = 2 * 60 * 1000 // 2 minutes (accounts change more frequently)
    
    if (cachedData && cacheTime && (now - parseInt(cacheTime)) < CACHE_DURATION) {
      try {
        setCustomers(JSON.parse(cachedData))
        setLoading(false)
        // Load fresh data in background
        loadCustomers(true)
        return
      } catch (e) {
        console.error('Error parsing cached customers:', e)
      }
    }
    
    // Only load if this is a new navigation to this page
    if (lastPathRef.current !== location.pathname) {
      lastPathRef.current = location.pathname
      loadCustomers(false)
    }
  }, [location.pathname])

  // Swipe gesture handlers
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX
  }

  const handleTouchMove = (e) => {
    touchEndX.current = e.touches[0].clientX
  }

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return
    
    const swipeDistance = touchStartX.current - touchEndX.current
    const minSwipeDistance = 50 // Minimum distance for a swipe
    
    // Swipe from right to left (navigate to customers page)
    if (swipeDistance > minSwipeDistance) {
      navigate('/customers')
    }
    
    // Reset
    touchStartX.current = null
    touchEndX.current = null
  }

  const loadCustomers = async (background = false) => {
    try {
      if (!background) {
        setLoading(true)
      }
      const data = await getCustomersWithPending()
      console.log('Customers data received:', data)
      const customersData = data.customers || []
      setCustomers(customersData)
      // Cache the data
      sessionStorage.setItem('accountsCustomers', JSON.stringify(customersData))
      sessionStorage.setItem('accountsCustomersTime', Date.now().toString())
      if (!customersData || customersData.length === 0) {
        console.log('No customers with pending bills found')
      }
    } catch (error) {
      console.error('Error loading customers:', error)
      console.error('Error details:', error.response?.data || error.message)
      // If offline, try to use cached data
      const cachedData = sessionStorage.getItem('accountsCustomers')
      if (cachedData && !navigator.onLine) {
        try {
          setCustomers(JSON.parse(cachedData))
          return
        } catch (e) {
          console.error('Error parsing cached customers:', e)
        }
      }
      if (error.response?.status !== 401 && !background) {
        alert(`Failed to load customers: ${error.response?.data?.detail || error.message || 'Unknown error'}`)
      }
      if (!background) {
        setCustomers([])
      }
    } finally {
      if (!background) {
        setLoading(false)
      }
    }
  }

  const handleCustomerClick = async (customer) => {
    try {
      setLoadingBills(true)
      setSelectedCustomer(customer)
      const data = await getCustomerUnpaidBills(customer.id)
      setCustomerBills(data.bills || [])
    } catch (error) {
      console.error('Error loading customer bills:', error)
      alert('Failed to load customer bills. Please try again.')
      setCustomerBills([])
    } finally {
      setLoadingBills(false)
    }
  }

  const handleCloseBills = () => {
    setSelectedCustomer(null)
    setCustomerBills([])
  }

  const handleMarkAsPaid = async () => {
    if (!selectedCustomer || customerBills.length === 0) return
    
    if (!confirm(`Mark all ${customerBills.length} bill(s) as paid for ${selectedCustomer.name}?`)) {
      return
    }

    try {
      setMarkingPaid(true)
      // Mark all bills as paid
      for (const bill of customerBills) {
        await markBillAsPaid(bill.id)
      }
      
      // Clear cache and reload customers list
      sessionStorage.removeItem('accountsCustomers')
      sessionStorage.removeItem('accountsCustomersTime')
      await loadCustomers(false)
      
      // Close the modal
      handleCloseBills()
      
      alert('All bills marked as paid successfully!')
    } catch (error) {
      console.error('Error marking bills as paid:', error)
      alert(`Failed to mark bills as paid: ${error.response?.data?.detail || error.message}`)
    } finally {
      setMarkingPaid(false)
    }
  }

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch (e) {
      return dateString
    }
  }

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₹0.00'
    return `₹${parseFloat(amount).toFixed(2)}`
  }

  if (loading) {
    return (
      <div className="accounts-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading customers...</p>
        </div>
      </div>
    )
  }

  return (
    <div 
      className="accounts-page"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <div className="page-header">
        <DollarIcon size={28} className="page-header-icon" />
        <h1>Accounts</h1>
      </div>

      {customers.length === 0 ? (
        <div className="empty-state">
          <DollarIcon size={48} className="empty-icon" />
          <p>No pending accounts</p>
          <p className="empty-hint">Create unpaid bills during checkout to see them here</p>
        </div>
      ) : (
        <div className="customers-list">
          {customers.map((customer) => (
            <div
              key={customer.id}
              className="customer-card"
              onClick={() => handleCustomerClick(customer)}
            >
              <div className="customer-info">
                <div className="customer-name">{customer.name}</div>
                <div className="customer-phone">
                  <PhoneIcon size={16} />
                  <span>{customer.phone}</span>
                </div>
              </div>
              <div className="customer-pending">
                <div className="pending-amount">{formatCurrency(customer.pending_amount)}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Customer Bills Modal */}
      {selectedCustomer && (
        <div className="bills-modal-overlay" onClick={handleCloseBills}>
          <div className="bills-modal" onClick={(e) => e.stopPropagation()}>
            <div className="bills-modal-header">
              <h2>{selectedCustomer.name} - Unpaid Bills</h2>
              <button className="bills-modal-close" onClick={handleCloseBills}>
                <XIcon size={20} />
              </button>
            </div>
            <div className="bills-modal-content">
              {loadingBills ? (
                <div className="loading-state">
                  <LoaderIcon size={24} className="spinner" />
                  <p>Loading bills...</p>
                </div>
              ) : customerBills.length === 0 ? (
                <div className="empty-state">
                  <p>No unpaid bills found</p>
                </div>
              ) : (
                <>
                  <div className="bills-list">
                    {customerBills.map((bill) => (
                      <div key={bill.id} className="bill-card">
                        <div className="bill-header">
                          <div className="bill-number">{bill.bill_number}</div>
                          <div className="bill-date">{formatDate(bill.created_at)}</div>
                        </div>
                        <div className="bill-total">
                          <span>Total:</span>
                          <span>{formatCurrency(bill.total_amount)}</span>
                        </div>
                      </div>
                    ))}
                    <div className="total-pending">
                      <span>Total Pending:</span>
                      <span>{formatCurrency(selectedCustomer.pending_amount)}</span>
                    </div>
                  </div>
                  <div className="bills-modal-actions">
                    <button
                      onClick={handleMarkAsPaid}
                      className="mark-paid-button"
                      disabled={markingPaid || customerBills.length === 0}
                    >
                      {markingPaid ? (
                        <>
                          <LoaderIcon size={18} className="spinner" />
                          <span>Marking as Paid...</span>
                        </>
                      ) : (
                        <>
                          <CheckIcon size={18} />
                          <span>Mark as Paid</span>
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AccountsPage


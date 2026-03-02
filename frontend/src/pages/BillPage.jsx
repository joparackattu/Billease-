import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBill, clearBill, saveBill, removeBillItem, updateBillItem, updateBillItemQuantity, getAllItems, addItemToBill } from '../api/backend'
import { DollarIcon, EditIcon, TrashIcon, SaveIcon, XIcon, ShoppingCartIcon, LoaderIcon, CheckIcon, PhoneIcon, PlusIcon, MinusIcon, SearchIcon } from '../components/Icons'
import './BillPage.css'

function BillPage() {
  const navigate = useNavigate()
  const [bill, setBill] = useState(null)
  const [loading, setLoading] = useState(true)
  const [checkingOut, setCheckingOut] = useState(false)
  const [editingIndex, setEditingIndex] = useState(null)
  const [editWeight, setEditWeight] = useState('')
  const [showCheckoutModal, setShowCheckoutModal] = useState(false)
  const [customerPhone, setCustomerPhone] = useState('')
  const [isUnpaid, setIsUnpaid] = useState(false)
  const [customerName, setCustomerName] = useState('')
  const [shopkeeper, setShopkeeper] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingItemIndex, setEditingItemIndex] = useState(null)
  const [editingItemName, setEditingItemName] = useState('')
  const [showAddItemModal, setShowAddItemModal] = useState(false)
  const [availableItems, setAvailableItems] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [loadingItems, setLoadingItems] = useState(false)

  useEffect(() => {
    // Load bill on component mount
    loadBill()
    
    // Load shopkeeper info for bill header
    const shopkeeperData = localStorage.getItem('shopkeeper')
    if (shopkeeperData) {
      try {
        setShopkeeper(JSON.parse(shopkeeperData))
      } catch (e) {
        console.error('Error parsing shopkeeper data:', e)
      }
    }

    // Listen for items being added from scanning
    const handleItemDetected = () => {
      // Refresh bill when an item is detected and added
      loadBill(false) // Don't show loading spinner
    }
    window.addEventListener('itemDetected', handleItemDetected)

    // Debounced focus handler - only refresh if page was hidden for more than 5 seconds
    let lastHiddenTime = 0
    const handleVisibilityChange = () => {
      if (document.hidden) {
        lastHiddenTime = Date.now()
      } else {
        // Only refresh if page was hidden for more than 5 seconds
        if (Date.now() - lastHiddenTime > 5000) {
          loadBill(false)
        }
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('itemDetected', handleItemDetected)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  const loadBill = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      const billData = await getBill()
      setBill(billData)
    } catch (error) {
      console.error('Error loading bill:', error)
      setBill({ items: [], total: 0 })
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  // Format bill as WhatsApp message
  const formatBillForWhatsApp = (billData, billNumber, totalAmount) => {
    const shopName = shopkeeper?.shop_name || 'BILLESE Store'
    const date = new Date().toLocaleDateString('en-IN', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
    const time = new Date().toLocaleTimeString('en-IN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
    
    let message = `*${shopName}*\n`
    message += ` Bill Receipt\n\n`
    message += `Bill No: ${billNumber}\n`
    message += `Date: ${date} ${time}\n`
    message += `━━━━━━━━━━━━━━━\n\n`
    message += `*Items:*\n`
    
    billData.items.forEach((item, index) => {
      const pricingType = item.pricing_type || 'kg'
      const quantity = item.quantity || 1
      
      message += `${index + 1}. ${item.item_name.charAt(0).toUpperCase() + item.item_name.slice(1)}\n`
      
      if (pricingType === 'units' || pricingType === 'piece') {
        // Per unit/piece items
        const unitLabel = quantity === 1 ? 'unit' : 'units'
        message += `   ${quantity} ${unitLabel} × ₹${item.price_per_kg}/unit = ₹${item.total_price.toFixed(2)}\n\n`
      } else if (pricingType === 'ltr') {
        // Per litre items
        const litres = (item.weight_grams / 1000).toFixed(3)
        message += `   ${litres} litre${litres === '1.000' ? '' : 's'} × ₹${item.price_per_kg}/litre = ₹${item.total_price.toFixed(2)}\n\n`
      } else {
        // Per kg items (default)
        const weightKg = (item.weight_grams / 1000).toFixed(3)
        message += `   ${weightKg} kg × ₹${item.price_per_kg}/kg = ₹${item.total_price.toFixed(2)}\n\n`
      }
    })
    
    const subtotalWhatsApp = billData.items.reduce((s, i) => s + (i.total_price || 0), 0)
    const gstWhatsApp = billData.items.reduce((s, i) => s + (i.gst_amount || 0), 0)
    message += `━━━━━━━━━━━━━━━\n`
    message += `Subtotal: ₹${subtotalWhatsApp.toFixed(2)}\n`
    if (gstWhatsApp > 0) {
      message += `GST: ₹${gstWhatsApp.toFixed(2)}\n`
    }
    message += `*Total: ₹${totalAmount.toFixed(2)}*\n\n`
    message += `Thank you for your purchase! `
    
    return encodeURIComponent(message)
  }

  // Detect if device is mobile
  const isMobileDevice = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           (window.matchMedia && window.matchMedia('(max-width: 768px)').matches)
  }

  // Send bill via WhatsApp
  const sendBillViaWhatsApp = (phoneNumber, message) => {
    // Clean phone number (remove spaces, dashes, etc.)
    const cleanPhone = phoneNumber.replace(/[\s\-\(\)]/g, '')
    
    // Ensure phone number starts with country code (default to +91 for India)
    let formattedPhone = cleanPhone
    if (!formattedPhone.startsWith('+')) {
      // If it starts with 0, remove it
      if (formattedPhone.startsWith('0')) {
        formattedPhone = formattedPhone.substring(1)
      }
      // Add +91 if it doesn't start with country code
      if (!formattedPhone.startsWith('91')) {
        formattedPhone = '91' + formattedPhone
      }
      formattedPhone = '+' + formattedPhone
    }
    
    // Remove + from phone number for URL
    const phoneForUrl = formattedPhone.replace('+', '')
    
    // Create WhatsApp link - wa.me automatically opens native app on mobile
    const whatsappUrl = `https://wa.me/${phoneForUrl}?text=${message}`
    
    // On mobile devices, use location.href to open native WhatsApp app
    // On desktop, open WhatsApp Web in new tab
    if (isMobileDevice()) {
      // On mobile, this will open the native WhatsApp app directly
      // The browser will handle opening the app, and user can return to the page
      window.location.href = whatsappUrl
      
      // Optional: After a delay, try to return to the page if WhatsApp didn't open
      // (This handles cases where WhatsApp might not be installed)
      setTimeout(() => {
        // If we're still on the page after 2 seconds, WhatsApp might not have opened
        // In that case, we could show a message, but usually the app opens immediately
      }, 2000)
    } else {
      // On desktop, open WhatsApp Web in new tab
      window.open(whatsappUrl, '_blank')
    }
  }

  const handleCheckoutClick = () => {
    if (!bill || bill.items.length === 0) {
      alert('Bill is empty!')
      return
    }
    setShowCheckoutModal(true)
  }

  const handleCheckout = async () => {
    if (!bill || bill.items.length === 0) {
      alert('Bill is empty!')
      return
    }

    // Check if user is authenticated before attempting checkout
    const token = localStorage.getItem('authToken')
    if (!token) {
      alert('Please login to save bills.')
      navigate('/login')
      return
    }

    // Validate unpaid requirements
    if (isUnpaid) {
      if (!customerName.trim()) {
        alert('Please enter customer name for unpaid bills')
        return
      }
      // Phone is optional - will be looked up from customer name if not provided
    }

    try {
      setCheckingOut(true)
      // Always pass customer info if provided (for both paid and unpaid bills)
      const customerNameToPass = customerName.trim() || null
      const customerPhoneToPass = customerPhone.trim() || null
      const result = await saveBill('default', isUnpaid, customerNameToPass, customerPhoneToPass)
      
      const totalAmount = bill.items.reduce((sum, item) => sum + item.total_price, 0)
      const hasPhoneNumber = customerPhone.trim()
      
      // If phone number is provided, send via WhatsApp
      if (hasPhoneNumber) {
        const message = formatBillForWhatsApp(bill, result.bill_number, totalAmount)
        sendBillViaWhatsApp(customerPhone.trim(), message)
        
        // On mobile, give WhatsApp time to open before navigating
        if (isMobileDevice()) {
          // Wait a bit for WhatsApp to open, then navigate
          setTimeout(() => {
            setCheckingOut(false)
            setShowCheckoutModal(false)
            setCustomerPhone('')
            setIsUnpaid(false)
            setCustomerName('')
            navigate('/history')
          }, 500)
          return // Exit early, navigation will happen in setTimeout
        }
      }
      
      setCheckingOut(false)
      setShowCheckoutModal(false)
      setCustomerPhone('')
      setIsUnpaid(false)
      setCustomerName('')
      
      // Clear customers cache so it refreshes when navigating to customers page
      sessionStorage.removeItem('allCustomers')
      sessionStorage.removeItem('allCustomersTime')
      
      navigate('/history')
    } catch (error) {
      console.error('Save bill error:', error)
      // Handle authentication errors
      if (error.response?.status === 401 || error.message?.includes('session has expired') || error.message?.includes('expired')) {
        alert('Your session has expired. Please login again to save bills.')
        navigate('/login')
      } else {
        const errorMsg = error.response?.data?.detail || error.message || 'Failed to save bill. Please try again.'
        // If customer not found, suggest adding phone number
        if (errorMsg.includes('Customer not found') && isUnpaid) {
          alert(`Customer not found. Please provide phone number for new customers.\n\nError: ${errorMsg}`)
        } else {
          alert(`Failed to save bill: ${errorMsg}`)
        }
      }
    } finally {
      setCheckingOut(false)
    }
  }

  const handleCancelCheckout = () => {
    setShowCheckoutModal(false)
    setCustomerPhone('')
  }

  const handleClear = async () => {
    if (!bill || bill.items.length === 0) return

    try {
      await clearBill()
      await loadBill(false) // Don't show loading spinner for updates
    } catch (error) {
      console.error('Clear error:', error)
      alert('Failed to clear bill.')
    }
  }

  const handleRemoveItem = async (index) => {
    try {
      await removeBillItem('default', index)
      await loadBill(false) // Don't show loading spinner for updates
    } catch (error) {
      console.error('Remove item error:', error)
      alert('Failed to remove item.')
    }
  }

  const handleStartEdit = (item, index) => {
    setEditingItemIndex(index)
    setEditingItemName(item.item_name)
    setEditWeight(item.weight_grams.toString())
    setShowEditModal(true)
  }

  const handleCancelEdit = () => {
    setShowEditModal(false)
    setEditingIndex(null)
    setEditingItemIndex(null)
    setEditingItemName('')
    setEditWeight('')
  }

  const handleSaveEdit = async () => {
    if (!editWeight || parseFloat(editWeight) <= 0) {
      alert('Please enter a valid weight')
      return
    }

    try {
      await updateBillItem('default', editingItemIndex, parseFloat(editWeight))
      await loadBill(false) // Don't show loading spinner for updates
      handleCancelEdit()
    } catch (error) {
      console.error('Update item error:', error)
      alert('Failed to update item.')
    }
  }

  const handlePresetWeight = async (weightKg) => {
    const weightGrams = weightKg * 1000
    setEditWeight(weightGrams.toString())
    
    // Immediately apply the weight and close modal
    try {
      await updateBillItem('default', editingItemIndex, weightGrams)
      await loadBill(false) // Don't show loading spinner for updates
      handleCancelEdit() // Close the modal
    } catch (error) {
      console.error('Update item error:', error)
      alert('Failed to update item.')
    }
  }

  const handleQuantityChange = async (index, delta) => {
    const item = bill.items[index]
    if (!item) return
    
    const newQuantity = (item.quantity || 1) + delta
    if (newQuantity < 1) return

    try {
      await updateBillItemQuantity('default', index, newQuantity)
      await loadBill(false) // Don't show loading spinner for updates
    } catch (error) {
      console.error('Update quantity error:', error)
      alert('Failed to update quantity.')
    }
  }

  const handleOpenAddItemModal = async () => {
    setShowAddItemModal(true)
    setSearchTerm('')
    if (availableItems.length === 0) {
      await loadAvailableItems()
    }
  }

  const handleCloseAddItemModal = () => {
    setShowAddItemModal(false)
    setSearchTerm('')
  }

  const loadAvailableItems = async () => {
    try {
      setLoadingItems(true)
      const data = await getAllItems()
      setAvailableItems(data || [])
    } catch (error) {
      console.error('Error loading items:', error)
      alert('Failed to load items. Please try again.')
      setAvailableItems([])
    } finally {
      setLoadingItems(false)
    }
  }

  const handleAddItemToBill = async (item) => {
    try {
      // Calculate default weight/quantity based on pricing type
      let weightGrams = 1000 // Default 1 kg
      
      if (item.pricing_type === 'units') {
        weightGrams = 1 // For units, we use quantity instead
      } else if (item.pricing_type === 'ltr') {
        weightGrams = 1000 // 1 litre = 1000 grams (assuming 1 litre = 1 kg)
      }
      // For 'kg', default is already 1000 grams (1 kg)

      const itemToAdd = {
        name: item.item_name,
        weight_grams: weightGrams,
        price_per_kg: parseFloat(item.selling_price || item.price_per_kg)
      }

      await addItemToBill(itemToAdd, 'default', item.pricing_type)
      await loadBill(false)
      handleCloseAddItemModal()
    } catch (error) {
      console.error('Error adding item to bill:', error)
      alert('Failed to add item to bill. Please try again.')
    }
  }

  const getPricingTypeLabel = (type) => {
    switch(type) {
      case 'kg': return 'per kg'
      case 'ltr': return 'per litre'
      case 'units': return 'per unit'
      default: return 'per kg'
    }
  }

  const getDefaultQuantity = (type) => {
    switch(type) {
      case 'kg': return '1 kg'
      case 'ltr': return '1 litre'
      case 'units': return '1 unit'
      default: return '1 kg'
    }
  }

  const filteredItems = searchTerm.trim() 
    ? availableItems.filter(item =>
        item.item_name.toLowerCase().startsWith(searchTerm.toLowerCase())
      )
    : []

  if (loading) {
    return (
      <div className="bill-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading bill...</p>
        </div>
      </div>
    )
  }

  const subtotal = bill?.subtotal ?? (bill?.items?.reduce((sum, item) => sum + item.total_price, 0) || 0)
  const gstTotal = bill?.gst_total ?? (bill?.items?.reduce((sum, item) => sum + (item.gst_amount || 0), 0) || 0)
  const total = bill?.total ?? (subtotal + gstTotal)

  return (
    <div className="bill-page">
      <div className="page-header">
        <DollarIcon size={28} className="page-header-icon" />
        <h1>Current Bill</h1>
      </div>

      {bill && bill.items && bill.items.length > 0 ? (
        <>
          <div className="bill-items">
            {bill.items.map((item, index) => (
              <div key={index} className="bill-item-card">
                <button
                  onClick={() => handleRemoveItem(index)}
                  className="delete-button-top-right"
                  title="Remove item"
                >
                  <XIcon size={18} />
                </button>
                <div className="item-info">
                  <div className="item-name">{item.item_name}</div>
                  <div className="item-details">
                    {item.pricing_type === 'piece' ? (
                      <>
                        <span>₹{item.price_per_kg}/piece</span>
                        <span>× {item.quantity || 1}</span>
                      </>
                    ) : (
                      <>
                        <span>{item.weight_grams}g</span>
                        <span>@ ₹{item.price_per_kg}/kg</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="item-price">
                  ₹{item.total_price.toFixed(2)}
                  {(item.gst_rate || 0) > 0 && (
                    <span className="item-gst-badge">{item.gst_rate}% GST</span>
                  )}
                </div>
                {item.pricing_type === 'piece' && (
                  <div className="quantity-controls">
                    <button
                      onClick={() => handleQuantityChange(index, -1)}
                      className="quantity-button minus-button"
                      title="Decrease quantity"
                    >
                      <MinusIcon size={16} />
                    </button>
                    <span className="quantity-display">{item.quantity || 1}</span>
                    <button
                      onClick={() => handleQuantityChange(index, 1)}
                      className="quantity-button plus-button"
                      title="Increase quantity"
                    >
                      <PlusIcon size={16} />
                    </button>
                  </div>
                )}
                {item.pricing_type !== 'piece' && (
                  <button
                    onClick={() => handleStartEdit(item, index)}
                    className="edit-button-below"
                    title="Edit weight"
                  >
                    <EditIcon size={18} />
                    <span>Edit</span>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="bill-summary">
            <div className="summary-row">
              <span>Items</span>
              <span>{bill.items.length}</span>
            </div>
            <div className="summary-row">
              <span>Subtotal</span>
              <span>₹{subtotal.toFixed(2)}</span>
            </div>
            {gstTotal > 0 && (
              <div className="summary-row">
                <span>GST</span>
                <span>₹{gstTotal.toFixed(2)}</span>
              </div>
            )}
            <div className="summary-row total">
              <span>Total</span>
              <span>₹{total.toFixed(2)}</span>
            </div>
          </div>

          <div className="bill-actions">
            <button
              onClick={handleOpenAddItemModal}
              className="add-item-button"
            >
              <PlusIcon size={20} />
              <span>Add Item</span>
            </button>
            <button
              onClick={handleCheckoutClick}
              disabled={checkingOut}
              className="checkout-button"
            >
              <CheckIcon size={20} />
              <span>Checkout</span>
            </button>
            <button
              onClick={handleClear}
              className="clear-button"
            >
              <TrashIcon size={20} />
              <span>Clear Bill</span>
            </button>
          </div>

          {/* Checkout Modal */}
          {showCheckoutModal && (
            <div className="modal-overlay" onClick={handleCancelCheckout}>
              <div className="checkout-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Complete Checkout</h2>
                  <button className="modal-close" onClick={handleCancelCheckout}>
                    <XIcon size={20} />
                  </button>
                </div>
                
                <div className="modal-content">
                  <div className="bill-summary-preview">
                    <div className="summary-preview-row">
                      <span>Items:</span>
                      <span>{bill.items.length}</span>
                    </div>
                    <div className="summary-preview-row">
                      <span>Subtotal:</span>
                      <span>₹{subtotal.toFixed(2)}</span>
                    </div>
                    {gstTotal > 0 && (
                      <div className="summary-preview-row">
                        <span>GST:</span>
                        <span>₹{gstTotal.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="summary-preview-row total">
                      <span>Total:</span>
                      <span>₹{total.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="unpaid-section">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={isUnpaid}
                        onChange={(e) => {
                          setIsUnpaid(e.target.checked)
                          if (!e.target.checked) {
                            setCustomerName('')
                          }
                        }}
                        className="unpaid-checkbox"
                      />
                      <span>Unpaid</span>
                    </label>
                  </div>

                  {isUnpaid && (
                    <div className="customer-name-section">
                      <label htmlFor="customer-name">
                        Customer Name *
                      </label>
                      <input
                        id="customer-name"
                        type="text"
                        placeholder="Enter customer name"
                        value={customerName}
                        onChange={(e) => setCustomerName(e.target.value)}
                        className="customer-name-input"
                        required
                      />
                      <p className="customer-name-hint">
                        Phone number will be retrieved from customer records if not provided
                      </p>
                    </div>
                  )}

                  <div className="phone-input-section">
                    <label htmlFor="customer-phone">
                      <PhoneIcon size={18} />
                      Customer Phone Number (Optional)
                    </label>
                    <input
                      id="customer-phone"
                      type="tel"
                      placeholder="e.g., +91 9876543210 or 9876543210"
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                      className="phone-input"
                    />
                    <p className="phone-hint">
                      {isUnpaid 
                        ? 'If not provided, phone will be retrieved from customer records by name'
                        : 'If provided, the bill will be sent to this number via WhatsApp'}
                    </p>
                  </div>
                </div>

                <div className="modal-actions">
                  <button
                    onClick={handleCancelCheckout}
                    className="modal-cancel-button"
                    disabled={checkingOut}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCheckout}
                    className="modal-confirm-button"
                    disabled={checkingOut}
                  >
                    {checkingOut ? (
                      <>
                        <LoaderIcon size={18} className="spinner" />
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <span>Confirm Checkout</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="empty-bill">
          <ShoppingCartIcon size={64} className="empty-icon" />
          <h3>No items in bill</h3>
          <p className="empty-hint">Add items manually or scan items to add them to the bill</p>
          <div className="empty-bill-actions">
            <button
              onClick={handleOpenAddItemModal}
              className="add-item-button"
            >
              <PlusIcon size={20} />
              <span>Add Item</span>
            </button>
            <button
              onClick={() => navigate('/scan')}
              className="scan-button"
            >
              Go to Scan
            </button>
          </div>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddItemModal && (
        <div className="modal-overlay add-item-modal-overlay" onClick={handleCloseAddItemModal}>
          <div className="add-item-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add Item to Bill</h2>
              <button className="modal-close" onClick={handleCloseAddItemModal}>
                <XIcon size={20} />
              </button>
            </div>
            <div className="modal-content">
              <div className="add-item-search-section">
                <div className="search-bar">
                  <SearchIcon size={20} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Search items..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="search-input"
                    autoFocus
                  />
                </div>
              </div>
              {loadingItems ? (
                <div className="loading-state">
                  <LoaderIcon size={24} className="spinner" />
                  <p>Loading items...</p>
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="empty-state">
                  <p>{searchTerm.trim() ? 'No items found matching your search' : 'Start typing to search for items...'}</p>
                </div>
              ) : (
                <div className="items-list">
                  {filteredItems.map((item) => (
                    <div
                      key={item.item_name}
                      className="item-option-card"
                      onClick={() => handleAddItemToBill(item)}
                    >
                      <div className="item-option-info">
                        <div className="item-option-name">{item.item_name}</div>
                        <div className="item-option-details">
                          <span className="item-option-price">₹{parseFloat(item.selling_price || item.price_per_kg).toFixed(2)}</span>
                          <span className="item-option-type">{getPricingTypeLabel(item.pricing_type)}</span>
                        </div>
                      </div>
                      <div className="item-option-action">
                        <span className="item-option-quantity">{getDefaultQuantity(item.pricing_type)}</span>
                        <PlusIcon size={20} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit Weight Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={handleCancelEdit}>
          <div className="edit-weight-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Weight - {editingItemName}</h2>
              <button className="modal-close" onClick={handleCancelEdit}>
                <XIcon size={20} />
              </button>
            </div>
            
            <div className="modal-content">
                  <div className="preset-weights-section">
                    <label className="preset-label">Quick Select:</label>
                    <div className="preset-weight-buttons">
                      <button
                        onClick={() => handlePresetWeight(0.5)}
                        className="preset-weight-btn"
                      >
                        0.5 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(1)}
                        className="preset-weight-btn"
                      >
                        1 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(1.5)}
                        className="preset-weight-btn"
                      >
                        1.5 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(2)}
                        className="preset-weight-btn"
                      >
                        2 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(2.5)}
                        className="preset-weight-btn"
                      >
                        2.5 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(3)}
                        className="preset-weight-btn"
                      >
                        3 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(3.5)}
                        className="preset-weight-btn"
                      >
                        3.5 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(4)}
                        className="preset-weight-btn"
                      >
                        4 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(4.5)}
                        className="preset-weight-btn"
                      >
                        4.5 kg
                      </button>
                      <button
                        onClick={() => handlePresetWeight(5)}
                        className="preset-weight-btn"
                      >
                        5 kg
                      </button>
                    </div>
                  </div>

              <div className="manual-weight-input">
                <label htmlFor="weight-input">Or Enter Weight Manually:</label>
                <div className="weight-input-wrapper">
                      <input
                        id="weight-input"
                        type="number"
                        value={editWeight}
                        onChange={(e) => setEditWeight(e.target.value)}
                        min="0"
                        step="0.1"
                        className="weight-edit-input"
                        placeholder="Weight in grams"
                      />
                  <span className="weight-unit">grams</span>
                </div>
                {editWeight && (
                  <div className="weight-preview">
                    = {(parseFloat(editWeight) / 1000).toFixed(3)} kg
                  </div>
                )}
              </div>
            </div>

            <div className="modal-actions">
              <button
                onClick={handleCancelEdit}
                className="modal-cancel-button"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="modal-confirm-button"
              >
                <SaveIcon size={18} />
                <span>Save</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default BillPage

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else {
    // Remove Authorization header if no token
    delete config.headers.Authorization
  }
  return config
})

// Handle 401 errors globally - token expired or invalid
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth data and redirect to login
      // But don't redirect if we're already on the login page (to avoid redirect loops)
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('authToken')
        localStorage.removeItem('shopkeeper')
        window.dispatchEvent(new Event('auth-change'))
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// API functions
export const scanItem = async (weightGrams, imageBase64 = null, sessionId = 'default', addToBill = false) => {
  try {
    // Token will be added automatically by interceptor
    const response = await api.post('/scan-item', {
      weight_grams: weightGrams,
      image: imageBase64, // Optional - backend will capture from camera if not provided
    }, {
      params: { 
        session_id: sessionId,
        add_to_bill: addToBill
      }
    })
    return response.data
  } catch (error) {
    console.error('Scan error:', error)
    throw error
  }
}

export const getBill = async (sessionId = 'default') => {
  try {
    const response = await api.get(`/bill/${sessionId}`)
    return response.data
  } catch (error) {
    console.error('Get bill error:', error)
    throw error
  }
}

export const clearBill = async (sessionId = 'default') => {
  try {
    const response = await api.delete(`/bill/${sessionId}`)
    return response.data
  } catch (error) {
    console.error('Clear bill error:', error)
    throw error
  }
}

export const addItemToBill = async (item, sessionId = 'default', pricingType = null) => {
  try {
    // Directly add item to bill without re-detection
    const params = {
      item_name: item.name,
      weight_grams: item.weight_grams
    }
    if (item.price_per_kg) {
      params.price_per_kg = item.price_per_kg
    }
    if (pricingType) {
      params.pricing_type = pricingType
    }
    const response = await api.post(`/bill/${sessionId}/add-item`, null, {
      params: params
    })
    return response.data
  } catch (error) {
    console.error('Add item error:', error)
    throw error
  }
}

export const removeBillItem = async (sessionId, itemIndex) => {
  try {
    const response = await api.delete(`/bill/${sessionId}/item/${itemIndex}`)
    return response.data
  } catch (error) {
    console.error('Remove item error:', error)
    throw error
  }
}

export const updateBillItem = async (sessionId, itemIndex, weightGrams = null, quantity = null) => {
  try {
    let url = `/bill/${sessionId}/item/${itemIndex}?`
    if (weightGrams !== null) {
      url += `weight_grams=${weightGrams}`
    }
    if (quantity !== null) {
      if (weightGrams !== null) url += '&'
      url += `quantity=${quantity}`
    }
    const response = await api.put(url)
    return response.data
  } catch (error) {
    console.error('Update item error:', error)
    throw error
  }
}

export const updateBillItemQuantity = async (sessionId, itemIndex, quantity) => {
  return updateBillItem(sessionId, itemIndex, null, quantity)
}

export const checkoutBill = async (sessionId = 'default') => {
  try {
    // Get current bill
    const bill = await getBill(sessionId)
    
    // Calculate totals
    const total = bill.items.reduce((sum, item) => sum + item.total_price, 0)
    
    // Save to history (localStorage for now, can be moved to backend)
    const historyItem = {
      id: Date.now().toString(),
      sessionId,
      items: bill.items,
      total: total,
      timestamp: new Date().toISOString(),
      date: new Date().toLocaleDateString(),
      time: new Date().toLocaleTimeString(),
    }
    
    // Save to localStorage
    const history = JSON.parse(localStorage.getItem('billHistory') || '[]')
    history.unshift(historyItem)
    localStorage.setItem('billHistory', JSON.stringify(history))
    
    // Clear current bill
    await clearBill(sessionId)
    
    return historyItem
  } catch (error) {
    console.error('Checkout error:', error)
    throw error
  }
}

export const getHistory = () => {
  try {
    const history = JSON.parse(localStorage.getItem('billHistory') || '[]')
    return history
  } catch (error) {
    console.error('Get history error:', error)
    return []
  }
}

export const getCameraFrame = () => {
  return `${API_BASE_URL}/camera/frame?max_width=640&t=${Date.now()}`
}

// Authentication APIs
export const login = async (username, password) => {
  try {
    console.log('Attempting login to:', API_BASE_URL)
    const response = await api.post('/auth/login', {
      username,
      password
    })
    
    // Validate response
    if (!response.data) {
      throw new Error('Empty response from server')
    }
    
    if (!response.data.token) {
      throw new Error('No token received from server')
    }
    
    if (!response.data.shopkeeper) {
      throw new Error('No shopkeeper data received from server')
    }
    
    return response.data
  } catch (error) {
    console.error('Login error:', error)
    console.error('Error details:', {
      message: error.message,
      code: error.code,
      response: error.response?.data,
      status: error.response?.status,
      config: {
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        method: error.config?.method
      }
    })
    throw error
  }
}

export const register = async (formData) => {
  try {
    const response = await api.post('/auth/register', formData)
    return response.data
  } catch (error) {
    console.error('Register error:', error)
    throw error
  }
}

// Price management APIs
export const getPrices = async () => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.get('/prices', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Get prices error:', error)
    throw error
  }
}

export const getAllItems = async () => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.get('/prices/items', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Get all items error:', error)
    throw error
  }
}

export const updatePrice = async (itemName, pricePerKg) => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.put(`/prices/${itemName}`, {
      item_name: itemName,
      price_per_kg: pricePerKg
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Update price error:', error)
    throw error
  }
}

export const updateItemDetails = async (itemName, costPrice, sellingPrice, pricingType) => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.put(`/prices/${itemName}/details`, {
      item_name: itemName,
      cost_price: costPrice,
      selling_price: sellingPrice,
      pricing_type: pricingType
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Update item details error:', error)
    throw error
  }
}

export const createItem = async (itemName, costPrice, sellingPrice, pricingType) => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.post('/prices/items', {
      item_name: itemName,
      cost_price: costPrice,
      selling_price: sellingPrice,
      pricing_type: pricingType
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Create item error:', error)
    throw error
  }
}

export const bulkUpdatePrices = async (prices) => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.put('/prices', {
      prices
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Bulk update prices error:', error)
    throw error
  }
}

// Bill history APIs
export const getBillHistory = async (limit = 50, offset = 0) => {
  try {
    const token = localStorage.getItem('authToken')
    const response = await api.get('/bills/history', {
      params: { limit, offset },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.data
  } catch (error) {
    console.error('Get bill history error:', error)
    throw error
  }
}

export const validateToken = async () => {
  try {
    const response = await api.get('/auth/validate')
    return response.data
  } catch (error) {
    // Token is invalid or expired
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('shopkeeper')
      window.dispatchEvent(new Event('auth-change'))
    }
    throw error
  }
}

export const getProfile = async () => {
  try {
    const response = await api.get('/auth/profile')
    return response.data
  } catch (error) {
    console.error('Get profile error:', error)
    throw error
  }
}

export const updateProfile = async (profileData) => {
  try {
    const response = await api.put('/auth/profile', profileData)
    return response.data
  } catch (error) {
    console.error('Update profile error:', error)
    throw error
  }
}

export const getCustomersWithPending = async () => {
  try {
    const response = await api.get('/accounts/customers')
    return response.data
  } catch (error) {
    console.error('Get customers error:', error)
    throw error
  }
}

export const getCustomerUnpaidBills = async (customerId) => {
  try {
    const response = await api.get(`/accounts/customers/${customerId}/bills`)
    return response.data
  } catch (error) {
    console.error('Get customer bills error:', error)
    throw error
  }
}

export const markBillAsPaid = async (billId) => {
  try {
    const response = await api.post(`/accounts/bills/${billId}/mark-paid`)
    return response.data
  } catch (error) {
    console.error('Mark bill as paid error:', error)
    throw error
  }
}

export const getAllCustomers = async () => {
  try {
    const response = await api.get('/customers')
    return response.data
  } catch (error) {
    console.error('Get all customers error:', error)
    throw error
  }
}

export const createCustomer = async (name, phone) => {
  try {
    const response = await api.post('/customers', {
      name,
      phone
    })
    return response.data
  } catch (error) {
    console.error('Create customer error:', error)
    throw error
  }
}

export const deleteCustomer = async (customerId) => {
  try {
    const response = await api.delete(`/customers/${customerId}`)
    return response.data
  } catch (error) {
    console.error('Delete customer error:', error)
    throw error
  }
}

// Logistics / Stock API
export const getStockList = async () => {
  try {
    const response = await api.get('/logistics/stock')
    return response.data
  } catch (error) {
    console.error('Get stock list error:', error)
    throw error
  }
}

export const addOrUpdateStockItem = async (itemName, quantity, unit = 'kg') => {
  try {
    const response = await api.post('/logistics/stock', {
      item_name: itemName,
      quantity: Number(quantity),
      unit: unit === 'unit' || unit === 'units' ? 'unit' : (unit || 'kg')
    })
    return response.data
  } catch (error) {
    console.error('Add/update stock error:', error)
    throw error
  }
}

export const updateStockQuantity = async (itemName, quantity, unit = 'kg') => {
  try {
    const body = { quantity: Number(quantity) }
    if (unit) body.unit = unit === 'unit' || unit === 'units' ? 'unit' : unit
    const response = await api.put(`/logistics/stock/${encodeURIComponent(itemName)}`, body)
    return response.data
  } catch (error) {
    console.error('Update stock quantity error:', error)
    throw error
  }
}

export const deleteStockItem = async (itemName) => {
  try {
    const response = await api.delete(`/logistics/stock/${encodeURIComponent(itemName)}`)
    return response.data
  } catch (error) {
    console.error('Delete stock item error:', error)
    throw error
  }
}

export const saveBill = async (sessionId = 'default', isUnpaid = false, customerName = null, customerPhone = null) => {
  try {
    // Check if token exists
    const token = localStorage.getItem('authToken')
    if (!token) {
      throw new Error('No authentication token found. Please login again.')
    }
    
    // Validate token before attempting to save
    try {
      await validateToken()
    } catch (error) {
      if (error.response?.status === 401) {
        throw new Error('Your session has expired. Please login again to save bills.')
      }
      throw error
    }
    
    // Use the axios instance which has the interceptor - it will add the token automatically
    const response = await api.post('/bills/save', {
      is_unpaid: isUnpaid,
      customer_name: customerName,
      customer_phone: customerPhone
    }, {
      params: { session_id: sessionId }
    })
    return response.data
  } catch (error) {
    console.error('Save bill error:', error)
    // If it's a 401, clear the token and redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('shopkeeper')
      window.dispatchEvent(new Event('auth-change'))
    }
    throw error
  }
}

// Statistics API
export const getStatistics = async (period = 'days') => {
  try {
    const response = await api.get('/statistics', { params: { period } })
    return response.data
  } catch (error) {
    console.error('Get statistics error:', error)
    throw error
  }
}

// Analytics API (deeper insights)
export const getAnalytics = async () => {
  try {
    const response = await api.get('/analytics')
    return response.data
  } catch (error) {
    console.error('Get analytics error:', error)
    throw error
  }
}

// GST settings API
export const getGstSettings = async () => {
  try {
    const response = await api.get('/gst/settings')
    return response.data
  } catch (error) {
    console.error('Get GST settings error:', error)
    throw error
  }
}

export const updateGstRate = async (categoryKey, rate) => {
  try {
    const response = await api.put(`/gst/settings/${categoryKey}`, { rate })
    return response.data
  } catch (error) {
    console.error('Update GST rate error:', error)
    throw error
  }
}

export const resetDetectionState = async () => {
  try {
    const response = await api.post('/detection/reset')
    return response.data
  } catch (error) {
    console.error('Reset detection error:', error)
    throw error
  }
}

export default api


import React, { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getAllItems, updateItemDetails, createItem } from '../api/backend'
import { SettingsIcon, SearchIcon, SaveIcon, XIcon, EditIcon, LoaderIcon, DollarIcon, PlusIcon } from '../components/Icons'
import './PricePage.css'

function PricePage() {
  const location = useLocation()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingItem, setEditingItem] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const lastPathRef = useRef(null)
  
  // Form state for editing
  const [editForm, setEditForm] = useState({
    item_name: '',
    cost_price: '',
    selling_price: '',
    pricing_type: 'kg'
  })
  
  // Form state for adding new item
  const [addForm, setAddForm] = useState({
    item_name: '',
    cost_price: '',
    selling_price: '',
    pricing_type: 'kg'
  })

  useEffect(() => {
    // Load from cache first
    const cachedData = sessionStorage.getItem('priceItems')
    const cacheTime = sessionStorage.getItem('priceItemsTime')
    const now = Date.now()
    const CACHE_DURATION = 10 * 60 * 1000 // 10 minutes (prices change less frequently)
    
    if (cachedData && cacheTime && (now - parseInt(cacheTime)) < CACHE_DURATION) {
      try {
        setItems(JSON.parse(cachedData))
        setLoading(false)
        // Load fresh data in background
        loadItems(true)
        return
      } catch (e) {
        console.error('Error parsing cached items:', e)
      }
    }
    
    // Only load if this is a new navigation to this page
    if (lastPathRef.current !== location.pathname) {
      lastPathRef.current = location.pathname
      loadItems(false)
    }
  }, [location.pathname])

  const loadItems = async (background = false) => {
    try {
      if (!background) {
        setLoading(true)
      }
      const data = await getAllItems()
      const itemsData = data || []
      setItems(itemsData)
      // Cache the data
      sessionStorage.setItem('priceItems', JSON.stringify(itemsData))
      sessionStorage.setItem('priceItemsTime', Date.now().toString())
    } catch (error) {
      console.error('Error loading items:', error)
      // If offline, try to use cached data
      const cachedData = sessionStorage.getItem('priceItems')
      if (cachedData && !navigator.onLine) {
        try {
          setItems(JSON.parse(cachedData))
          return
        } catch (e) {
          console.error('Error parsing cached items:', e)
        }
      }
      // Don't show alert if it's a 401 (unauthorized) - let the interceptor handle it
      if (error.response?.status !== 401 && !background) {
        alert('Failed to load items. Please try again.')
      }
      // Set empty array to prevent crashes
      if (!background) {
        setItems([])
      }
    } finally {
      if (!background) {
        setLoading(false)
      }
    }
  }

  const handleStartEdit = (item) => {
    setEditingItem(item.item_name)
    setEditForm({
      item_name: item.item_name,
      cost_price: item.cost_price || '',
      selling_price: item.selling_price || item.price_per_kg || '',
      pricing_type: item.pricing_type || 'kg'
    })
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
    setEditForm({
      item_name: '',
      cost_price: '',
      selling_price: '',
      pricing_type: 'kg'
    })
  }

  const handleSaveItem = async () => {
    if (!editForm.selling_price || parseFloat(editForm.selling_price) <= 0) {
      alert('Please enter a valid selling price')
      return
    }

    try {
      setSaving(true)
      await updateItemDetails(
        editForm.item_name,
        editForm.cost_price ? parseFloat(editForm.cost_price) : null,
        parseFloat(editForm.selling_price),
        editForm.pricing_type
      )
      // Clear cache and reload
      sessionStorage.removeItem('priceItems')
      sessionStorage.removeItem('priceItemsTime')
      await loadItems(false)
      handleCancelEdit()
    } catch (error) {
      console.error('Error updating item:', error)
      alert('Failed to update item. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleAddItem = async () => {
    if (!addForm.item_name.trim()) {
      alert('Please enter an item name')
      return
    }
    
    if (!addForm.selling_price || parseFloat(addForm.selling_price) <= 0) {
      alert('Please enter a valid selling price')
      return
    }

    try {
      setSaving(true)
      await createItem(
        addForm.item_name.trim(),
        addForm.cost_price ? parseFloat(addForm.cost_price) : null,
        parseFloat(addForm.selling_price),
        addForm.pricing_type
      )
      // Clear cache and reload
      sessionStorage.removeItem('priceItems')
      sessionStorage.removeItem('priceItemsTime')
      await loadItems(false)
      setShowAddForm(false)
      setAddForm({
        item_name: '',
        cost_price: '',
        selling_price: '',
        pricing_type: 'kg'
      })
    } catch (error) {
      console.error('Error creating item:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create item'
      alert(`Failed to create item: ${errorMsg}`)
    } finally {
      setSaving(false)
    }
  }

  const handleCancelAdd = () => {
    setShowAddForm(false)
    setAddForm({
      item_name: '',
      cost_price: '',
      selling_price: '',
      pricing_type: 'kg'
    })
  }

  const filteredItems = items.filter(item =>
    item.item_name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getPricingTypeLabel = (type) => {
    switch(type) {
      case 'kg': return 'per kg'
      case 'ltr': return 'per liter'
      case 'units': return 'per unit'
      default: return 'per kg'
    }
  }

  if (loading) {
    return (
      <div className="price-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading items...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="price-page">
      <div className="page-header">
        <SettingsIcon size={28} className="page-header-icon" />
        <h1>Price Management</h1>
      </div>

      <div className="price-page-controls">
        <div className="search-bar">
          <SearchIcon size={20} className="search-icon" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="add-item-button"
        >
          <PlusIcon size={20} />
          <span>Item</span>
        </button>
      </div>

      {/* Add Item Modal */}
      {showAddForm && (
        <div className="modal-overlay" onClick={handleCancelAdd}>
          <div className="item-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add New Item</h2>
              <button className="modal-close" onClick={handleCancelAdd}>
                <XIcon size={20} />
              </button>
            </div>
            <div className="modal-content">
              <div className="item-form">
                <div className="form-group">
                  <label>Item Name *</label>
                  <input
                    type="text"
                    value={addForm.item_name}
                    onChange={(e) => setAddForm({...addForm, item_name: e.target.value})}
                    className="form-input"
                    placeholder="Enter item name"
                  />
                </div>
                <div className="form-group">
                  <label>Pricing Type *</label>
                  <div className="pricing-type-buttons">
                    <button
                      type="button"
                      className={`pricing-type-btn ${addForm.pricing_type === 'kg' ? 'active' : ''}`}
                      onClick={() => setAddForm({...addForm, pricing_type: 'kg'})}
                    >
                      per kg
                    </button>
                    <button
                      type="button"
                      className={`pricing-type-btn ${addForm.pricing_type === 'units' ? 'active' : ''}`}
                      onClick={() => setAddForm({...addForm, pricing_type: 'units'})}
                    >
                      per unit
                    </button>
                    <button
                      type="button"
                      className={`pricing-type-btn ${addForm.pricing_type === 'ltr' ? 'active' : ''}`}
                      onClick={() => setAddForm({...addForm, pricing_type: 'ltr'})}
                    >
                      litre
                    </button>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Cost Price (CP)</label>
                    <input
                      type="number"
                      value={addForm.cost_price}
                      onChange={(e) => setAddForm({...addForm, cost_price: e.target.value})}
                      min="0"
                      step="0.01"
                      className="form-input"
                      placeholder="Enter cost price"
                    />
                  </div>
                  <div className="form-group">
                    <label>Selling Price (SP) *</label>
                    <input
                      type="number"
                      value={addForm.selling_price}
                      onChange={(e) => setAddForm({...addForm, selling_price: e.target.value})}
                      min="0"
                      step="0.01"
                      className="form-input"
                      placeholder="Enter selling price"
                      required
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button
                onClick={handleCancelAdd}
                className="modal-cancel-button"
                disabled={saving}
              >
                <XIcon size={18} />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleAddItem}
                disabled={saving}
                className="modal-confirm-button"
              >
                {saving ? (
                  <>
                    <LoaderIcon size={18} className="spinner" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <SaveIcon size={18} />
                    <span>Save</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="prices-list">
        {filteredItems.length === 0 ? (
          <div className="empty-state">
            <DollarIcon size={48} className="empty-icon" />
            <p>No items found</p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <div key={item.item_name} className="price-item-card">
              <div className="item-info">
                <div className="item-name">{item.item_name}</div>
                <div className="item-details">
                  <div className="price-row">
                    {item.cost_price && (
                      <span className="price-item">CP: ₹{parseFloat(item.cost_price).toFixed(2)}</span>
                    )}
                    <span className="price-item price-sp">SP: ₹{parseFloat(item.selling_price || item.price_per_kg).toFixed(2)}</span>
                  </div>
                  <div className="pricing-type-row">
                    <span>{getPricingTypeLabel(item.pricing_type)}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleStartEdit(item)}
                className="edit-button"
                title="Edit item"
              >
                <EditIcon size={14} />
                <span>Edit</span>
              </button>
            </div>
          ))
        )}
      </div>

      {/* Edit Item Modal */}
      {editingItem && (
        <div className="modal-overlay" onClick={handleCancelEdit}>
          <div className="item-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Item - {editForm.item_name}</h2>
              <button className="modal-close" onClick={handleCancelEdit}>
                <XIcon size={20} />
              </button>
            </div>
            <div className="modal-content">
              <div className="item-form">
                <div className="form-group">
                  <label>Pricing Type *</label>
                  <div className="pricing-type-buttons">
                    <button
                      type="button"
                      className={`pricing-type-btn ${editForm.pricing_type === 'kg' ? 'active' : ''}`}
                      onClick={() => setEditForm({...editForm, pricing_type: 'kg'})}
                    >
                      per kg
                    </button>
                    <button
                      type="button"
                      className={`pricing-type-btn ${editForm.pricing_type === 'units' ? 'active' : ''}`}
                      onClick={() => setEditForm({...editForm, pricing_type: 'units'})}
                    >
                      per unit
                    </button>
                    <button
                      type="button"
                      className={`pricing-type-btn ${editForm.pricing_type === 'ltr' ? 'active' : ''}`}
                      onClick={() => setEditForm({...editForm, pricing_type: 'ltr'})}
                    >
                      litre
                    </button>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Cost Price (CP)</label>
                    <input
                      type="number"
                      value={editForm.cost_price}
                      onChange={(e) => setEditForm({...editForm, cost_price: e.target.value})}
                      min="0"
                      step="0.01"
                      className="form-input"
                      placeholder="Enter cost price"
                    />
                  </div>
                  <div className="form-group">
                    <label>Selling Price (SP) *</label>
                    <input
                      type="number"
                      value={editForm.selling_price}
                      onChange={(e) => setEditForm({...editForm, selling_price: e.target.value})}
                      min="0"
                      step="0.01"
                      className="form-input"
                      placeholder="Enter selling price"
                      required
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button
                onClick={handleCancelEdit}
                className="modal-cancel-button"
                disabled={saving}
              >
                <XIcon size={18} />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSaveItem}
                disabled={saving}
                className="modal-confirm-button"
              >
                {saving ? (
                  <>
                    <LoaderIcon size={18} className="spinner" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <SaveIcon size={18} />
                    <span>Save</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PricePage

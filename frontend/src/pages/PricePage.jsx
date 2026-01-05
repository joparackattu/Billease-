import React, { useState, useEffect } from 'react'
import { getPrices, updatePrice } from '../api/backend'
import { SettingsIcon, SearchIcon, SaveIcon, XIcon, EditIcon, LoaderIcon, DollarIcon } from '../components/Icons'
import './PricePage.css'

function PricePage() {
  const [prices, setPrices] = useState({})
  const [loading, setLoading] = useState(true)
  const [editingItem, setEditingItem] = useState(null)
  const [editPrice, setEditPrice] = useState('')
  const [saving, setSaving] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadPrices()
  }, [])

  const loadPrices = async () => {
    try {
      setLoading(true)
      const data = await getPrices()
      setPrices(data.prices || {})
    } catch (error) {
      console.error('Error loading prices:', error)
      alert('Failed to load prices. Please login again.')
    } finally {
      setLoading(false)
    }
  }

  const handleStartEdit = (itemName, currentPrice) => {
    setEditingItem(itemName)
    setEditPrice(currentPrice.toString())
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
    setEditPrice('')
  }

  const handleSavePrice = async (itemName) => {
    if (!editPrice || parseFloat(editPrice) <= 0) {
      alert('Please enter a valid price')
      return
    }

    try {
      setSaving(true)
      await updatePrice(itemName, parseFloat(editPrice))
      await loadPrices()
      setEditingItem(null)
      setEditPrice('')
    } catch (error) {
      console.error('Error updating price:', error)
      alert('Failed to update price. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const filteredItems = Object.entries(prices).filter(([itemName]) =>
    itemName.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <div className="price-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading prices...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="price-page">
      <div className="page-header">
        <SettingsIcon size={28} className="page-header-icon" />
        <div>
          <h1>Price Management</h1>
          <p>Manage prices for your shop</p>
        </div>
      </div>

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

      <div className="prices-list">
        {filteredItems.length === 0 ? (
          <div className="empty-state">
            <DollarIcon size={48} className="empty-icon" />
            <p>No items found</p>
          </div>
        ) : (
          filteredItems.map(([itemName, price]) => (
            <div key={itemName} className="price-item-card">
              {editingItem === itemName ? (
                <div className="edit-price-form">
                  <div className="item-name">{itemName}</div>
                  <div className="price-input-group">
                    <label>Price per kg</label>
                    <input
                      type="number"
                      value={editPrice}
                      onChange={(e) => setEditPrice(e.target.value)}
                      min="0"
                      step="0.01"
                      className="price-input"
                      autoFocus
                    />
                  </div>
                  <div className="edit-actions">
                    <button
                      onClick={() => handleSavePrice(itemName)}
                      disabled={saving}
                      className="save-button"
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
                    <button
                      onClick={handleCancelEdit}
                      className="cancel-button"
                    >
                      <XIcon size={18} />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="item-info">
                    <div className="item-name">{itemName}</div>
                    <div className="item-price">₹{price.toFixed(2)}/kg</div>
                  </div>
                  <button
                    onClick={() => handleStartEdit(itemName, price)}
                    className="edit-button"
                    title="Edit price"
                  >
                    <EditIcon size={20} />
                    <span>Edit</span>
                  </button>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default PricePage

import React, { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getStockList, addOrUpdateStockItem, updateStockQuantity, deleteStockItem, getAllItems } from '../api/backend'
import { PackageIcon, LoaderIcon, XIcon, EditIcon, SaveIcon } from '../components/Icons'
import './LogisticsPage.css'

const LOW_STOCK_THRESHOLD = 5
const UNIT_OPTIONS = [
  { value: 'kg', label: 'kg' },
  { value: 'unit', label: 'units' }
]

function LogisticsPage() {
  const location = useLocation()
  const [stockList, setStockList] = useState([])
  const [priceItems, setPriceItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [adding, setAdding] = useState(false)
  const [editingItemName, setEditingItemName] = useState(null)
  const [editQuantity, setEditQuantity] = useState('')
  const [editUnit, setEditUnit] = useState('kg')
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingItemName, setDeletingItemName] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const lastPathRef = useRef(null)
  const suggestionRef = useRef(null)

  const [addForm, setAddForm] = useState({
    item_name: '',
    quantity: '',
    unit: 'kg'
  })

  const loadStock = async (background = false) => {
    try {
      if (!background) setLoading(true)
      const data = await getStockList()
      setStockList(data.stock || [])
    } catch (error) {
      console.error('Error loading stock:', error)
      if (!background) setStockList([])
    } finally {
      if (!background) setLoading(false)
    }
  }

  const loadPriceItems = async () => {
    try {
      const data = await getAllItems()
      const list = Array.isArray(data) ? data : (data?.items || [])
      setPriceItems(list)
    } catch (error) {
      console.error('Error loading price items for suggestions:', error)
      setPriceItems([])
    }
  }

  useEffect(() => {
    if (lastPathRef.current !== location.pathname) {
      lastPathRef.current = location.pathname
      loadStock(false)
      loadPriceItems()
    }
  }, [location.pathname])

  const suggestionList = addForm.item_name.trim()
    ? priceItems.filter(
        (p) =>
          (p.item_name || p.name || '')
            .toLowerCase()
            .includes(addForm.item_name.trim().toLowerCase())
      ).slice(0, 8)
    : []

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionRef.current && !suggestionRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleAddSubmit = async (e) => {
    e.preventDefault()
    const name = addForm.item_name.trim()
    const qty = parseFloat(addForm.quantity)
    const unit = addForm.unit || 'kg'
    if (!name) {
      alert('Item name is required')
      return
    }
    if (isNaN(qty) || qty < 0) {
      alert('Please enter a valid quantity (0 or more)')
      return
    }
    try {
      setAdding(true)
      await addOrUpdateStockItem(name, qty, unit)
      await loadStock(false)
      setAddForm({ item_name: '', quantity: '', unit: 'kg' })
      setShowAddForm(false)
    } catch (error) {
      console.error('Add stock error:', error)
      const msg = error.response?.data?.detail || error.message || 'Failed to add stock item'
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setAdding(false)
    }
  }

  const handleSelectSuggestion = (item) => {
    const name = item.item_name || item.name || ''
    const pt = (item.pricing_type || 'kg').toLowerCase()
    const unit = pt === 'piece' || pt === 'unit' || pt === 'units' ? 'unit' : 'kg'
    setAddForm((prev) => ({ ...prev, item_name: name, unit }))
    setShowSuggestions(false)
  }

  const handleStartEdit = (item) => {
    setEditingItemName(item.item_name)
    setEditQuantity(String(item.quantity))
    setEditUnit(item.unit === 'unit' || item.unit === 'units' ? 'unit' : (item.unit || 'kg'))
  }

  const handleCancelEdit = () => {
    setEditingItemName(null)
    setEditQuantity('')
    setEditUnit('kg')
  }

  const handleSaveEdit = async () => {
    const qty = parseFloat(editQuantity)
    if (isNaN(qty) || qty < 0) {
      alert('Please enter a valid quantity')
      return
    }
    try {
      setSavingEdit(true)
      await updateStockQuantity(editingItemName, qty, editUnit)
      await loadStock(false)
      handleCancelEdit()
    } catch (error) {
      console.error('Update stock error:', error)
      alert(error.response?.data?.detail || 'Failed to update quantity')
    } finally {
      setSavingEdit(false)
    }
  }

  const handleDelete = async (itemName) => {
    if (!confirm(`Remove "${itemName}" from stock?`)) return
    try {
      setDeletingItemName(itemName)
      await deleteStockItem(itemName)
      await loadStock(false)
    } catch (error) {
      console.error('Delete stock error:', error)
      alert(error.response?.data?.detail || 'Failed to remove item')
    } finally {
      setDeletingItemName(null)
    }
  }

  const formatQuantity = (q, unit) => {
    const n = Number(q)
    const numStr = Number.isInteger(n) ? String(n) : n.toFixed(2)
    const u = (unit || 'kg').toLowerCase()
    return u === 'unit' || u === 'units' ? `${numStr} units` : `${numStr} kg`
  }

  return (
    <div className="logistics-page">
      <div className="page-header">
        <PackageIcon size={28} className="page-header-icon" />
        <h1>Stock / Logistics</h1>
      </div>
      <p className="page-description">
        Track items in stock (per shop). Quantities are in kg or units. They are deducted when you save a bill.
      </p>

      {loading ? (
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading stock...</p>
        </div>
      ) : (
        <div className="logistics-content">
          <div className="logistics-actions">
            <button
              type="button"
              className="add-stock-button"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              + Add item to stock
            </button>
          </div>

          {showAddForm && (
            <form className="add-stock-form" onSubmit={handleAddSubmit}>
              <div className="form-row">
                <div className="form-group form-group-item" ref={suggestionRef}>
                  <label>Item name *</label>
                  <input
                    type="text"
                    value={addForm.item_name}
                    onChange={(e) => {
                      setAddForm({ ...addForm, item_name: e.target.value })
                      setShowSuggestions(true)
                    }}
                    onFocus={() => setShowSuggestions(!!addForm.item_name.trim())}
                    placeholder="Type to search your items..."
                    required
                    autoComplete="off"
                  />
                  {showSuggestions && suggestionList.length > 0 && (
                    <ul className="item-suggestions">
                      {suggestionList.map((p, idx) => (
                        <li
                          key={idx}
                          className="suggestion-item"
                          onMouseDown={() => handleSelectSuggestion(p)}
                        >
                          {p.item_name || p.name}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="form-group form-group-qty">
                  <label>Quantity to add *</label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={addForm.quantity}
                    onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })}
                    placeholder="0"
                    required
                  />
                  <span className="form-hint">Added to existing stock if item already exists</span>
                </div>
                <div className="form-group form-group-unit">
                  <label>Unit</label>
                  <select
                    value={addForm.unit}
                    onChange={(e) => setAddForm({ ...addForm, unit: e.target.value })}
                  >
                    {UNIT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-actions">
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => {
                    setShowAddForm(false)
                    setAddForm({ item_name: '', quantity: '', unit: 'kg' })
                    setShowSuggestions(false)
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="save-button" disabled={adding}>
                  {adding ? 'Adding...' : 'Add to stock'}
                </button>
              </div>
            </form>
          )}

          {stockList.length === 0 ? (
            <div className="empty-state">
              <PackageIcon size={48} className="empty-icon" />
              <p>No stock items yet</p>
              <p className="empty-hint">Add items you have in stock. Quantities will decrease when you save bills.</p>
            </div>
          ) : (
            <div className="stock-list">
              {stockList.map((item) => (
                <div
                  key={item.id}
                  className={`stock-item ${item.quantity <= LOW_STOCK_THRESHOLD ? 'low-stock' : ''}`}
                >
                  <div className="stock-item-info">
                    <div className="stock-item-name">{item.item_name}</div>
                    {editingItemName === item.item_name ? (
                      <div className="stock-item-edit">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          value={editQuantity}
                          onChange={(e) => setEditQuantity(e.target.value)}
                          className="edit-qty-input"
                        />
                        <select
                          value={editUnit}
                          onChange={(e) => setEditUnit(e.target.value)}
                          className="edit-unit-select"
                        >
                          {UNIT_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="save-edit-btn"
                          onClick={handleSaveEdit}
                          disabled={savingEdit}
                        >
                          {savingEdit ? <LoaderIcon size={16} className="spinner" /> : <SaveIcon size={16} />}
                        </button>
                        <button type="button" className="cancel-edit-btn" onClick={handleCancelEdit}>
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="stock-item-qty">
                        <span className="qty-value">{formatQuantity(item.quantity, item.unit)}</span>
                        {item.quantity <= LOW_STOCK_THRESHOLD && (
                          <span className="low-stock-badge">Low stock</span>
                        )}
                        <button
                          type="button"
                          className="edit-qty-button"
                          onClick={() => handleStartEdit(item)}
                          title="Edit quantity"
                        >
                          <EditIcon size={16} />
                        </button>
                      </div>
                    )}
                  </div>
                  {editingItemName !== item.item_name && (
                    <button
                      type="button"
                      className="delete-stock-button"
                      onClick={() => handleDelete(item.item_name)}
                      disabled={deletingItemName === item.item_name}
                      title="Remove from stock"
                    >
                      {deletingItemName === item.item_name ? (
                        <LoaderIcon size={16} className="spinner" />
                      ) : (
                        <XIcon size={16} />
                      )}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default LogisticsPage

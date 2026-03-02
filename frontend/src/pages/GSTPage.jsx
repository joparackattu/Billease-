import React, { useState, useEffect } from 'react'
import { getGstSettings, updateGstRate } from '../api/backend'
import './GSTPage.css'

function GSTPage() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingKey, setSavingKey] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await getGstSettings()
      setCategories(res.categories || [])
    } catch (err) {
      console.error('Failed to load GST settings:', err)
      setError(err.response?.data?.detail || 'Failed to load GST settings')
    } finally {
      setLoading(false)
    }
  }

  const handleRateChange = (key, value) => {
    setCategories((prev) =>
      prev.map((c) =>
        c.category_key === key ? { ...c, rate: value } : c
      )
    )
  }

  const handleSave = async (key, rate) => {
    if (isNaN(parseFloat(rate))) {
      alert('Please enter a valid GST rate')
      return
    }
    try {
      setSavingKey(key)
      await updateGstRate(key, parseFloat(rate))
      await loadSettings()
    } catch (err) {
      console.error('Failed to update GST rate:', err)
      alert(err.response?.data?.detail || 'Failed to update GST rate')
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <div className="gst-page">
      <div className="page-header">
        <span className="page-header-icon">₹</span>
        <h1>GST Settings</h1>
      </div>
      <p className="page-description">
        Set GST % for item categories. These defaults are used to estimate GST on the bill.
      </p>

      {loading ? (
        <div className="loading-state">
          <p>Loading GST settings...</p>
        </div>
      ) : error ? (
        <div className="gst-error">{error}</div>
      ) : (
        <div className="gst-content">
          <table className="gst-table">
            <thead>
              <tr>
                <th>Category</th>
                <th className="num">GST %</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.category_key}>
                  <td>{cat.display_name}</td>
                  <td className="num">
                    <input
                      type="number"
                      min="0"
                      max="28"
                      step="0.1"
                      value={cat.rate}
                      onChange={(e) =>
                        handleRateChange(cat.category_key, e.target.value)
                      }
                      className="gst-input"
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="gst-save-button"
                      disabled={savingKey === cat.category_key}
                      onClick={() => handleSave(cat.category_key, cat.rate)}
                    >
                      {savingKey === cat.category_key ? 'Saving...' : 'Save'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="gst-info">
            <h3>GST slabs reference</h3>
            <ul>
              <li><strong>0% (Exempt)</strong> – fresh fruits & vegetables, milk, eggs, unbranded rice/wheat, salt.</li>
              <li><strong>5%</strong> – basic packaged foods, edible oils, sugar, tea, spices.</li>
              <li><strong>12%</strong> – processed foods (butter, cheese, fruit juice), some tools.</li>
              <li><strong>18%</strong> – toothpaste, soap, shampoo, detergents, chocolates, many services.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default GSTPage


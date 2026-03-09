import React, { useState, useEffect } from 'react'
import { getGstSettings, getGstAnalytics } from '../api/backend'
import { LoaderIcon } from '../components/Icons'
import './GSTPage.css'

function GSTPage() {
  const [categories, setCategories] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError('')
      const [settingsRes, analyticsRes] = await Promise.all([
        getGstSettings(),
        getGstAnalytics(),
      ])
      setCategories(settingsRes.categories || [])
      setAnalytics(analyticsRes)
    } catch (err) {
      console.error('Failed to load GST data:', err)
      setError(err.response?.data?.detail || 'Failed to load GST data')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="gst-page">
      <div className="page-header">
        <span className="page-header-icon">₹</span>
        <h1>GST</h1>
      </div>
      <p className="page-description">
        Government-fixed GST slabs by category. Rates cannot be changed.
      </p>

      {loading ? (
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading GST...</p>
        </div>
      ) : error ? (
        <div className="gst-error">{error}</div>
      ) : (
        <div className="gst-content">
          {/* GST Analytics - how much collected for government */}
          <div className="gst-analytics-section">
            <h3 className="gst-section-title">GST collected (to be paid to government)</h3>
            <p className="gst-analytics-hint">
              This is the GST collected from your sales. You need to pay this to the government as per GST filing.
            </p>
            <div className="gst-analytics-cards">
              <div className="gst-analytics-card">
                <div className="gst-card-label">Total GST collected</div>
                <div className="gst-card-value">
                  ₹{Number(analytics?.total_gst_collected || 0).toLocaleString('en-IN')}
                </div>
              </div>
              <div className="gst-analytics-card">
                <div className="gst-card-label">This month</div>
                <div className="gst-card-value">
                  ₹{Number(analytics?.this_month_gst || 0).toLocaleString('en-IN')}
                </div>
              </div>
              <div className="gst-analytics-card">
                <div className="gst-card-label">Last month</div>
                <div className="gst-card-value">
                  ₹{Number(analytics?.last_month_gst || 0).toLocaleString('en-IN')}
                </div>
              </div>
              <div className="gst-analytics-card">
                <div className="gst-card-label">Today</div>
                <div className="gst-card-value">
                  ₹{Number(analytics?.today_gst || 0).toLocaleString('en-IN')}
                </div>
              </div>
            </div>
          </div>

          {/* Fixed GST rates by category */}
          <div className="gst-rates-section">
            <h3 className="gst-section-title">GST slabs by category</h3>
            <table className="gst-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th className="num">GST %</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((cat) => (
                  <tr key={cat.category_key}>
                    <td>{cat.display_name}</td>
                    <td className="num gst-rate-fixed">{cat.rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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

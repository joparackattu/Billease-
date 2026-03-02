import React, { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { getBillHistory } from '../api/backend'
import { DocumentIcon, XIcon, LoaderIcon } from '../components/Icons'
import './HistoryPage.css'

function HistoryPage() {
  const location = useLocation()
  const [history, setHistory] = useState([])
  const [selectedBill, setSelectedBill] = useState(null)
  const [loading, setLoading] = useState(true)
  const lastPathRef = useRef(null)

  useEffect(() => {
    // Load from cache first
    const cachedData = sessionStorage.getItem('billHistory')
    const cacheTime = sessionStorage.getItem('billHistoryTime')
    const now = Date.now()
    const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes
    
    if (cachedData && cacheTime && (now - parseInt(cacheTime)) < CACHE_DURATION) {
      try {
        setHistory(JSON.parse(cachedData))
        setLoading(false)
        // Load fresh data in background
        loadHistory(true)
        return
      } catch (e) {
        console.error('Error parsing cached history:', e)
      }
    }
    
    // Only load if this is a new navigation to this page
    if (lastPathRef.current !== location.pathname) {
      lastPathRef.current = location.pathname
      loadHistory(false)
    }
  }, [location.pathname])

  const loadHistory = async (background = false) => {
    try {
      if (!background) {
        setLoading(true)
      }
      const data = await getBillHistory()
      const bills = data.bills || []
      setHistory(bills)
      // Cache the data
      sessionStorage.setItem('billHistory', JSON.stringify(bills))
      sessionStorage.setItem('billHistoryTime', Date.now().toString())
    } catch (error) {
      console.error('Error loading history:', error)
      // If offline, try to use cached data
      const cachedData = sessionStorage.getItem('billHistory')
      if (cachedData && !navigator.onLine) {
        try {
          setHistory(JSON.parse(cachedData))
          return
        } catch (e) {
          console.error('Error parsing cached history:', e)
        }
      }
      if (error.response?.status === 401) {
        alert('Please login to view bill history.')
        window.location.href = '/login'
      } else if (!background) {
        alert('Failed to load bill history.')
      }
    } finally {
      if (!background) {
        setLoading(false)
      }
    }
  }

  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  }

  const handleBillClick = (bill) => {
    setSelectedBill(bill)
  }

  const handleCloseDetail = () => {
    setSelectedBill(null)
  }

  if (loading) {
    return (
      <div className="history-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading bill history...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="history-page">
      <div className="page-header">
        <DocumentIcon size={28} className="page-header-icon" />
        <h1>Bill History</h1>
      </div>

      {history.length > 0 ? (
        <>
          <div className="history-list">
            {history.map((bill) => (
              <div
                key={bill.id}
                className="history-item-card"
                onClick={() => handleBillClick(bill)}
              >
                <div className="history-item-header">
                  <div className="history-item-date">
                    {formatDate(bill.created_at)}
                  </div>
                  <div className="history-item-total">
                    ₹{bill.total_amount.toFixed(2)}
                  </div>
                </div>
                <div className="history-item-info">
                  <span>{bill.items.length} item{bill.items.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="history-item-bill-number">
                  {bill.bill_number}
                </div>
              </div>
            ))}
          </div>

          {selectedBill && (
            <div className="bill-detail-modal" onClick={handleCloseDetail}>
              <div className="bill-detail-content" onClick={(e) => e.stopPropagation()}>
                <div className="bill-detail-header">
                  <h2>Bill Details</h2>
                  <button className="close-button" onClick={handleCloseDetail}>
                    <XIcon size={24} />
                  </button>
                </div>
                <div className="bill-detail-bill-number">
                  {selectedBill.bill_number}
                </div>
                <div className="bill-detail-date">
                  {formatDate(selectedBill.created_at)}
                </div>
                <div className="bill-detail-items">
                  {selectedBill.items.map((item, index) => {
                    const pricingType = item.pricing_type || 'weight'
                    const quantity = item.quantity || 1
                    const isPerPiece = pricingType === 'piece'
                    const gstRate = item.gst_rate || 0
                    const gstAmount = item.gst_amount || 0
                    
                    return (
                      <div key={index} className="bill-detail-item">
                        <div className="detail-item-info">
                          <div className="detail-item-name">{item.item_name}</div>
                          <div className="detail-item-meta">
                            {isPerPiece ? (
                              <>
                                {quantity} {quantity === 1 ? 'piece' : 'pieces'} @ ₹{item.price_per_kg}/piece
                              </>
                            ) : (
                              <>
                                {item.weight_grams}g @ ₹{item.price_per_kg}/kg
                              </>
                            )}
                            {gstRate > 0 && (
                              <span className="detail-item-gst"> ({gstRate}% GST: ₹{gstAmount.toFixed(2)})</span>
                            )}
                          </div>
                        </div>
                        <div className="detail-item-price">
                          ₹{item.total_price.toFixed(2)}
                        </div>
                      </div>
                    )
                  })}
                </div>
                {(() => {
                  const detailSubtotal = selectedBill.items.reduce((s, i) => s + (i.total_price || 0), 0)
                  const detailGst = selectedBill.items.reduce((s, i) => s + (i.gst_amount || 0), 0)
                  return (
                    <>
                      <div className="bill-detail-subtotal">
                        <span>Subtotal</span>
                        <span>₹{detailSubtotal.toFixed(2)}</span>
                      </div>
                      {detailGst > 0 && (
                        <div className="bill-detail-gst">
                          <span>GST</span>
                          <span>₹{detailGst.toFixed(2)}</span>
                        </div>
                      )}
                      <div className="bill-detail-total">
                        <span>Total</span>
                        <span>₹{selectedBill.total_amount.toFixed(2)}</span>
                      </div>
                    </>
                  )
                })()}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="empty-history">
          <DocumentIcon size={64} className="empty-icon" />
          <h3>No bill history</h3>
          <p className="empty-hint">Checked out bills will appear here</p>
        </div>
      )}
    </div>
  )
}

export default HistoryPage

import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getStatistics } from '../api/backend'
import { LoaderIcon } from '../components/Icons'
import './StatisticsPage.css'

function StatisticsPage() {
  const [period, setPeriod] = useState('days')
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('most') // 'most' or 'least'

  useEffect(() => {
    loadStatistics()
  }, [period])

  const loadStatistics = async () => {
    try {
      setLoading(true)
      const data = await getStatistics(period)
      setStatistics(data)
    } catch (error) {
      console.error('Error loading statistics:', error)
      if (error.response?.status === 401) {
        alert('Please login to view statistics.')
        window.location.href = '/login'
      } else {
        alert('Failed to load statistics.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="statistics-page">
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading statistics...</p>
        </div>
      </div>
    )
  }

  const chartData = statistics?.earnings || []
  let mostSoldItems = statistics?.most_sold_items || []
  
  // Sort most sold items based on selected sort option
  if (sortBy === 'least') {
    // Sort by quantity ascending (least sold first)
    mostSoldItems = [...mostSoldItems].sort((a, b) => 
      (a.total_quantity || 0) - (b.total_quantity || 0)
    )
  } else {
    // Sort by quantity descending (most sold first - default)
    mostSoldItems = [...mostSoldItems].sort((a, b) => 
      (b.total_quantity || 0) - (a.total_quantity || 0)
    )
  }
  
  // Get the period label (month for days, year for months) - use the first one since all are the same
  const periodLabel = chartData.length > 0 && chartData[0]?.month_label ? chartData[0].month_label : ''
  
  // Calculate max amount for Y-axis scaling
  const maxAmount = chartData.length > 0 
    ? Math.max(...chartData.map(item => item.amount || 0))
    : 1000
  
  // Calculate Y-axis domain with whole number increments (1k, 2k, 3k, 4k, etc.)
  // Ensure ticks are whole numbers (no 2.5k, 7.5k, etc.)
  const getNiceMaxAndIncrement = (value) => {
    if (value === 0) return { max: 4000, increment: 1000 }
    
    const inThousands = Math.ceil(value / 1000)
    
    // Find a nice increment and max that gives whole number ticks
    // We want 5 ticks total (0 and 4 intervals)
    let increment, nice
    if (inThousands <= 1) {
      increment = 1
      nice = 4  // 0, 1k, 2k, 3k, 4k
    } else if (inThousands <= 2) {
      increment = 1
      nice = 4
    } else if (inThousands <= 4) {
      increment = 1
      nice = 4
    } else if (inThousands <= 6) {
      increment = 2
      nice = 8  // 0, 2k, 4k, 6k, 8k
    } else if (inThousands <= 8) {
      increment = 2
      nice = 8
    } else if (inThousands <= 12) {
      increment = 3
      nice = 12  // 0, 3k, 6k, 9k, 12k
    } else if (inThousands <= 16) {
      increment = 4
      nice = 16  // 0, 4k, 8k, 12k, 16k
    } else if (inThousands <= 20) {
      increment = 5
      nice = 20  // 0, 5k, 10k, 15k, 20k
    } else if (inThousands <= 40) {
      increment = 10
      nice = 40  // 0, 10k, 20k, 30k, 40k
    } else {
      increment = Math.ceil(inThousands / 4)
      nice = increment * 4
    }
    
    return { max: nice * 1000, increment: increment * 1000 }
  }
  
  const { max: yAxisMax, increment } = getNiceMaxAndIncrement(maxAmount)
  // Create 5 ticks with whole number increments
  const yAxisTicks = [0, increment, increment * 2, increment * 3, yAxisMax]

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{label}</p>
          <p className="tooltip-value">
            ₹{payload[0].value.toFixed(2)}
          </p>
          <p className="tooltip-count">
            {payload[0].payload.count} bill{payload[0].payload.count !== 1 ? 's' : ''}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="statistics-page">
      <div className="page-header">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="page-header-icon">
          <line x1="18" y1="20" x2="18" y2="10"></line>
          <line x1="12" y1="20" x2="12" y2="4"></line>
          <line x1="6" y1="20" x2="6" y2="14"></line>
        </svg>
        <h1>Statistics</h1>
      </div>

      {/* Earnings Chart */}
      <div className="chart-container">
        <div className="chart-header">
          <h3 className="chart-title">Earnings by {period === 'days' ? 'Day' : 'Month'}</h3>
          <div className="chart-header-right">
            {periodLabel && (
              <div className="period-label">{periodLabel}</div>
            )}
            {/* Period Toggle - Inside Chart Container */}
            <div className="period-toggle">
              <button
                className={period === 'days' ? 'active' : ''}
                onClick={() => setPeriod('days')}
              >
                Days
              </button>
              <button
                className={period === 'months' ? 'active' : ''}
                onClick={() => setPeriod('months')}
              >
                Months
              </button>
            </div>
          </div>
        </div>

        <div className={period === 'days' ? 'chart-scroll-container' : 'chart-container-fixed'}>
          <ResponsiveContainer 
            width={period === 'days' ? Math.max(600, chartData.length * 20) : '100%'} 
            height={250}
            minHeight={250}
            maxHeight={250}
          >
            <BarChart 
              data={chartData} 
              margin={{ top: 20, right: 0, bottom: -20, left: -20 }}
              barCategoryGap={period === 'days' ? 0.5 : 3}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis 
                type="category"
                dataKey="period" 
                stroke="#666"
                fontSize={8}
                angle={period === 'days' ? 0 : 0}
                textAnchor={period === 'days' ? 'end' : 'middle'}
                height={60}
                interval={0}
                padding={{ left: 0, right: 0 }}
                allowDecimals={false}
                tickFormatter={(value, index) => {
                  if (period === 'months') {
                    // For months, show numbers 1-12 instead of month names
                    return (index + 1).toString()
                  }
                  // For days, return the value as is
                  return value
                }}
              />
            <YAxis 
              stroke="#666"
              fontSize={12}
              domain={[0, yAxisMax]}
              ticks={yAxisTicks}
              tickFormatter={(value) => {
                if (value >= 1000) {
                  const inK = value / 1000
                  // Show whole numbers without .0 (2k instead of 2.0k)
                  if (inK % 1 === 0) {
                    return `₹${inK}k`
                  }
                  return `₹${inK.toFixed(1)}k`
                }
                return `₹${value}`
              }}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="amount" 
              fill="url(#colorGradient)"
              radius={[4, 4, 0, 0]}
              barSize={period === 'days' ? 12 : 15}
            />
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#667eea" stopOpacity={1} />
                <stop offset="100%" stopColor="#764ba2" stopOpacity={1} />
              </linearGradient>
            </defs>
          </BarChart>
        </ResponsiveContainer>
        </div>
      </div>

      {/* Most Sold Items */}
      <div className="most-sold-section">
        <div className="section-header">
          <h3 className="section-title">Most Sold Items</h3>
          {mostSoldItems.length > 0 && (
            <div className="sort-filter">
              <button
                className={`sort-btn ${sortBy === 'most' ? 'active' : ''}`}
                onClick={() => setSortBy('most')}
              >
                Most Sold
              </button>
              <button
                className={`sort-btn ${sortBy === 'least' ? 'active' : ''}`}
                onClick={() => setSortBy('least')}
              >
                Least Sold
              </button>
            </div>
          )}
        </div>
        {mostSoldItems.length > 0 ? (
          <div className="items-list">
            {mostSoldItems.map((item, index) => {
              // For progress bar, always use the maximum quantity from the original sorted list
              const maxQuantity = Math.max(...mostSoldItems.map(i => i.total_quantity || 0))
              const quantity = item.total_quantity || 0
              const unitType = item.unit_type || 'kg'
              const unitLabel = unitType === 'units' ? 'unit' : unitType
              
              return (
                <div key={index} className="item-row">
                  <div className="item-info">
                    <div className="item-name">{item.item_name}</div>
                    <div className="item-count">
                      {quantity} {unitLabel}{quantity !== 1 && unitType === 'units' ? 's' : ''}
                    </div>
                  </div>
                  <div className="item-bar-container">
                    <div 
                      className="item-bar"
                      style={{ 
                        width: `${maxQuantity > 0 ? (quantity / maxQuantity) * 100 : 0}%` 
                      }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="no-data">
            <p>No items sold yet</p>
            <p className="no-data-hint">Start scanning items to see sales data</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatisticsPage

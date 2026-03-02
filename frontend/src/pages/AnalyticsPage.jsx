import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getAnalytics } from '../api/backend'
import { LoaderIcon } from '../components/Icons'
import './AnalyticsPage.css'

function AnalyticsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState('day') // 'day' or 'month'
  const [metric, setMetric] = useState('revenue') // 'revenue' or 'profit'

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await getAnalytics()
      setData(res)
    } catch (err) {
      console.error('Analytics load error:', err)
      setError(err.response?.data?.detail || 'Failed to load analytics')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="analytics-page">
        <div className="page-header">
          <span className="page-header-icon">📊</span>
          <h1>Analytics</h1>
        </div>
        <div className="loading-state">
          <LoaderIcon size={32} className="spinner" />
          <p>Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="analytics-page">
        <div className="page-header">
          <span className="page-header-icon">📊</span>
          <h1>Analytics</h1>
        </div>
        <div className="analytics-error">
          <p>{error}</p>
          <button type="button" className="retry-button" onClick={loadAnalytics}>Retry</button>
        </div>
      </div>
    )
  }

  const summary = data?.summary || {}
  const topItemsRevenue = data?.top_items_by_revenue || []
  const topItemsProfit = data?.top_items_by_profit || []
  const billsByDay = data?.bills_by_day_of_week || []
  const lowStock = data?.low_stock_items || []
  const revenueByDay = data?.revenue_by_day || []
  const revenueByMonth = data?.revenue_by_month || []

  const trendData = (period === 'day' ? revenueByDay : revenueByMonth).map((row) => ({
    label: period === 'day' ? row.day_label : row.month_label,
    revenue: Number(row.revenue || 0),
    profit: Number(row.profit || 0),
    bills: row.bills || 0,
  }))

  const currentMetricKey = metric === 'revenue' ? 'revenue' : 'profit'
  const chartTitle =
    period === 'day'
      ? `Daily ${metric === 'revenue' ? 'revenue' : 'profit'} (last ${trendData.length} days)`
      : `Monthly ${metric === 'revenue' ? 'revenue' : 'profit'}`

  const ChartTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{label}</p>
          <p className="tooltip-value">
            ₹{(point[currentMetricKey] || 0).toFixed(2)}
          </p>
          <p className="tooltip-count">
            {point.bills} bill{point.bills !== 1 ? 's' : ''}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="analytics-page">
      <div className="page-header">
        <h1>Analytics</h1>
      </div>
      <p className="page-description">
        Detailed shop performance: revenue, profit, trends, and stock health.
      </p>

      {/* Summary cards */}
      <div className="analytics-cards">
        <div className="analytics-card">
          <div className="card-label">Total revenue</div>
          <div className="card-value">
            ₹{Number(summary.total_revenue || 0).toLocaleString('en-IN')}
          </div>
          <div className="card-subtext">
            Average bill: ₹{Number(summary.avg_bill_value || 0).toLocaleString('en-IN')}
          </div>
        </div>
        <div className="analytics-card">
          <div className="card-label">Total profit</div>
          <div className="card-value">
            ₹{Number(summary.total_profit || 0).toLocaleString('en-IN')}
          </div>
          <div className="card-subtext">
            Avg profit / bill: ₹{Number(summary.avg_profit_per_bill || 0).toLocaleString('en-IN')}
          </div>
        </div>
        <div className="analytics-card">
          <div className="card-label">Today</div>
          <div className="card-value">
            ₹{Number(summary.today_revenue || 0).toLocaleString('en-IN')}
          </div>
          <div className="card-subtext">
            Profit: ₹{Number(summary.today_profit || 0).toLocaleString('en-IN')}
          </div>
        </div>
        <div className="analytics-card">
          <div className="card-label">This month</div>
          <div className="card-value">
            ₹{Number(summary.this_month_revenue || 0).toLocaleString('en-IN')}
          </div>
          <div className="card-subtext">
            Profit: ₹{Number(summary.this_month_profit || 0).toLocaleString('en-IN')}
          </div>
          {(summary.revenue_change_percent != null || summary.profit_change_percent != null) && (
            <div className="card-change-row">
              {summary.revenue_change_percent != null && (
                <span
                  className={`card-change ${
                    summary.revenue_change_percent >= 0 ? 'positive' : 'negative'
                  }`}
                >
                  Rev: {summary.revenue_change_percent >= 0 ? '↑' : '↓'}{' '}
                  {Math.abs(summary.revenue_change_percent)}%
                </span>
              )}
              {summary.profit_change_percent != null && (
                <span
                  className={`card-change ${
                    summary.profit_change_percent >= 0 ? 'positive' : 'negative'
                  }`}
                >
                  Profit: {summary.profit_change_percent >= 0 ? '↑' : '↓'}{' '}
                  {Math.abs(summary.profit_change_percent)}%
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Revenue / Profit trend (matches Statistics chart style) */}
      <div className="analytics-section chart-container">
        <div className="chart-header">
          <h3 className="chart-title">{chartTitle}</h3>
          <div className="chart-header-right analytics-header-toggles">
            <div className="metric-toggle">
              <button
                className={metric === 'revenue' ? 'active' : ''}
                onClick={() => setMetric('revenue')}
              >
                Revenue
              </button>
              <button
                className={metric === 'profit' ? 'active' : ''}
                onClick={() => setMetric('profit')}
              >
                Profit
              </button>
            </div>
            <div className="period-toggle">
              <button
                className={period === 'day' ? 'active' : ''}
                onClick={() => setPeriod('day')}
              >
                Daily
              </button>
              <button
                className={period === 'month' ? 'active' : ''}
                onClick={() => setPeriod('month')}
              >
                Monthly
              </button>
            </div>
          </div>
        </div>

        {trendData.length > 0 ? (
          <div className={period === 'day' ? 'chart-scroll-container' : 'chart-container-fixed'}>
            <ResponsiveContainer
              width={period === 'day' ? Math.max(600, trendData.length * 22) : '100%'}
              height={250}
              minHeight={250}
              maxHeight={250}
            >
              <BarChart
                data={trendData}
                margin={{ top: 20, right: 0, bottom: -10, left: -20 }}
                barCategoryGap={period === 'day' ? 0.5 : 3}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  type="category"
                  dataKey="label"
                  stroke="#666"
                  fontSize={10}
                  height={50}
                  interval={0}
                />
                <YAxis
                  stroke="#666"
                  fontSize={12}
                  tickFormatter={(value) => {
                    if (value >= 1000) {
                      const inK = value / 1000
                      if (inK % 1 === 0) {
                        return `₹${inK}k`
                      }
                      return `₹${inK.toFixed(1)}k`
                    }
                    return `₹${value}`
                  }}
                  width={60}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar
                  dataKey={currentMetricKey}
                  fill="url(#analyticsGradient)"
                  radius={[4, 4, 0, 0]}
                  barSize={period === 'day' ? 14 : 18}
                />
                <defs>
                  <linearGradient id="analyticsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#667eea" stopOpacity={1} />
                    <stop offset="100%" stopColor="#764ba2" stopOpacity={1} />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="no-data">
            <p>No bills yet to show trends.</p>
            <p className="no-data-hint">Start billing to see revenue and profit charts here.</p>
          </div>
        )}
      </div>

      {/* Bills by day of week */}
      {billsByDay.length > 0 && (
        <div className="analytics-section">
          <h3 className="section-title">Bills by day of week</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={billsByDay} margin={{ top: 12, right: 12, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e8e8" />
                <XAxis dataKey="day" stroke="#666" fontSize={12} />
                <YAxis stroke="#666" fontSize={12} allowDecimals={false} />
                <Tooltip
                  formatter={(value) => [value, 'Bills']}
                  contentStyle={{ borderRadius: 8, border: '1px solid #eee' }}
                />
                <Bar dataKey="count" fill="var(--primary-color, #081552)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Top items by revenue */}
      <div className="analytics-section">
        <h3 className="section-title">Top items by revenue</h3>
        {topItemsRevenue.length > 0 ? (
          <div className="analytics-table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item</th>
                  <th className="num">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {topItemsRevenue.map((row, i) => (
                  <tr key={row.item_name + i}>
                    <td>{i + 1}</td>
                    <td>{row.item_name}</td>
                    <td className="num">
                      ₹{Number(row.revenue || 0).toLocaleString('en-IN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data">No sales data yet. Bills will appear here.</div>
        )}
      </div>

      {/* Top items by profit */}
      <div className="analytics-section">
        <h3 className="section-title">Top items by profit</h3>
        {topItemsProfit.length > 0 ? (
          <div className="analytics-table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item</th>
                  <th className="num">Profit</th>
                  <th className="num">Revenue</th>
                  <th className="num">Margin</th>
                </tr>
              </thead>
              <tbody>
                {topItemsProfit.map((row, i) => (
                  <tr key={row.item_name + i}>
                    <td>{i + 1}</td>
                    <td>{row.item_name}</td>
                    <td className="num">
                      ₹{Number(row.profit || 0).toLocaleString('en-IN')}
                    </td>
                    <td className="num">
                      ₹{Number(row.revenue || 0).toLocaleString('en-IN')}
                    </td>
                    <td className="num">
                      {row.margin_percent != null ? `${row.margin_percent}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data">
            <p>No profit data yet.</p>
            <p className="no-data-hint">
              Set cost price for items in the price list to see profit analytics.
            </p>
          </div>
        )}
      </div>

      {/* Low stock */}
      <div className="analytics-section">
        <h3 className="section-title">Low stock</h3>
        {lowStock.length > 0 ? (
          <div className="low-stock-list">
            {lowStock.map((item, i) => (
              <div key={item.item_name + i} className="low-stock-item">
                <span className="low-stock-name">{item.item_name}</span>
                <span className="low-stock-qty">
                  {item.quantity} {item.unit || 'kg'}
                </span>
              </div>
            ))}
            <button type="button" className="link-button" onClick={() => navigate('/logistics')}>
              Open Logistics →
            </button>
          </div>
        ) : (
          <div className="no-data">No low-stock items. Stock is tracked in Logistics.</div>
        )}
      </div>
    </div>
  )
}

export default AnalyticsPage

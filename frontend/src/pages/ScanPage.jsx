import React, { useState, useEffect, useRef } from 'react'
import { getCameraFrame, resetDetectionState, teachItem } from '../api/backend'
import scanningService from '../services/scanningService'
import { CameraIcon, PlayIcon, StopIcon, CheckIcon, AlertCircleIcon } from '../components/Icons'
import './ScanPage.css'

function ScanPage() {
  const [cameraUrl, setCameraUrl] = useState('')
  const [cameraError, setCameraError] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [detectedItems, setDetectedItems] = useState([])
  const [error, setError] = useState('')
  const [itemNameOverride, setItemNameOverride] = useState('')
  const [teachingItemName, setTeachingItemName] = useState(null) // when set, we're in "capture more" mode
  const [teachingCaptureCount, setTeachingCaptureCount] = useState(0)
  const [capturing, setCapturing] = useState(false)
  const cameraRefreshInterval = useRef(null)

  // Initialize scanning state from service (persists across navigation)
  useEffect(() => {
    const currentState = scanningService.isScanningActive()
    setIsScanning(currentState)

    const handleStateChange = (isActive) => {
      setIsScanning(isActive)
    }
    scanningService.addListener(handleStateChange)

    const handleItemDetected = (event) => {
      const detectedItem = event.detail
      
      setDetectedItems(prev => {
        const isDuplicate = prev.some(
          item => item.name === detectedItem.name
        )

        if (!isDuplicate) {
          const newItems = [...prev, detectedItem]
          
          setTimeout(() => {
            setDetectedItems(current => current.filter(i => 
              !(i.name === detectedItem.name && 
                Math.abs(i.weight_grams - detectedItem.weight_grams) < 5)
            ))
          }, 3000)
          
          return newItems
        } else {
          console.log(`Skipping duplicate detection: ${detectedItem.name}`)
          return prev
        }
      })
    }
    window.addEventListener('itemDetected', handleItemDetected)

    return () => {
      scanningService.removeListener(handleStateChange)
      window.removeEventListener('itemDetected', handleItemDetected)
    }
  }, [])

  // Refresh camera feed (every 500ms so the image has time to load before next request)
  useEffect(() => {
    const refreshCamera = () => {
      setCameraUrl(getCameraFrame())
    }
    
    refreshCamera()
    cameraRefreshInterval.current = setInterval(refreshCamera, 500)
    
    return () => {
      if (cameraRefreshInterval.current) {
        clearInterval(cameraRefreshInterval.current)
      }
    }
  }, [])

  useEffect(() => {
    scanningService.setOverrideItemName(itemNameOverride)
  }, [itemNameOverride])

  const handleToggleScan = async () => {
    if (!isScanning) {
      setDetectedItems([])
      setError('')
      try {
        await resetDetectionState()
      } catch (err) {
        console.error('Failed to reset detection state:', err)
      }
      scanningService.startScanning()
    } else {
      try {
        await resetDetectionState()
      } catch (err) {
        console.error('Failed to reset detection state:', err)
      }
      scanningService.stopScanning()
    }
  }

  return (
    <div className="scan-page">
      <div className="page-header">
        <CameraIcon size={28} className="page-header-icon" />
        <h1>Scan Item</h1>
      </div>

      <div className="camera-container">
        <div className="camera-feed">
          {cameraUrl && !cameraError ? (
            <img 
              src={cameraUrl} 
              alt="Camera Feed" 
              className="camera-image"
              onLoad={() => setCameraError(false)}
              onError={() => setCameraError(true)}
            />
          ) : (
            <div className="camera-placeholder">
              <CameraIcon size={48} className="placeholder-icon" />
              <p>{cameraUrl && cameraError ? 'Camera offline or unreachable' : 'Loading camera...'}</p>
              {cameraError && (
                <p className="camera-placeholder-hint">Check that the camera is on and RTSP is enabled in the Tapo app.</p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="scan-item-name-row">
        <label className="scan-item-name-label">Item name (if not detected)</label>
        <input
          type="text"
          className="scan-item-name-input"
          placeholder="e.g. potato, chips..."
          value={itemNameOverride}
          onChange={(e) => setItemNameOverride(e.target.value)}
        />
        <p className="scan-item-name-hint">When the model doesn’t recognize the item, this name is used for the bill.</p>
      </div>

      <button
        onClick={handleToggleScan}
        className={`scan-button ${isScanning ? 'scanning' : ''}`}
      >
        {isScanning ? (
          <>
            <StopIcon size={20} />
            <span>Stop Scanning</span>
          </>
        ) : (
          <>
            <PlayIcon size={20} />
            <span>Start Scanning</span>
          </>
        )}
      </button>

      <button
        type="button"
        className="teach-item-button"
        disabled={!!teachingItemName || capturing}
        onClick={async () => {
          const name = window.prompt('Enter the item name (e.g. green peas):')
          if (!name || !name.trim()) return
          try {
            setCapturing(true)
            await teachItem(null, name.trim())
            setTeachingItemName(name.trim())
            setTeachingCaptureCount(1)
          } catch (err) {
            alert(err.response?.data?.detail || err.message || 'Failed to save image')
          } finally {
            setCapturing(false)
          }
        }}
      >
        {capturing ? 'Saving...' : 'Teach system this item'}
      </button>

      {teachingItemName && (
        <div className="teaching-panel">
          <h3 className="teaching-panel-title">Teaching: {teachingItemName}</h3>
          <p className="teaching-panel-message">
            Change the item position and click <strong>Capture</strong> to add another image. Aim for 20–50+ images.
          </p>
          <p className="teaching-panel-count">{teachingCaptureCount} image{teachingCaptureCount !== 1 ? 's' : ''} saved</p>
          <div className="teaching-panel-actions">
            <button
              type="button"
              className="teaching-capture-button"
              disabled={capturing}
              onClick={async () => {
                try {
                  setCapturing(true)
                  await teachItem(null, teachingItemName)
                  setTeachingCaptureCount((c) => c + 1)
                } catch (err) {
                  alert(err.response?.data?.detail || err.message || 'Failed to save image')
                } finally {
                  setCapturing(false)
                }
              }}
            >
              {capturing ? 'Saving...' : 'Capture'}
            </button>
            <button
              type="button"
              className="teaching-done-button"
              onClick={() => {
                setTeachingItemName(null)
                setTeachingCaptureCount(0)
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {isScanning && (
        <div className="scanning-status">
          <div className="scanning-indicator">
            <span className="pulse-dot"></span>
            <span>Scanning active - Place items on platform</span>
          </div>
        </div>
      )}

      {error && (
        <div className="error-message">
          <AlertCircleIcon size={20} />
          <span>{error}</span>
        </div>
      )}

      {detectedItems.length > 0 && (
        <div className="detected-items-section">
          <div className="section-header">
            <CheckIcon size={24} className="success-icon" />
            <h3>Item Added to Bill</h3>
          </div>
          {detectedItems.map((item, index) => (
            <div key={index} className="detected-item-card">
              <div className="item-details">
                <div className="item-row">
                  <span className="label">Item</span>
                  <span className="value">{item.name}</span>
                </div>
                <div className="item-row">
                  <span className="label">Weight</span>
                  <span className="value">{item.weight_grams}g</span>
                </div>
                <div className="item-row">
                  <span className="label">Price</span>
                  <span className="value price">₹{item.total_price}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ScanPage

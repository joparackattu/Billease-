/**
 * Persistent Scanning Service
 * 
 * This service manages scanning state that persists across page navigation.
 * Scanning continues even when the user navigates away from the scan page.
 * 
 * Uses an async loop that continuously calls performScan() while scanningActive is true.
 * Yields control between iterations to avoid UI blocking.
 */

import { scanItem } from '../api/backend'

const SCANNING_STATE_KEY = 'billease_scanning_active'

class ScanningService {
  constructor() {
    this.scanningActive = false
    this.isDetecting = false
    this.listeners = new Set() // For notifying components about state changes
    this.stableDetectionCount = 0 // Track stable detections
    this.lastDetectedItem = null
    this.overrideItemName = '' // When set, used when model returns "unknown"
    this.scanCount = 0
    this.lastFpsUpdate = Date.now()
    this.currentFps = 0
    this.initialize()
  }

  setOverrideItemName(name) {
    this.overrideItemName = name ? String(name).trim() : ''
  }

  getOverrideItemName() {
    return this.overrideItemName || ''
  }

  /**
   * Initialize the service - restore state from localStorage
   */
  initialize() {
    const wasScanning = this.isScanningActive()
    if (wasScanning) {
      // Restore scanning state
      this.startScanning()
    }
  }

  /**
   * Check if scanning is active (from localStorage)
   */
  isScanningActive() {
    try {
      return localStorage.getItem(SCANNING_STATE_KEY) === 'true'
    } catch (e) {
      return false
    }
  }

  /**
   * Set scanning state in localStorage
   */
  setScanningState(active) {
    try {
      localStorage.setItem(SCANNING_STATE_KEY, active ? 'true' : 'false')
      this.notifyListeners(active)
    } catch (e) {
      console.error('Failed to save scanning state:', e)
    }
  }

  /**
   * Start scanning - begins continuous async loop
   * 
   * YOLO inference runs continuously in an async loop while scanningActive is true.
   * The loop yields control between iterations to avoid UI blocking.
   * Target: 5-10 FPS (limited by inference speed, not artificial delays).
   * Stops automatically once detection is stable.
   */
  startScanning() {
    if (this.scanningActive) {
      // Already scanning
      return
    }

    this.setScanningState(true)
    this.scanningActive = true
    this.stableDetectionCount = 0
    this.lastDetectedItem = null
    
    // Start continuous async scanning loop
    // Don't await - let it run in background
    this.scanLoop().catch(err => {
      console.error('Scan loop error:', err)
      // Reset state on error
      this.scanningActive = false
      this.setScanningState(false)
    })
    
    console.log('✅ Scanning started - YOLO running continuously (target: 5-10 FPS)')
  }

  /**
   * Stop scanning - sets flag to exit loop
   */
  stopScanning() {
    this.scanningActive = false
    this.stableDetectionCount = 0
    this.lastDetectedItem = null
    this.setScanningState(false)
    console.log('⏹️ Scanning stopped')
  }
  
  /**
   * Async loop that continuously calls performScan() while scanningActive is true.
   * Yields control between iterations using Promise.resolve() to avoid UI blocking.
   * 
   * This ensures the event loop can process other tasks (UI updates, user interactions)
   * between detection iterations, preventing the UI from freezing.
   */
  async scanLoop() {
    // Run loop continuously while scanning is active
    while (this.scanningActive) {
      // Perform scan (async operation)
      await this.performScan()
      
      // Yield control to event loop to avoid UI blocking
      // This allows React to update UI, handle user interactions, etc.
      // Using Promise.resolve() is the most efficient way to yield
      await Promise.resolve()
      
      // Loop continues immediately after yielding
      // Actual speed is limited by inference time, not this yield
    }
    
    console.log('🛑 Scan loop exited')
  }

  /**
   * Perform a single scan iteration
   * 
   * This method runs as fast as the API allows.
   * No throttling, no delays - pure continuous execution.
   * Returns immediately if already detecting or scanning is inactive.
   */
  async performScan() {
    // Skip if already detecting (prevents overlapping calls)
    // or if scanning is no longer active
    if (this.isDetecting || !this.scanningActive) {
      return
    }

    this.isDetecting = true
    const scanStartTime = performance.now()

    try {
      // Use random weight between 100-500g for now
      // In production, this will come from ESP32
      const randomWeight = Math.floor(Math.random() * 400) + 100
      
      const itemNameOverride = this.getOverrideItemName()
      const result = await scanItem(randomWeight, null, 'default', true, itemNameOverride)
      
      // Track performance (FPS)
      this.scanCount++
      const now = Date.now()
      if (now - this.lastFpsUpdate >= 1000) {
        // Update FPS every second
        this.currentFps = this.scanCount
        this.scanCount = 0
        this.lastFpsUpdate = now
        if (this.currentFps > 0) {
          console.log(`📊 Detection FPS: ${this.currentFps} (target: 5-10 FPS)`)
        }
      }
      
      // Check if item was detected
      if (result.detected_item) {
        const itemName = result.detected_item.name
        const inferenceTime = (performance.now() - scanStartTime).toFixed(0)
        
        // Check if same item detected multiple times (stable detection)
        if (this.lastDetectedItem === itemName) {
          this.stableDetectionCount++
          console.log(`✅ Stable detection: ${itemName} (count: ${this.stableDetectionCount}/3, ${inferenceTime}ms)`)
          
          // Stop scanning after 3 stable detections
          if (this.stableDetectionCount >= 3) {
            console.log(`🎯 Detection stable for ${itemName} - stopping scan`)
            this.stopScanning()
            return
          }
        } else {
          // New item detected - reset counter
          this.lastDetectedItem = itemName
          this.stableDetectionCount = 1
          console.log(`✅ New item detected: ${itemName} (${result.detected_item.weight_grams}g, ${inferenceTime}ms)`)
        }
        
        this.notifyDetection(result.detected_item)
      } else {
        // No detection - reset stability counter
        this.stableDetectionCount = 0
        this.lastDetectedItem = null
      }
    } catch (err) {
      // Show error for debugging (but don't stop the loop)
      console.error('❌ Detection error:', err)
      console.error('   Error details:', err.response?.data || err.message)
      // Continue loop even on error - don't let errors stop scanning
    } finally {
      this.isDetecting = false
      // Loop continues immediately after this method completes
    }
  }

  /**
   * Add a listener for scanning state changes
   */
  addListener(callback) {
    this.listeners.add(callback)
    // Immediately notify of current state
    callback(this.isScanningActive())
  }

  /**
   * Remove a listener
   */
  removeListener(callback) {
    this.listeners.delete(callback)
  }

  /**
   * Notify all listeners of state change
   */
  notifyListeners(isActive) {
    this.listeners.forEach(callback => {
      try {
        callback(isActive)
      } catch (e) {
        console.error('Error in scanning listener:', e)
      }
    })
  }

  /**
   * Notify listeners of a detection
   */
  notifyDetection(detectedItem) {
    // Emit custom event for components to listen to
    window.dispatchEvent(new CustomEvent('itemDetected', {
      detail: detectedItem
    }))
  }
}

// Create singleton instance
const scanningService = new ScanningService()

// Cleanup on page unload (optional - but good practice)
window.addEventListener('beforeunload', () => {
  // Don't stop scanning on page unload - let it continue
  // Only stop when user explicitly clicks "Stop Scanning"
})

export default scanningService



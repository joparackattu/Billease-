"""
Camera Service for RTSP Stream

This service handles capturing frames from the RTSP camera stream.
Uses a continuous background thread to read RTSP and keep only the latest frame.
"""

import cv2
import base64
from typing import Optional, Tuple, Dict
import logging
import time
import threading
import numpy as np

logger = logging.getLogger(__name__)


class RTSPCameraService:
    """
    Service to capture frames from RTSP camera stream.
    
    Uses a single background thread that continuously reads RTSP frames.
    Only the latest frame is kept in memory (overwrites old frames).
    API endpoints never read RTSP directly - they just get the latest frame.
    """
    
    def __init__(self, rtsp_url: str, timeout: int = 5):
        """
        Initialize RTSP camera service.
        
        Args:
            rtsp_url: RTSP URL for the camera
            timeout: Connection timeout in seconds (default: 5)
        """
        self.rtsp_url = rtsp_url
        self.timeout = timeout
        self.working_url = None  # Will store the working URL after discovery
        
        # Crop region (ROI - Region of Interest)
        # Format: (x, y, width, height) in pixels, or None for no crop
        self.crop_region: Optional[Tuple[int, int, int, int]] = None
        
        # Latest frame storage (thread-safe)
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_frame_base64: Optional[str] = None
        self._latest_frame_timestamp: float = 0
        self._frame_lock = threading.Lock()
        
        # Background RTSP reader thread
        self._rtsp_cap: Optional[cv2.VideoCapture] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_running = False
        self._reader_lock = threading.Lock()
        
        # DO NOT start reader here - must be started explicitly via start_rtsp_reader()
        # This ensures it only starts once at app startup
        
        logger.info(f"Initialized RTSP camera service with URL: {rtsp_url.split('@')[0]}@...")
        logger.info("RTSP reader will start at app startup (not during initialization)")
    
    def start_rtsp_reader(self):
        """
        Start background thread to continuously read RTSP frames.
        
        This should be called ONCE at app startup, not per request.
        The reader will automatically reconnect if connection is lost.
        """
        if self._reader_running:
            logger.warning("RTSP reader is already running")
            return
        
        if self._reader_thread is not None:
            logger.warning("RTSP reader thread already exists (may be stale)")
            return
        
        self._reader_running = True
        self._reader_thread = threading.Thread(
            target=self._rtsp_reader_loop,
            daemon=True,
            name="RTSPReader"
        )
        self._reader_thread.start()
        logger.info("✅ Started background RTSP reader thread (will run continuously)")
    
    def _rtsp_reader_loop(self):
        """
        Background loop that continuously reads RTSP frames.
        
        Uses cap.grab() + cap.retrieve() pattern for efficient reading.
        Only keeps the latest frame in memory (overwrites old frames).
        """
        reconnect_delay = 1.0  # Wait 1 second before reconnecting
        
        while self._reader_running:
            try:
                # Create or get RTSP connection
                with self._reader_lock:
                    if self._rtsp_cap is None or not self._rtsp_cap.isOpened():
                        # Close old connection if exists
                        if self._rtsp_cap is not None:
                            try:
                                self._rtsp_cap.release()
                            except:
                                pass
                        
                        # Use working URL if available, otherwise use original
                        rtsp_url = self.working_url if self.working_url else self.rtsp_url
                        
                        # Add TCP transport if not present (more reliable)
                        if '?transport=' not in rtsp_url and '&transport=' not in rtsp_url:
                            separator = '&' if '?' in rtsp_url else '?'
                            rtsp_url = f"{rtsp_url}{separator}transport=tcp"
                        
                        logger.info(f"Connecting to RTSP stream: {rtsp_url.split('@')[0]}@...")
                        
                        # Create VideoCapture with FFMPEG backend
                        self._rtsp_cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                        
                        # CRITICAL: Set buffer size to 1 (minimal buffering)
                        self._rtsp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # Give connection a moment to establish
                        time.sleep(0.2)
                        
                        if not self._rtsp_cap.isOpened():
                            logger.warning("Failed to open RTSP connection, will retry...")
                            self._rtsp_cap = None
                            time.sleep(reconnect_delay)
                            continue
                        
                        logger.info("✅ RTSP connection established")
                
                # Continuously read frames using grab() + retrieve() pattern
                # This is more efficient than read() and allows us to skip frames if needed
                cap = self._rtsp_cap
                
                # Grab frame (non-blocking, discards old frames in buffer)
                grabbed = cap.grab()
                
                if not grabbed:
                    logger.debug("Failed to grab frame, connection may be lost")
                    # Mark connection as broken, will reconnect on next iteration
                    with self._reader_lock:
                        if self._rtsp_cap is not None:
                            try:
                                self._rtsp_cap.release()
                            except:
                                pass
                            self._rtsp_cap = None
                    time.sleep(reconnect_delay)
                    continue
                
                # Retrieve the grabbed frame
                ret, frame = cap.retrieve()
                
                if not ret or frame is None:
                    logger.debug("Failed to retrieve frame")
                    time.sleep(0.1)
                    continue
                
                # Apply crop if needed
                if self.crop_region:
                    frame = self._apply_crop(frame)
                    if frame is None:
                        continue
                
                # Store latest frame (overwrite old one)
                with self._frame_lock:
                    self._latest_frame = frame.copy()  # Copy to avoid reference issues
                    self._latest_frame_timestamp = time.time()
                    self._latest_frame_base64 = None  # Clear cached base64 (will regenerate on demand)
                
                # Read at ~30 FPS for low latency (33ms interval)
                time.sleep(0.033)
                
            except Exception as e:
                logger.error(f"RTSP reader loop error: {e}")
                # Mark connection as broken
                with self._reader_lock:
                    if self._rtsp_cap is not None:
                        try:
                            self._rtsp_cap.release()
                        except:
                            pass
                        self._rtsp_cap = None
                time.sleep(reconnect_delay)
        
        # Cleanup: release connection when stopping
        with self._reader_lock:
            if self._rtsp_cap is not None:
                try:
                    self._rtsp_cap.release()
                except:
                    pass
                self._rtsp_cap = None
        logger.info("RTSP reader thread stopped")
    
    def stop_rtsp_reader(self):
        """
        Stop background RTSP reader thread.
        
        Should only be called on app shutdown.
        """
        if not self._reader_running:
            return
        
        self._reader_running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2.0)
        logger.info("Stopped background RTSP reader")
    
    def set_crop_region(self, x: int, y: int, width: int, height: int):
        """
        Set crop region (ROI) for camera feed.
        
        Args:
            x: X coordinate of top-left corner (pixels)
            y: Y coordinate of top-left corner (pixels)
            width: Width of crop region (pixels)
            height: Height of crop region (pixels)
        """
        self.crop_region = (x, y, width, height)
        logger.info(f"Crop region set: x={x}, y={y}, width={width}, height={height}")
    
    def clear_crop_region(self):
        """Clear crop region (use full frame)."""
        self.crop_region = None
        logger.info("Crop region cleared (using full frame)")
    
    def get_crop_region(self) -> Optional[dict]:
        """
        Get current crop region settings.
        
        Returns:
            dict with crop coordinates or None if no crop
        """
        if self.crop_region:
            return {
                "x": self.crop_region[0],
                "y": self.crop_region[1],
                "width": self.crop_region[2],
                "height": self.crop_region[3]
            }
        return None
    
    def _apply_crop(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Apply crop region to frame if crop is set.
        
        Args:
            frame: OpenCV frame (numpy array)
        
        Returns:
            Cropped frame or original frame if no crop
        """
        if self.crop_region is None:
            return frame
        
        x, y, width, height = self.crop_region
        
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Validate crop region
        if x < 0 or y < 0:
            logger.warning("Crop region has negative coordinates, adjusting...")
            x = max(0, x)
            y = max(0, y)
        
        if x + width > frame_width:
            logger.warning(f"Crop width exceeds frame width, adjusting...")
            width = frame_width - x
        
        if y + height > frame_height:
            logger.warning(f"Crop height exceeds frame height, adjusting...")
            height = frame_height - y
        
        # Apply crop: frame[y:y+height, x:x+width]
        cropped = frame[y:y+height, x:x+width]
        
        if cropped.size == 0:
            logger.error("Crop region resulted in empty frame, using full frame")
            return frame
        
        return cropped
    
    def get_status(self) -> Dict:
        """
        Get current status of the RTSP reader and frame availability.
        
        Returns:
            dict: Status information including reader state, frame availability, etc.
        """
        with self._frame_lock:
            has_frame = self._latest_frame is not None
            frame_age = time.time() - self._latest_frame_timestamp if has_frame else None
        
        with self._reader_lock:
            reader_running = self._reader_running
            connection_open = self._rtsp_cap is not None and self._rtsp_cap.isOpened() if self._rtsp_cap else False
        
        return {
            "reader_running": reader_running,
            "connection_open": connection_open,
            "has_frame": has_frame,
            "frame_age_seconds": frame_age,
            "frame_too_old": frame_age > 5.0 if frame_age else None
        }
    
    def capture_frame(self, max_retries: int = 0, use_cache: bool = True, max_width: int = 1280) -> Optional[str]:
        """
        Get the latest frame from RTSP (does NOT read RTSP - uses background reader).
        
        This method never reads RTSP directly. It just returns the latest frame
        that the background thread has already captured.
        
        Args:
            max_retries: Ignored (kept for API compatibility)
            use_cache: Ignored (always uses latest frame)
            max_width: Maximum width for frame (default: 1280)
        
        Returns:
            str: Base64 encoded image string, or None if no frame available
        """
        with self._frame_lock:
            if self._latest_frame is None:
                logger.debug("No frame available yet (RTSP reader may still be connecting)")
                return None
            
            frame = self._latest_frame.copy()
            frame_timestamp = self._latest_frame_timestamp
        
        # Check if frame is too old (more than 5 seconds = connection issue)
        frame_age = time.time() - frame_timestamp
        if frame_age > 5.0:
            logger.warning(f"Latest frame is too old ({frame_age:.1f}s), RTSP connection may be lost")
            return None
        
        try:
            # Resize frame if needed
            height, width = frame.shape[:2]
            if width > max_width:
                scale = max_width / width
                new_width = max_width
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            # Encode frame to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.debug(f"Returned latest frame ({len(image_base64)} bytes, age: {time.time() - frame_timestamp:.2f}s)")
            return image_base64
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def _generate_alternative_urls(self, base_url: str) -> list:
        """
        Generate alternative RTSP URL formats to try.
        
        Args:
            base_url: Base RTSP URL (rtsp://user:pass@ip:port)
        
        Returns:
            list: List of alternative RTSP URLs to try
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        alternatives = [
            f"{base}/stream1",
            f"{base}/stream2",
            f"{base}/cam/realmonitor?channel=1&subtype=0",  # Main stream
            f"{base}/cam/realmonitor?channel=1&subtype=1",  # Sub stream
            f"{base}/cam/realmonitor?channel=1&subtype=0&transport=tcp",
            f"{base}/cam/realmonitor?channel=1&subtype=1&transport=tcp",
            f"{base}/stream1?transport=tcp",
            f"{base}/stream2?transport=tcp",
        ]
        
        return alternatives
    
    def test_connection(self, try_alternatives: bool = True, quick_test: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Test if RTSP connection is working.
        
        Args:
            try_alternatives: If True, try alternative URL formats if primary fails
            quick_test: If True, use shorter timeout and skip alternatives if we have a working URL
        
        Returns:
            tuple: (success: bool, working_url: Optional[str])
        """
        # If we already have a working URL and doing quick test, try it first
        if quick_test and self.working_url:
            urls_to_try = [self.working_url, self.rtsp_url]
        else:
            urls_to_try = [self.rtsp_url]
        
        # If primary fails and we should try alternatives, generate them
        if try_alternatives and not quick_test:
            urls_to_try.extend(self._generate_alternative_urls(self.rtsp_url))
        
        # Use shorter timeout for quick tests
        test_timeout = 5 if quick_test else self.timeout
        
        for url in urls_to_try:
            cap = None
            try:
                if not quick_test:
                    logger.info(f"Testing RTSP connection with: {url.split('@')[0]}@...")
                
                # Create capture with this URL
                rtsp_url = url
                if '?transport=' not in rtsp_url and '&transport=' not in rtsp_url:
                    separator = '&' if '?' in rtsp_url else '?'
                    rtsp_url = f"{rtsp_url}{separator}transport=tcp"
                
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Set a timeout by trying to read quickly
                if not cap.isOpened():
                    if not quick_test:
                        logger.debug(f"Failed to open: {url.split('@')[0]}@...")
                    continue
                
                # Try to read a frame with timeout
                start_time = time.time()
                ret, frame = cap.read()
                elapsed = time.time() - start_time
                
                # For quick test, fail fast if it takes too long
                if elapsed > test_timeout:
                    if not quick_test:
                        logger.debug(f"Timeout for: {url.split('@')[0]}@... (took {elapsed:.2f}s)")
                    cap.release()
                    continue
                
                if ret and frame is not None:
                    if not quick_test:
                        logger.info(f"✅ RTSP connection SUCCESS with: {url.split('@')[0]}@...")
                        logger.info(f"   Frame size: {frame.shape}")
                    self.working_url = url  # Store working URL
                    return True, url
                else:
                    if not quick_test:
                        logger.debug(f"No frame received from: {url.split('@')[0]}@...")
                    cap.release()
                    continue
                    
            except Exception as e:
                if not quick_test:
                    logger.debug(f"Error testing {url.split('@')[0]}@...: {str(e)}")
                if cap is not None:
                    cap.release()
                continue
            finally:
                if cap is not None:
                    cap.release()
        
        if not quick_test:
            logger.warning("❌ RTSP connection test: FAILED (tried all URL formats)")
        return False, None
    
    def test_connection_simple(self) -> bool:
        """
        Simple test that returns only bool (for backward compatibility).
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        success, _ = self.test_connection()
        return success
    
    def get_working_url(self) -> Optional[str]:
        """
        Get the working RTSP URL (if discovered).
        
        Returns:
            str: Working RTSP URL, or None if not yet discovered
        """
        return self.working_url
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        self.stop_rtsp_reader()


# Global camera service instance
# Will be initialized in main.py
camera_service: Optional[RTSPCameraService] = None

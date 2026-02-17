/**
 * Network Detection Utilities
 * Detects network connectivity and Adobe PDF Embed API availability
 */

export interface NetworkStatus {
  isOnline: boolean;
  isAdobeAPIAvailable: boolean;
  shouldUseFallback: boolean;
}

/**
 * Check if the browser is online
 */
export const checkOnlineStatus = (): boolean => {
  return navigator.onLine;
};

/**
 * Check if Adobe PDF Embed API is available
 */
export const checkAdobeAPIAvailability = async (): Promise<boolean> => {
  try {
    // Check if Adobe DC View is loaded
    if (typeof window !== 'undefined' && window.AdobeDC) {
      return true;
    }

    // Try to load Adobe PDF Embed API
    const response = await fetch('https://documentservices.adobe.com/view-sdk/viewer.js', {
      method: 'HEAD',
      mode: 'no-cors',
      cache: 'no-cache'
    });
    
    return true; // If no error, API is available
  } catch (error) {
    console.warn('Adobe PDF Embed API not available:', error);
    return false;
  }
};

/**
 * Comprehensive network and API status check
 */
export const getNetworkStatus = async (): Promise<NetworkStatus> => {
  const isOnline = checkOnlineStatus();
  
  if (!isOnline) {
    return {
      isOnline: false,
      isAdobeAPIAvailable: false,
      shouldUseFallback: true
    };
  }

  const isAdobeAPIAvailable = await checkAdobeAPIAvailability();
  
  return {
    isOnline,
    isAdobeAPIAvailable,
    shouldUseFallback: !isAdobeAPIAvailable
  };
};

/**
 * Create a network status monitor
 */
export class NetworkStatusMonitor {
  private listeners: ((status: NetworkStatus) => void)[] = [];
  private currentStatus: NetworkStatus | null = null;
  private checkInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.startMonitoring();
  }

  /**
   * Add a listener for network status changes
   */
  addListener(callback: (status: NetworkStatus) => void) {
    this.listeners.push(callback);
    
    // Immediately call with current status if available
    if (this.currentStatus) {
      callback(this.currentStatus);
    }
  }

  /**
   * Remove a listener
   */
  removeListener(callback: (status: NetworkStatus) => void) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  /**
   * Start monitoring network status
   */
  private startMonitoring() {
    // Initial check
    this.checkStatus();

    // Listen to online/offline events
    window.addEventListener('online', () => this.checkStatus());
    window.addEventListener('offline', () => this.checkStatus());

    // Periodic check every 30 seconds
    this.checkInterval = setInterval(() => {
      this.checkStatus();
    }, 30000);
  }

  /**
   * Stop monitoring
   */
  stopMonitoring() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    
    window.removeEventListener('online', () => this.checkStatus());
    window.removeEventListener('offline', () => this.checkStatus());
  }

  /**
   * Check current network status
   */
  private async checkStatus() {
    try {
      const newStatus = await getNetworkStatus();
      
      // Only notify if status changed
      if (!this.currentStatus || 
          this.currentStatus.isOnline !== newStatus.isOnline ||
          this.currentStatus.isAdobeAPIAvailable !== newStatus.isAdobeAPIAvailable ||
          this.currentStatus.shouldUseFallback !== newStatus.shouldUseFallback) {
        
        this.currentStatus = newStatus;
        this.notifyListeners(newStatus);
      }
    } catch (error) {
      console.error('Error checking network status:', error);
      
      // Fallback to offline mode on error
      const fallbackStatus: NetworkStatus = {
        isOnline: false,
        isAdobeAPIAvailable: false,
        shouldUseFallback: true
      };
      
      this.currentStatus = fallbackStatus;
      this.notifyListeners(fallbackStatus);
    }
  }

  /**
   * Notify all listeners of status change
   */
  private notifyListeners(status: NetworkStatus) {
    console.log('📡 Network status changed:', status);
    this.listeners.forEach(callback => {
      try {
        callback(status);
      } catch (error) {
        console.error('Error in network status listener:', error);
      }
    });
  }

  /**
   * Get current status synchronously
   */
  getCurrentStatus(): NetworkStatus | null {
    return this.currentStatus;
  }

  /**
   * Force a status check
   */
  async forceCheck(): Promise<NetworkStatus> {
    await this.checkStatus();
    return this.currentStatus!;
  }
}

// Global network status monitor instance
export const networkMonitor = new NetworkStatusMonitor();

/**
 * React hook for network status
 */
export const useNetworkStatus = () => {
  const [status, setStatus] = React.useState<NetworkStatus | null>(null);

  React.useEffect(() => {
    const handleStatusChange = (newStatus: NetworkStatus) => {
      setStatus(newStatus);
    };

    networkMonitor.addListener(handleStatusChange);

    // Get initial status
    const currentStatus = networkMonitor.getCurrentStatus();
    if (currentStatus) {
      setStatus(currentStatus);
    }

    return () => {
      networkMonitor.removeListener(handleStatusChange);
    };
  }, []);

  return status;
};

// Import React for the hook
import React from 'react';

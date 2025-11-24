'use client';

import React, { useState, useRef, useEffect } from 'react';

interface Anchor {
  id: number;
  mac_address: string;
  name: string;
  x_position: number;
  y_position: number;
  is_active: boolean;
}

interface Position {
  id: number;
  tag_id: string;
  x_position: number;
  y_position: number;
  confidence: number;
  timestamp: string;
}

interface Item {
  product_id: string;
  product_name: string;
  x_position: number;
  y_position: number;
  status: string; // "present", "missing", "unknown"
}

type ViewMode = 'live' | 'stock-heatmap' | 'purchase-heatmap' | 'restock-queue';

interface StoreMapProps {
  anchors: Anchor[];
  positions: Position[];
  items: Item[];
  setupMode: boolean;
  viewMode?: ViewMode;
  stockHeatmap?: any[];
  purchaseHeatmap?: any[];
  restockQueue?: any[];
  highlightedItem?: string | null;
  onAnchorPlace?: (x: number, y: number, anchorIndex: number) => void;
  onAnchorUpdate?: (anchorId: number, x: number, y: number) => void;
  onItemClick?: (item: Item) => void;
}

const STORE_WIDTH = 1000;  // 10 meters in cm
const STORE_HEIGHT = 800;  // 8 meters in cm

export default function StoreMap({ 
  anchors, 
  positions,
  items,
  setupMode,
  viewMode = 'live',
  stockHeatmap = [],
  purchaseHeatmap = [],
  restockQueue = [],
  highlightedItem = null,
  onAnchorPlace,
  onAnchorUpdate,
  onItemClick 
}: StoreMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggedAnchor, setDraggedAnchor] = useState<number | null>(null);
  const [hoveredAnchor, setHoveredAnchor] = useState<number | null>(null);
  const [nextAnchorIndex, setNextAnchorIndex] = useState(0);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 640 });

  // Convert store coordinates (cm) to canvas coordinates (pixels)
  const toCanvasCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = canvas.width / STORE_WIDTH;
    const scaleY = canvas.height / STORE_HEIGHT;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  };

  // Convert canvas coordinates to store coordinates
  const toStoreCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = STORE_WIDTH / canvas.width;
    const scaleY = STORE_HEIGHT / canvas.height;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  };

  // Draw heatmap overlay for zones
  const drawHeatmap = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, data: any[], type: 'stock' | 'purchase') => {
    if (!data || data.length === 0) return;
    
    // Find max value for normalization
    const maxValue = Math.max(...data.map(d => type === 'stock' ? d.item_count : d.purchase_count));
    if (maxValue === 0) return;
    
    // Draw zones with heat colors
    data.forEach(entry => {
      const zone = entry.zone;
      const value = type === 'stock' ? entry.item_count : entry.purchase_count;
      const intensity = value / maxValue;
      
      // Convert zone coordinates
      const topLeft = toCanvasCoords(zone.x_min, zone.y_min, canvas);
      const bottomRight = toCanvasCoords(zone.x_max, zone.y_max, canvas);
      const width = bottomRight.x - topLeft.x;
      const height = bottomRight.y - topLeft.y;
      
      // Heat color: blue (low) -> yellow -> red (high)
      let r, g, b;
      if (intensity < 0.5) {
        r = Math.floor(intensity * 2 * 255);
        g = Math.floor(intensity * 2 * 255);
        b = 255;
      } else {
        r = 255;
        g = Math.floor((1 - intensity) * 2 * 255);
        b = 0;
      }
      
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.3)`;
      ctx.fillRect(topLeft.x, topLeft.y, width, height);
      
      // Draw zone border
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.6)`;
      ctx.lineWidth = 2;
      ctx.strokeRect(topLeft.x, topLeft.y, width, height);
      
      // Draw value label
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 24px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(value.toString(), topLeft.x + width/2, topLeft.y + height/2);
    });
  };

  // Draw the entire map
  const drawMap = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas with white background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    const gridSize = 100; // 1 meter grid
    for (let x = 0; x < STORE_WIDTH; x += gridSize) {
      const canvasX = toCanvasCoords(x, 0, canvas).x;
      ctx.beginPath();
      ctx.moveTo(canvasX, 0);
      ctx.lineTo(canvasX, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < STORE_HEIGHT; y += gridSize) {
      const canvasY = toCanvasCoords(0, y, canvas).y;
      ctx.beginPath();
      ctx.moveTo(0, canvasY);
      ctx.lineTo(canvas.width, canvasY);
      ctx.stroke();
    }

    // Draw store boundary
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, canvas.width, canvas.height);

    // Draw aisles (4 vertical aisles at x=200, 400, 600, 800)
    const aisleX = [200, 400, 600, 800];
    const aisleStartY = 150;
    const aisleEndY = 700;
    const aisleWidth = 80; // 80cm wide aisles
    
    aisleX.forEach((x, index) => {
      const leftEdge = toCanvasCoords(x - aisleWidth / 2, aisleStartY, canvas);
      const rightEdge = toCanvasCoords(x + aisleWidth / 2, aisleStartY, canvas);
      const bottomY = toCanvasCoords(x, aisleEndY, canvas).y;
      
      // Draw aisle background
      ctx.fillStyle = 'rgba(243, 244, 246, 0.8)';
      ctx.fillRect(leftEdge.x, leftEdge.y, rightEdge.x - leftEdge.x, bottomY - leftEdge.y);
      
      // Draw aisle borders (shelving edges)
      ctx.strokeStyle = '#9ca3af';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(leftEdge.x, leftEdge.y);
      ctx.lineTo(leftEdge.x, bottomY);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(rightEdge.x, leftEdge.y);
      ctx.lineTo(rightEdge.x, bottomY);
      ctx.stroke();
      
      // Draw aisle label
      ctx.fillStyle = '#6b7280';
      ctx.font = 'bold 28px sans-serif';
      ctx.textAlign = 'center';
      const labelPos = toCanvasCoords(x, aisleStartY - 30, canvas);
      ctx.fillText(`Aisle ${index + 1}`, labelPos.x, labelPos.y);
    });
    
    // Draw cross aisle (horizontal at y=400)
    const crossAisleY = 400;
    const crossAisleHeight = 80;
    const crossLeftEdge = toCanvasCoords(0, crossAisleY - crossAisleHeight / 2, canvas);
    const crossRightEdge = toCanvasCoords(STORE_WIDTH, crossAisleY + crossAisleHeight / 2, canvas);
    
    ctx.fillStyle = 'rgba(243, 244, 246, 0.6)';
    ctx.fillRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);

    // Draw heatmap overlays for non-live modes
    if (viewMode === 'stock-heatmap') {
      drawHeatmap(ctx, canvas, stockHeatmap, 'stock');
    } else if (viewMode === 'purchase-heatmap') {
      drawHeatmap(ctx, canvas, purchaseHeatmap, 'purchase');
    }

    // Draw items on the map (only in live mode)
    if (viewMode === 'live') {
      const missingItems = items.filter(item => item.status === 'missing');
      const presentItems = items.filter(item => item.status !== 'missing');
      
      // Draw present items first (so missing items are on top)
      presentItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      const isHighlighted = highlightedItem && item.product_id === highlightedItem;
      
      // Draw highlight glow if this item is selected
      if (isHighlighted) {
        ctx.fillStyle = 'rgba(255, 215, 0, 0.4)';  // Gold glow
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 28, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      // Draw item as small square with subtle glow
      ctx.fillStyle = isHighlighted ? 'rgba(255, 215, 0, 0.9)' : 'rgba(34, 197, 94, 0.6)';  // Gold if highlighted, green otherwise
      ctx.fillRect(pos.x - 6, pos.y - 6, 12, 12);
      ctx.strokeStyle = isHighlighted ? '#FFD700' : '#22c55e';
      ctx.lineWidth = isHighlighted ? 4 : 2;
      ctx.strokeRect(pos.x - 6, pos.y - 6, 12, 12);
    });
    
    // Draw missing items on top with emphasis
    missingItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      const isHighlighted = highlightedItem && item.product_id === highlightedItem;
      
      // Pulsing glow effect for missing items
      ctx.fillStyle = isHighlighted ? 'rgba(255, 215, 0, 0.4)' : 'rgba(239, 68, 68, 0.3)';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isHighlighted ? 32 : 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw missing item as prominent square
      ctx.fillStyle = isHighlighted ? '#FFD700' : '#ef4444';  // Gold if highlighted, red otherwise
      ctx.fillRect(pos.x - 10, pos.y - 10, 20, 20);
      ctx.strokeStyle = isHighlighted ? '#FFA500' : '#fca5a5';
      ctx.lineWidth = isHighlighted ? 6 : 4;
      ctx.strokeRect(pos.x - 10, pos.y - 10, 20, 20);
      
      // Draw warning icon
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 32px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('!', pos.x, pos.y + 10);
    });
    }

    // Draw distance circles from anchors to tags (only for the most recent position in live mode)
    if (viewMode === 'live' && !setupMode && positions.length > 0) {
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.15)';
      ctx.lineWidth = 2;
      
      // Only draw circles for the first (most recent) position
      const recentPos = positions[0];
      anchors.forEach(anchor => {
        if (!anchor.is_active) return;
        
        const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
        const distance = Math.sqrt(
          Math.pow(recentPos.x_position - anchor.x_position, 2) +
          Math.pow(recentPos.y_position - anchor.y_position, 2)
        );
        
        const radiusPx = distance * (canvas.width / STORE_WIDTH);
        
        ctx.beginPath();
        ctx.arc(anchorCanvas.x, anchorCanvas.y, radiusPx, 0, 2 * Math.PI);
        ctx.stroke();
      });
    }

    // Draw anchors
    anchors.forEach((anchor, index) => {
      const pos = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      
      // Anchor circle - royal blue
      ctx.fillStyle = anchor.is_active ? '#0055A4' : '#9ca3af';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Highlight if hovered or dragged
      if (hoveredAnchor === anchor.id || draggedAnchor === anchor.id) {
        ctx.strokeStyle = '#1a6bbb';
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 30, 0, 2 * Math.PI);
        ctx.stroke();
      }
      
      // Anchor label
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 24px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(anchor.name || anchor.mac_address, pos.x, pos.y - 40);
      
      // MAC address
      ctx.font = '20px sans-serif';
      ctx.fillStyle = '#6b7280';
      ctx.fillText(anchor.mac_address, pos.x, pos.y + 60);
    });

    // Draw employee positions (from UWB triangulation) - only in live mode
    if (viewMode === 'live' && positions.length > 0) {
      // Draw trail for previous positions (fading)
      for (let i = Math.min(positions.length - 1, 5); i > 0; i--) {
        const pos = positions[i];
        const canvasPos = toCanvasCoords(pos.x_position, pos.y_position, canvas);
        const alpha = (5 - i) / 8;
        
        ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
        ctx.beginPath();
        ctx.arc(canvasPos.x, canvasPos.y, 8, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      // Draw current employee position (most recent)
      const currentPos = positions[0];
      const canvasPos = toCanvasCoords(currentPos.x_position, currentPos.y_position, canvas);
      
      // 1.5m detection radius circle (RFID range)
      ctx.strokeStyle = 'rgba(0, 85, 164, 0.3)';
      ctx.lineWidth = 4;
      ctx.setLineDash([16, 8]);
      const radiusCm = 150; // 1.5 meters RFID range
      const radiusPx = radiusCm * (canvas.width / STORE_WIDTH);
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, radiusPx, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Outer glow for employee
      ctx.fillStyle = 'rgba(0, 85, 164, 0.15)';
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, 48, 0, 2 * Math.PI);
      ctx.fill();
      
      // Employee icon - royal blue (scaled 2x)
      ctx.fillStyle = '#0055A4';
      ctx.strokeStyle = '#1a6bbb';
      ctx.lineWidth = 4;
      
      // Head
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y - 16, 16, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      
      // Body
      ctx.fillStyle = '#0055A4';
      ctx.fillRect(canvasPos.x - 12, canvasPos.y + 4, 24, 28);
      ctx.strokeRect(canvasPos.x - 12, canvasPos.y + 4, 24, 28);
      
      // Employee label
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 26px sans-serif';
      ctx.textAlign = 'center';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.9)';
      ctx.shadowBlur = 6;
      ctx.fillText('Employee', canvasPos.x, canvasPos.y - 64);
      ctx.shadowBlur = 0;
      
      // Position coordinates
      ctx.font = '20px monospace';
      ctx.fillStyle = '#374151';
      ctx.fillText(`(${Math.round(currentPos.x_position)}, ${Math.round(currentPos.y_position)})`, canvasPos.x, canvasPos.y + 60);
    }

  };

  // Removed drawMissingItemsAlert function - now displayed in sidebar

  // Handle responsive canvas sizing
  useEffect(() => {
    const updateCanvasSize = () => {
      if (!containerRef.current) return;
      
      const container = containerRef.current;
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      
      // Maintain aspect ratio of STORE_WIDTH:STORE_HEIGHT (1000:800 = 1.25:1)
      const aspectRatio = STORE_WIDTH / STORE_HEIGHT;
      
      let width = containerWidth;
      let height = width / aspectRatio;
      
      // If height exceeds container, constrain by height instead
      if (height > containerHeight) {
        height = containerHeight;
        width = height * aspectRatio;
      }
      
      // Increase resolution by 2x for sharper rendering
      setCanvasSize({ 
        width: Math.floor(width * 2), 
        height: Math.floor(height * 2) 
      });
    };
    
    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    
    return () => window.removeEventListener('resize', updateCanvasSize);
  }, []);

  // Redraw when data changes
  useEffect(() => {
    drawMap();
    // Removed drawMissingItemsAlert - now shown in sidebar instead
  }, [anchors, positions, items, setupMode, hoveredAnchor, draggedAnchor, canvasSize, viewMode, stockHeatmap, purchaseHeatmap]);

  // Removed auto-pulsing animation for missing items alert (now shown in sidebar)

  // Handle canvas click (place new anchor in setup mode)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    // Get click position in displayed coordinates
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    // If in setup mode, handle anchor placement
    if (setupMode && onAnchorPlace) {
      if (draggedAnchor !== null) return; // Don't place if we were dragging
      const storeCoords = toStoreCoords(x, y, canvas);
      onAnchorPlace(storeCoords.x, storeCoords.y, nextAnchorIndex);
      setNextAnchorIndex(nextAnchorIndex + 1);
      return;
    }
    
    // If in live mode and onItemClick is provided, check for item clicks
    if (viewMode === 'live' && onItemClick) {
      const storeCoords = toStoreCoords(x, y, canvas);
      const clickRadius = 15; // pixels
      
      // Check if click is near any item
      for (const item of items) {
        const distance = Math.sqrt(
          Math.pow(storeCoords.x - item.x_position, 2) + 
          Math.pow(storeCoords.y - item.y_position, 2)
        );
        
        // Convert distance to canvas pixels for comparison
        const distancePx = distance * (canvas.width / STORE_WIDTH);
        
        if (distancePx < clickRadius) {
          onItemClick(item);
          return;
        }
      }
    }
  };

  // Handle mouse down (start dragging)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    // Check if clicking on an anchor
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 30) {  // Increased radius for easier clicking
        setDraggedAnchor(anchor.id);
        break;
      }
    }
  };

  // Handle mouse move (dragging)
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    if (draggedAnchor !== null && setupMode && onAnchorUpdate) {
      const storeCoords = toStoreCoords(x, y, canvas);
      onAnchorUpdate(draggedAnchor, storeCoords.x, storeCoords.y);
    }
    
    // Update hover state
    let hovering = null;
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 30) {  // Increased radius for easier hovering
        hovering = anchor.id;
        break;
      }
    }
    setHoveredAnchor(hovering);
  };

  // Handle mouse up (stop dragging)
  const handleMouseUp = () => {
    setDraggedAnchor(null);
  };

  return (
    <div ref={containerRef} className="relative w-full h-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={canvasSize.width}
        height={canvasSize.height}
        style={{
          width: `${canvasSize.width / 2}px`,
          height: `${canvasSize.height / 2}px`
        }}
        className="border-2 border-gray-300 cursor-crosshair"
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
      
      {setupMode && (
        <div className="absolute top-4 right-4 bg-[#0055A4] text-white px-4 py-2 text-sm font-medium">
          Click to place anchor #{nextAnchorIndex + 1}<br/>
          Drag existing anchors to reposition
        </div>
      )}
    </div>
  );
}

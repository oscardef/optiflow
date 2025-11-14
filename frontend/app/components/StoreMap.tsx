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

interface StoreMapProps {
  anchors: Anchor[];
  positions: Position[];
  items: Item[];
  setupMode: boolean;
  onAnchorPlace?: (x: number, y: number, anchorIndex: number) => void;
  onAnchorUpdate?: (anchorId: number, x: number, y: number) => void;
}

const STORE_WIDTH = 1000;  // 10 meters in cm
const STORE_HEIGHT = 800;  // 8 meters in cm

export default function StoreMap({ 
  anchors, 
  positions,
  items,
  setupMode, 
  onAnchorPlace,
  onAnchorUpdate 
}: StoreMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [draggedAnchor, setDraggedAnchor] = useState<number | null>(null);
  const [hoveredAnchor, setHoveredAnchor] = useState<number | null>(null);
  const [nextAnchorIndex, setNextAnchorIndex] = useState(0);

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

  // Draw the entire map
  const drawMap = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = '#2a2a2a';
    ctx.lineWidth = 1;
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
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 2;
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
      
      // Draw aisle background (lighter floor)
      ctx.fillStyle = 'rgba(60, 60, 80, 0.3)';
      ctx.fillRect(leftEdge.x, leftEdge.y, rightEdge.x - leftEdge.x, bottomY - leftEdge.y);
      
      // Draw aisle borders (shelving edges)
      ctx.strokeStyle = 'rgba(100, 100, 120, 0.5)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(leftEdge.x, leftEdge.y);
      ctx.lineTo(leftEdge.x, bottomY);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(rightEdge.x, leftEdge.y);
      ctx.lineTo(rightEdge.x, bottomY);
      ctx.stroke();
      
      // Draw aisle label
      ctx.fillStyle = '#8888aa';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'center';
      const labelPos = toCanvasCoords(x, aisleStartY - 30, canvas);
      ctx.fillText(`Aisle ${index + 1}`, labelPos.x, labelPos.y);
    });
    
    // Draw cross aisle (horizontal at y=400)
    const crossAisleY = 400;
    const crossAisleHeight = 80;
    const crossLeftEdge = toCanvasCoords(0, crossAisleY - crossAisleHeight / 2, canvas);
    const crossRightEdge = toCanvasCoords(STORE_WIDTH, crossAisleY + crossAisleHeight / 2, canvas);
    
    ctx.fillStyle = 'rgba(60, 60, 80, 0.2)';
    ctx.fillRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);
    ctx.strokeStyle = 'rgba(100, 100, 120, 0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);

    // Draw items on the map
    const missingItems = items.filter(item => item.status === 'missing');
    const presentItems = items.filter(item => item.status !== 'missing');
    
    // Draw present items first (so missing items are on top)
    presentItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      
      // Draw item as small square with subtle glow
      ctx.fillStyle = 'rgba(34, 197, 94, 0.6)';  // Green for present
      ctx.fillRect(pos.x - 3, pos.y - 3, 6, 6);
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 1;
      ctx.strokeRect(pos.x - 3, pos.y - 3, 6, 6);
    });
    
    // Draw missing items on top with emphasis
    missingItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      
      // Pulsing glow effect for missing items
      ctx.fillStyle = 'rgba(239, 68, 68, 0.3)';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 12, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw missing item as prominent square
      ctx.fillStyle = '#ef4444';  // Bright red
      ctx.fillRect(pos.x - 5, pos.y - 5, 10, 10);
      ctx.strokeStyle = '#fca5a5';
      ctx.lineWidth = 2;
      ctx.strokeRect(pos.x - 5, pos.y - 5, 10, 10);
      
      // Draw warning icon
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('!', pos.x, pos.y + 5);
    });

    // Draw distance circles from anchors to tags (only for the most recent position)
    if (!setupMode && positions.length > 0) {
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.15)';
      ctx.lineWidth = 1;
      
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
      
      // Anchor circle
      ctx.fillStyle = anchor.is_active ? '#3b82f6' : '#6b7280';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 12, 0, 2 * Math.PI);
      ctx.fill();
      
      // Highlight if hovered or dragged
      if (hoveredAnchor === anchor.id || draggedAnchor === anchor.id) {
        ctx.strokeStyle = '#60a5fa';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 15, 0, 2 * Math.PI);
        ctx.stroke();
      }
      
      // Anchor label
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(anchor.name || anchor.mac_address, pos.x, pos.y - 20);
      
      // MAC address
      ctx.font = '10px sans-serif';
      ctx.fillStyle = '#aaa';
      ctx.fillText(anchor.mac_address, pos.x, pos.y + 30);
    });

    // Draw employee positions (from UWB triangulation)
    if (positions.length > 0) {
      // Draw trail for previous positions (fading)
      for (let i = Math.min(positions.length - 1, 5); i > 0; i--) {
        const pos = positions[i];
        const canvasPos = toCanvasCoords(pos.x_position, pos.y_position, canvas);
        const alpha = (5 - i) / 8;
        
        ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
        ctx.beginPath();
        ctx.arc(canvasPos.x, canvasPos.y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      // Draw current employee position (most recent)
      const currentPos = positions[0];
      const canvasPos = toCanvasCoords(currentPos.x_position, currentPos.y_position, canvas);
      
      // 1.5m detection radius circle (RFID range)
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);
      const radiusCm = 150; // 1.5 meters RFID range
      const radiusPx = radiusCm * (canvas.width / STORE_WIDTH);
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, radiusPx, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Outer glow for employee
      ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Employee icon (larger, more prominent)
      ctx.fillStyle = '#3b82f6';
      ctx.strokeStyle = '#60a5fa';
      ctx.lineWidth = 2;
      
      // Head
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y - 8, 8, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      
      // Body
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(canvasPos.x - 6, canvasPos.y + 2, 12, 14);
      ctx.strokeRect(canvasPos.x - 6, canvasPos.y + 2, 12, 14);
      
      // Employee label with emoji
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 13px sans-serif';
      ctx.textAlign = 'center';
      ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
      ctx.shadowBlur = 4;
      ctx.fillText('� Employee', canvasPos.x, canvasPos.y - 32);
      ctx.shadowBlur = 0;
      
      // Position coordinates (for debugging)
      ctx.font = '10px monospace';
      ctx.fillStyle = '#93c5fd';
      ctx.fillText(`(${Math.round(currentPos.x_position)}, ${Math.round(currentPos.y_position)})`, canvasPos.x, canvasPos.y + 30);
    }

    // Draw legend
    const legendX = 20;
    const legendY = 20;
    const legendHeight = setupMode ? 80 : 140;
    ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
    ctx.fillRect(legendX, legendY, 180, legendHeight);
    ctx.strokeStyle = 'rgba(100, 100, 120, 0.5)';
    ctx.lineWidth = 1;
    ctx.strokeRect(legendX, legendY, 180, legendHeight);
    
    ctx.font = 'bold 13px sans-serif';
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'left';
    ctx.fillText('📊 Live Store Map', legendX + 10, legendY + 20);
    
    if (!setupMode) {
      // Employee
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(legendX + 17, legendY + 40, 8, 10);
      ctx.fillStyle = '#e0e7ff';
      ctx.font = '11px sans-serif';
      ctx.fillText('� Employee', legendX + 35, legendY + 49);
      
      // Item - Present
      ctx.fillStyle = '#22c55e';
      ctx.fillRect(legendX + 17, legendY + 60, 6, 6);
      ctx.fillStyle = '#d1fae5';
      ctx.fillText('✓ Item Detected', legendX + 35, legendY + 67);
      
      // Item - Missing
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(legendX + 17, legendY + 80, 10, 10);
      ctx.fillStyle = '#fef2f2';
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText('⚠️  Missing Item', legendX + 35, legendY + 89);
      
      // Detection range
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.5)';
      ctx.setLineDash([4, 2]);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(legendX + 22, legendY + 105, 10, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.fillText('1.5m RFID Range', legendX + 35, legendY + 109);
    } else {
      // Anchor in setup mode
      ctx.fillStyle = '#3b82f6';
      ctx.beginPath();
      ctx.arc(legendX + 22, legendY + 45, 7, 0, 2 * Math.PI);
      ctx.fill();
      ctx.fillStyle = '#ddd';
      ctx.font = '11px sans-serif';
      ctx.fillText('UWB Anchor', legendX + 35, legendY + 49);
    }
    
    // Grid info
    ctx.fillStyle = '#64748b';
    ctx.font = '9px sans-serif';
    ctx.fillText('Grid: 1m × 1m', legendX + 10, legendY + legendHeight - 8);
  };

  // Removed drawMissingItemsAlert function - now displayed in sidebar

  // Redraw when data changes
  useEffect(() => {
    drawMap();
    // Removed drawMissingItemsAlert - now shown in sidebar instead
  }, [anchors, positions, items, setupMode, hoveredAnchor, draggedAnchor]);

  // Removed auto-pulsing animation for missing items alert (now shown in sidebar)

  // Handle canvas click (place new anchor in setup mode)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode || !onAnchorPlace) return;
    if (draggedAnchor !== null) return; // Don't place if we were dragging
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const storeCoords = toStoreCoords(x, y, canvas);
    onAnchorPlace(storeCoords.x, storeCoords.y, nextAnchorIndex);
    setNextAnchorIndex(nextAnchorIndex + 1);
  };

  // Handle mouse down (start dragging)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Check if clicking on an anchor
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 15) {
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
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
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
      
      if (distance < 15) {
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
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={800}
        height={640}
        className="border-2 border-slate-700 rounded-lg cursor-crosshair"
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
      
      {setupMode && (
        <div className="absolute top-4 right-4 bg-blue-900/80 text-white px-4 py-2 rounded-lg text-sm">
          Click to place anchor #{nextAnchorIndex + 1}<br/>
          Drag existing anchors to reposition
        </div>
      )}
      
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div className="bg-slate-800 p-3 rounded-lg">
          <p className="text-slate-400 mb-1">Store Layout</p>
          <p className="text-white font-semibold">{STORE_WIDTH/100}m × {STORE_HEIGHT/100}m</p>
          <p className="text-slate-400 text-xs mt-1">4 Aisles + Cross Section</p>
        </div>
        
        <div className="bg-slate-800 p-3 rounded-lg">
          <p className="text-slate-400 mb-1">UWB Tracking</p>
          <p className="text-white font-semibold">{anchors.filter(a => a.is_active).length} Anchors Active</p>
          {positions.length > 0 && (
            <p className="text-green-400 text-xs mt-1">✓ Employee Tracked</p>
          )}
        </div>
        
        <div className="bg-slate-800 p-3 rounded-lg">
          <p className="text-slate-400 mb-1">Inventory</p>
          <p className="text-white font-semibold">{items.length} Items Detected</p>
          <p className="text-green-400 text-xs mt-1">
            {items.filter(i => i.status !== 'missing').length} Present
          </p>
        </div>
        
        <div className={`p-3 rounded-lg ${items.filter(i => i.status === 'missing').length > 0 ? 'bg-red-900/40 border-2 border-red-500' : 'bg-slate-800'}`}>
          <p className="text-slate-400 mb-1">Missing Items</p>
          <p className={`font-bold text-2xl ${items.filter(i => i.status === 'missing').length > 0 ? 'text-red-400' : 'text-white'}`}>
            {items.filter(i => i.status === 'missing').length}
          </p>
          {items.filter(i => i.status === 'missing').length > 0 && (
            <p className="text-red-300 text-xs mt-1">⚠️ Restock Required</p>
          )}
        </div>
      </div>
    </div>
  );
}

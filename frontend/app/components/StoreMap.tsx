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
    ctx.strokeStyle = '#333';
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

    // Draw items on the map
    items.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      
      // Item appearance based on status
      let fillColor, strokeColor;
      if (item.status === 'missing') {
        fillColor = '#ef4444';  // Red for missing
        strokeColor = '#dc2626';
      } else if (item.status === 'present') {
        fillColor = '#f59e0b';  // Orange for present
        strokeColor = '#d97706';
      } else {
        fillColor = '#6b7280';  // Gray for unknown
        strokeColor = '#4b5563';
      }
      
      // Draw item as small square
      ctx.fillStyle = fillColor;
      ctx.fillRect(pos.x - 4, pos.y - 4, 8, 8);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(pos.x - 4, pos.y - 4, 8, 8);
      
      // Draw warning icon for missing items
      if (item.status === 'missing') {
        ctx.fillStyle = '#fef2f2';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('!', pos.x, pos.y + 4);
      }
    });

    // Draw distance circles from anchors to tags (if not in setup mode)
    if (!setupMode && positions.length > 0) {
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.2)';
      ctx.lineWidth = 1;
      
      positions.forEach(pos => {
        anchors.forEach(anchor => {
          if (!anchor.is_active) return;
          
          const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
          const distance = Math.sqrt(
            Math.pow(pos.x_position - anchor.x_position, 2) +
            Math.pow(pos.y_position - anchor.y_position, 2)
          );
          
          const radiusPx = distance * (canvas.width / STORE_WIDTH);
          
          ctx.beginPath();
          ctx.arc(anchorCanvas.x, anchorCanvas.y, radiusPx, 0, 2 * Math.PI);
          ctx.stroke();
        });
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

    // Draw tag positions
    positions.forEach((pos, index) => {
      const canvasPos = toCanvasCoords(pos.x_position, pos.y_position, canvas);
      
      // Confidence indicator (outer circle)
      const alpha = pos.confidence;
      ctx.fillStyle = `rgba(16, 185, 129, ${alpha * 0.3})`;
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, 20, 0, 2 * Math.PI);
      ctx.fill();
      
      // Tag circle
      ctx.fillStyle = '#10b981';
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, 8, 0, 2 * Math.PI);
      ctx.fill();
      
      // Tag label
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(pos.tag_id, canvasPos.x, canvasPos.y - 25);
      
      // Confidence
      ctx.font = '9px sans-serif';
      ctx.fillStyle = '#aaa';
      ctx.fillText(`${(pos.confidence * 100).toFixed(0)}%`, canvasPos.x, canvasPos.y + 35);
    });

    // Draw legend
    const legendX = 20;
    const legendY = 20;
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(legendX, legendY, 150, setupMode ? 80 : 100);
    
    ctx.font = 'bold 12px sans-serif';
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'left';
    ctx.fillText('Legend', legendX + 10, legendY + 20);
    
    // Anchor
    ctx.fillStyle = '#3b82f6';
    ctx.beginPath();
    ctx.arc(legendX + 20, legendY + 40, 6, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#ddd';
    ctx.font = '11px sans-serif';
    ctx.fillText('Anchor', legendX + 35, legendY + 44);
    
    if (!setupMode) {
      // Tag
      ctx.fillStyle = '#10b981';
      ctx.beginPath();
      ctx.arc(legendX + 20, legendY + 60, 6, 0, 2 * Math.PI);
      ctx.fill();
      ctx.fillStyle = '#ddd';
      ctx.fillText('Tag/Employee', legendX + 35, legendY + 64);
    }
    
    // Grid info
    ctx.fillStyle = '#888';
    ctx.font = '10px sans-serif';
    ctx.fillText('Grid: 1m squares', legendX + 10, legendY + (setupMode ? 65 : 85));
  };

  // Redraw when data changes
  useEffect(() => {
    drawMap();
  }, [anchors, positions, setupMode, hoveredAnchor, draggedAnchor]);

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
      
      <div className="mt-4 text-sm text-slate-400">
        <p>Store dimensions: {STORE_WIDTH/100}m × {STORE_HEIGHT/100}m</p>
        <p>Anchors: {anchors.filter(a => a.is_active).length} active / {anchors.length} total</p>
        {positions.length > 0 && (
          <p>Tags tracked: {new Set(positions.map(p => p.tag_id)).size}</p>
        )}
      </div>
    </div>
  );
}
